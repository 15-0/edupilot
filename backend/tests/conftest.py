import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="edupilot-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_tmp / 'test.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(_tmp / "uploads")
os.environ["ANTHROPIC_API_KEY"] = ""  # tests never call the real LLM
os.environ["EMBEDDING_PROVIDER"] = "hashing"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def register(client, name, email, role="student"):
    r = client.post("/api/auth/register", json={"name": name, "email": email, "password": "password123", "role": role})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]
