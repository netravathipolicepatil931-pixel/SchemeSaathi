import asyncio
import base64
import copy
import json
import sqlite3
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend import auth_store
from backend.config import settings
from backend.database import init_db
from backend.main import app
from backend.models.auth import AuthenticatedUser
from backend.models.document import DocumentAnalysis
from backend.routers.auth import require_user
from backend.services import document_service


@pytest.fixture
def document_client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "documents.db"))
    monkeypatch.setattr(
        settings, "document_encryption_key", Fernet.generate_key().decode()
    )
    monkeypatch.setattr(settings, "gemini_api_key", "test-api-key")
    init_db()

    account = auth_store.create_user("documents@example.com", "unused")
    current_user = AuthenticatedUser(
        id=account["id"],
        email=account["email"],
        token_id=str(uuid4()),
        token_expires_at=1,
    )
    app.dependency_overrides[require_user] = lambda: current_user
    with TestClient(app) as client:
        yield client, current_user
    app.dependency_overrides.clear()


def _pdf_upload(content=b"%PDF-1.7\nexample"):
    return {
        "content": content,
        "headers": {
            "Content-Type": "application/pdf",
            "X-Filename": "Aadhaar%20Card.pdf",
        },
    }


def test_upload_stores_encrypted_file_and_enforces_account_isolation(
    document_client, monkeypatch
):
    client, owner = document_client
    upload_buffer = None

    async def classify(_content, _media_type):
        nonlocal upload_buffer
        upload_buffer = _content
        return DocumentAnalysis(
            is_supported_document=True,
            document_type="aadhaar",
            confidence=0.98,
        )

    monkeypatch.setattr(document_service, "classify_document", classify)
    content = b"%PDF-1.7\nsensitive document bytes"
    response = client.post("/api/documents", **_pdf_upload(content))
    assert response.status_code == 201
    created = response.json()
    assert created["document_type"] == "aadhaar"
    assert created["original_filename"] == "Aadhaar Card.pdf"
    assert upload_buffer == b"\x00" * len(content)
    listed = client.get("/api/documents")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["document_type"] == "aadhaar"
    assert listed.json()[0]["original_filename"] == "Aadhaar Card.pdf"
    assert "encrypted_content" not in listed.json()[0]

    with sqlite3.connect(settings.db_path) as connection:
        stored, stored_filename = connection.execute(
            "SELECT encrypted_content, encrypted_filename "
            "FROM user_documents WHERE id = ?",
            (created["id"],),
        ).fetchone()
    assert content not in stored
    assert b"Aadhaar Card.pdf" not in stored_filename

    other_account = auth_store.create_user("other@example.com", "unused")
    app.dependency_overrides[require_user] = lambda: AuthenticatedUser(
        id=other_account["id"],
        email=other_account["email"],
        token_id=str(uuid4()),
        token_expires_at=1,
    )
    assert client.get("/api/documents").json() == []
    assert client.get(
        f"/api/documents/{created['id']}/file"
    ).status_code == 404
    assert client.delete(
        f"/api/documents/{created['id']}"
    ).status_code == 404

    app.dependency_overrides[require_user] = lambda: owner
    downloaded = client.get(f"/api/documents/{created['id']}/file")
    assert downloaded.status_code == 200
    assert downloaded.content == content
    assert downloaded.headers["cache-control"] == "private, no-store"
    assert "filename*=UTF-8''Aadhaar%20Card.pdf" in downloaded.headers[
        "content-disposition"
    ]
    assert client.delete(f"/api/documents/{created['id']}").status_code == 204
    assert client.get("/api/documents").json() == []


def test_upload_rejects_files_over_two_megabytes_without_ai_call(
    document_client, monkeypatch
):
    client, _ = document_client
    called = False

    async def classify(_content, _media_type):
        nonlocal called
        called = True
        raise AssertionError("Oversized upload must not reach AI.")

    monkeypatch.setattr(document_service, "classify_document", classify)
    response = client.post(
        "/api/documents",
        **_pdf_upload(b"%PDF-" + b"x" * document_service.MAX_DOCUMENT_BYTES),
    )
    assert response.status_code == 413
    assert called is False


def test_upload_rejects_non_pdf_or_jpeg_content(document_client, monkeypatch):
    client, _ = document_client

    async def classify(_content, _media_type):
        raise AssertionError("Invalid content must not reach AI.")

    monkeypatch.setattr(document_service, "classify_document", classify)
    response = client.post(
        "/api/documents", **_pdf_upload(b"not a document")
    )
    assert response.status_code == 415


def test_upload_rejects_filename_extension_that_does_not_match_content(
    document_client, monkeypatch
):
    client, _ = document_client

    async def classify(_content, _media_type):
        raise AssertionError("Mismatched filenames must not reach AI.")

    monkeypatch.setattr(document_service, "classify_document", classify)
    response = client.post(
        "/api/documents",
        content=b"%PDF-1.7\nexample",
        headers={
            "Content-Type": "application/pdf",
            "X-Filename": "document.jpg",
        },
    )
    assert response.status_code == 415


def test_upload_sanitizes_path_components_in_original_filename(
    document_client, monkeypatch
):
    client, _ = document_client

    async def classify(_content, _media_type):
        return DocumentAnalysis(
            is_supported_document=True,
            document_type="pan_card",
            confidence=0.98,
        )

    monkeypatch.setattr(document_service, "classify_document", classify)
    response = client.post(
        "/api/documents",
        content=b"%PDF-1.7\nexample",
        headers={
            "Content-Type": "application/pdf",
            "X-Filename": "..%2F..%5Cprivate%2FPAN.pdf",
        },
    )
    assert response.status_code == 201
    assert response.json()["original_filename"] == "PAN.pdf"


