"""Document processing + retrieval-augmented question answering."""
import io
import re

import numpy as np
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document, DocumentChunk
from app.services import embeddings, llm

CHUNK_CHARS = 1000
CHUNK_OVERLAP = 180


class DocumentError(ValueError):
    pass


def extract_pages(filename: str, data: bytes) -> list[tuple[int | None, str]]:
    """Return [(page_number, text)]."""
    name = filename.lower()
    if name.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise DocumentError("Encrypted PDFs are not supported")
            if len(reader.pages) > settings.max_pdf_pages:
                raise DocumentError(f"PDF has more than {settings.max_pdf_pages} pages")
            pages = [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]
        except PdfReadError as exc:
            raise DocumentError(f"Could not read PDF: {exc}") from exc
    elif name.endswith((".txt", ".md")):
        pages = [(None, data.decode("utf-8", errors="replace"))]
    else:
        raise DocumentError("Only .pdf, .txt and .md files are supported")
    if not any(text.strip() for _, text in pages):
        raise DocumentError("No extractable text found (scanned PDFs need OCR first)")
    return pages


def chunk_pages(pages: list[tuple[int | None, str]]) -> list[tuple[int | None, str]]:
    chunks = []
    for page_no, text in pages:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        start = 0
        while start < len(text):
            end = min(start + CHUNK_CHARS, len(text))
            if end < len(text):  # prefer to break on a sentence/paragraph boundary
                window = text[start:end]
                cut = max(window.rfind("\n\n"), window.rfind(". "))
                if cut > CHUNK_CHARS * 0.5:
                    end = start + cut + 1
            piece = text[start:end].strip()
            if len(piece) > 30:
                chunks.append((page_no, piece))
            if end >= len(text):
                break
            start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def index_document(db: Session, doc: Document, pages: list[tuple[int | None, str]]) -> int:
    chunks = chunk_pages(pages)
    vectors = embeddings.embed([c[1] for c in chunks])
    for i, ((page_no, text), vec) in enumerate(zip(chunks, vectors)):
        db.add(DocumentChunk(document_id=doc.document_id, chunk_index=i, page_number=page_no, content=text, embedding=vec))
    doc.chunk_count = len(chunks)
    doc.page_count = sum(1 for p, _ in pages if p is not None) or 1
    return len(chunks)


def search(db: Session, user_id: int, question: str, top_k: int = 5,
           document_ids: list[int] | None = None, course_id: int | None = None) -> list[tuple[DocumentChunk, Document, float]]:
    query_vec = embeddings.embed([question])[0]
    if embeddings.is_zero(query_vec):
        return []
    base = select(DocumentChunk, Document).join(Document, Document.document_id == DocumentChunk.document_id).where(
        Document.user_id == user_id
    )
    if document_ids:
        base = base.where(Document.document_id.in_(document_ids))
    if course_id is not None:
        base = base.where(Document.course_id == course_id)

    if settings.is_postgres:
        distance = DocumentChunk.embedding.cosine_distance(query_vec)
        rows = db.execute(base.add_columns(distance.label("distance")).order_by(distance).limit(top_k)).all()
        return [(chunk, doc, round(1 - float(dist), 4)) for chunk, doc, dist in rows]

    # SQLite fallback: cosine similarity in Python (vectors are L2-normalised)
    rows = db.execute(base).all()
    if not rows:
        return []
    matrix = np.array([chunk.embedding for chunk, _ in rows], dtype=np.float32)
    q = np.array(query_vec, dtype=np.float32)
    sims = matrix @ q / (np.linalg.norm(matrix, axis=1) * np.linalg.norm(q) + 1e-9)
    order = np.argsort(-sims)[:top_k]
    return [(rows[i][0], rows[i][1], round(float(sims[i]), 4)) for i in order]


SYSTEM_PROMPT = (
    "You are EduPilot, a friendly study assistant for university students. "
    "Answer the student's question using the numbered lecture-note excerpts provided. "
    "Cite the excerpts you rely on inline as [1], [2], etc. "
    "If the excerpts do not contain the answer, say so plainly, then give a brief general explanation "
    "clearly labelled as general knowledge (not from their notes). "
    "Be concise and well structured; use short paragraphs or bullet points and plain Markdown."
)


def answer(db: Session, user_id: int, question: str, top_k: int = 5,
           document_ids: list[int] | None = None, course_id: int | None = None) -> dict:
    hits = search(db, user_id, question, top_k, document_ids, course_id)
    hits = [h for h in hits if h[2] > 0.02]
    sources = [
        {
            "ref": i + 1,
            "document_id": doc.document_id,
            "filename": doc.filename,
            "page_number": chunk.page_number,
            "snippet": chunk.content[:400],
            "score": score,
        }
        for i, (chunk, doc, score) in enumerate(hits)
    ]
    if not hits:
        return {
            "answer": "I couldn't find anything relevant in your uploaded notes. Try rephrasing, "
                      "or upload the lecture material that covers this topic.",
            "mode": "empty",
            "sources": [],
        }

    context = "\n\n".join(
        f"[{i + 1}] {doc.filename}" + (f", page {chunk.page_number}" if chunk.page_number else "") + f"\n{chunk.content}"
        for i, (chunk, doc, _) in enumerate(hits)
    )
    prompt = f"<excerpts>\n{context}\n</excerpts>\n\nStudent question: {question}"
    text = llm.complete(SYSTEM_PROMPT, prompt, max_tokens=4000)
    if text:
        return {"answer": text, "mode": "llm", "sources": sources}

    bullets = "\n".join(
        f"- [{s['ref']}] {s['snippet'][:280].strip()}..." for s in sources[:3]
    )
    note = (
        "AI answers are not configured (set ANTHROPIC_API_KEY on the server)."
        if not settings.llm_enabled else "The AI service is temporarily unavailable."
    )
    return {
        "answer": f"{note} Here are the most relevant passages from your notes:\n\n{bullets}",
        "mode": "extractive",
        "sources": sources,
    }
