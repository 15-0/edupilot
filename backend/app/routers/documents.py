import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import require_enrolled_course
from app.models import Document, User
from app.schemas import ChatIn, ChatOut, DocumentOut
from app.security import get_current_user
from app.services import rag

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
def list_documents(course_id: int | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Document).where(Document.user_id == user.user_id)
    if course_id is not None:
        q = q.where(Document.course_id == course_id)
    return db.scalars(q.order_by(Document.upload_date.desc(), Document.document_id.desc())).all()


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    course_id: int | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if course_id is not None:
        require_enrolled_course(db, user, course_id)
    filename = Path(file.filename or "document").name
    data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File is larger than {settings.max_upload_mb} MB")
    if not data:
        raise HTTPException(status_code=400, detail="File is empty")
    try:
        pages = rag.extract_pages(filename, data)
    except rag.DocumentError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    folder = Path(settings.upload_dir) / str(user.user_id)
    folder.mkdir(parents=True, exist_ok=True)
    stored = folder / f"{uuid.uuid4().hex}_{filename}"
    stored.write_bytes(data)

    doc = Document(user_id=user.user_id, course_id=course_id, filename=filename,
                   stored_path=str(stored), file_size=len(data))
    db.add(doc)
    db.flush()
    try:
        rag.index_document(db, doc, pages)
        db.commit()
    except Exception:
        db.rollback()
        stored.unlink(missing_ok=True)
        raise
    db.refresh(doc)
    return doc


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if doc is None or doc.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Document not found")
    Path(doc.stored_path).unlink(missing_ok=True)
    db.delete(doc)
    db.commit()


@router.post("/chat", response_model=ChatOut)
def chat(data: ChatIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return rag.answer(db, user.user_id, data.question.strip(), data.top_k, data.document_ids, data.course_id)