def test_uncertain_ai_classification_does_not_save_file(
    document_client, monkeypatch
):
    client, _ = document_client

    async def classify(_content, _media_type):
        return DocumentAnalysis(
            is_supported_document=False,
            document_type="other",
            confidence=0.2,
        )

    monkeypatch.setattr(document_service, "classify_document", classify)
    response = client.post("/api/documents", **_pdf_upload())
    assert response.status_code == 422
    assert client.get("/api/documents").json() == []


def test_upload_buffer_is_cleared_if_ai_classification_fails(
    document_client, monkeypatch
):
    client, _ = document_client
    upload_buffer = None

    async def classify(content, _media_type):
        nonlocal upload_buffer
        upload_buffer = content
        raise HTTPException(status_code=502, detail="AI unavailable.")

    monkeypatch.setattr(document_service, "classify_document", classify)
    content = b"%PDF-1.7\nprivate content"
    response = client.post("/api/documents", **_pdf_upload(content))

    assert response.status_code == 502
    assert upload_buffer == b"\x00" * len(content)
    assert client.get("/api/documents").json() == []


def test_upload_requires_encryption_key_before_ai(document_client, monkeypatch):
    client, _ = document_client
    monkeypatch.setattr(settings, "document_encryption_key", None)

    async def classify(_content, _media_type):
        raise AssertionError("No file should be sent to AI without encryption.")

    monkeypatch.setattr(document_service, "classify_document", classify)
    response = client.post("/api/documents", **_pdf_upload())
    assert response.status_code == 503
    assert "DOCUMENT_ENCRYPTION_KEY" in response.json()["detail"]


def test_existing_document_table_encrypts_and_migrates_plaintext_filename(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "existing-documents.db"
    monkeypatch.setattr(settings, "db_path", str(database_path))
    monkeypatch.setattr(
        settings, "document_encryption_key", Fernet.generate_key().decode()
    )
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE user_documents (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                document_type TEXT NOT NULL,
                original_filename TEXT NOT NULL DEFAULT '',
                media_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                encrypted_content BLOB NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            INSERT INTO user_documents
                (id, user_id, document_type, original_filename, media_type,
                 size_bytes, encrypted_content)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-document",
                "legacy-user",
                "aadhaar",
                "Legacy Aadhaar.pdf",
                "application/pdf",
                16,
                b"encrypted-file",
            ),
        )

    init_db()

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute(
                "PRAGMA table_info(user_documents)"
            )
        }
        encrypted_filename = connection.execute(
            "SELECT encrypted_filename FROM user_documents "
            "WHERE id = 'legacy-document'"
        ).fetchone()[0]
    assert "encrypted_filename" in columns
    assert "original_filename" not in columns
    assert b"Legacy Aadhaar.pdf" not in encrypted_filename
    assert document_service.list_documents("legacy-user")[0][
        "original_filename"
    ] == "Legacy Aadhaar.pdf"


def test_document_routes_require_authentication(document_client):
    client, _ = document_client
    app.dependency_overrides.clear()
    response = client.get("/api/documents")
    assert response.status_code == 401


def test_document_status_reports_missing_ai_configuration(
    document_client, monkeypatch
):
    client, _ = document_client
    assert client.get("/api/documents/status").json() == {
        "ai_configured": True,
        "storage_configured": True,
    }

    monkeypatch.setattr(settings, "gemini_api_key", None)
    assert client.get("/api/documents/status").json() == {
        "ai_configured": False,
        "storage_configured": True,
    }


def test_gemini_classification_sends_only_file_and_type_prompt(
    monkeypatch,
):
    sent = {}

    class FakeResponse:
        is_success = True
        status_code = 200

        @staticmethod
        def json():
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "is_supported_document": True,
                                            "document_type": "pan_card",
                                            "confidence": 0.95,
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ]
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, **options):
            sent["url"] = url
            sent["headers"] = options["headers"]
            sent["payload"] = copy.deepcopy(options["json"])
            return FakeResponse()

    monkeypatch.setattr(settings, "gemini_api_key", "test-api-key")
    monkeypatch.setattr(
        document_service.httpx, "AsyncClient", lambda **_kwargs: FakeClient()
    )
    content = b"%PDF-1.7\nprivate content"
    result = asyncio.run(
        document_service.classify_document(content, "application/pdf")
    )

    assert result.document_type == "pan_card"
    assert sent["headers"] == {"x-goog-api-key": "test-api-key"}
    parts = sent["payload"]["contents"][0]["parts"]
    assert "Do not transcribe" in parts[0]["text"]
    assert parts[1]["inline_data"]["data"] == base64.b64encode(content).decode()


def test_gemini_classification_falls_back_when_primary_model_is_unavailable(
    monkeypatch,
):
    class FakeClient:
        def __init__(self):
            self.models = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, **options):
            self.models.append(url)
            if len(self.models) == 1:
                return httpx.Response(503, request=httpx.Request("POST", url))
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": json_module.dumps(
                                            {
                                                "is_supported_document": True,
                                                "document_type": "aadhaar",
                                                "confidence": 0.9,
                                            }
                                        )
                                    }
                                ]
                            }
                        }
                    ]
                },
                request=httpx.Request("POST", url),
            )

    import httpx

    import json as json_module

    client = FakeClient()
    monkeypatch.setattr(settings, "gemini_api_key", "test-api-key")
    monkeypatch.setattr(
        document_service.httpx, "AsyncClient", lambda **_kwargs: client
    )

    result = asyncio.run(
        document_service.classify_document(b"%PDF-1.7\nexample", "application/pdf")
    )

    assert result.document_type == "aadhaar"
    assert len(client.models) == 2
    assert "gemini-3.5-flash" in client.models[0]
    assert "gemini-3.8-flash" in client.models[1]
