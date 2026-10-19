"""PDF upload validation and knowledge-base index integrity."""

import io

import pytest
from pypdf import PdfWriter

from services.knowledge_base import (
    KnowledgeBase,
    KnowledgeBaseError,
    SourceDocument,
    rebuild_from_storage,
    vector_id,
)
from tests.conftest import FakeIndex, FakeStorage, FakeVectorStore
from utils.pdf_utils import normalize_text


def _pdf_bytes():
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _upload(client, headers, data, filename="guide.pdf"):
    return client.post(
        "/api/pdfs/upload",
        data={"file": (io.BytesIO(data), filename)},
        headers=headers,
        content_type="multipart/form-data",
    )


# --- Upload validation -------------------------------------------------------------
def test_valid_pdf_upload(client, admin_headers, storage):
    response = _upload(client, admin_headers, _pdf_bytes())
    assert response.status_code == 201
    pdf = response.get_json()["pdf"]
    assert pdf["is_public"] is False
    assert storage.uploaded == ["guide.pdf"]


def test_upload_rejects_wrong_extension(client, admin_headers):
    assert _upload(client, admin_headers, _pdf_bytes(), "notes.exe").status_code == 400


def test_upload_rejects_fake_pdf_content(client, admin_headers, storage):
    response = _upload(client, admin_headers, b"MZ\x90\x00 this is an executable", "fake.pdf")
    assert response.status_code == 400
    assert storage.uploaded == []


def test_upload_rejects_damaged_pdf(client, admin_headers):
    assert _upload(client, admin_headers, b"%PDF-1.7\n garbage", "broken.pdf").status_code == 400


def test_upload_rejects_oversized_file(make_app, storage):
    app = make_app(MAX_CONTENT_LENGTH=1024)
    client = app.test_client()
    login = client.post("/api/admin/login",
                        json={"email": "admin@example.test", "password": "correct-horse-battery-staple"})
    headers = {"Authorization": "Bearer " + login.get_json()["token"]}
    response = _upload(client, headers, b"%PDF-" + b"0" * 4096)
    assert response.status_code == 413
    assert storage.uploaded == []


def test_upload_reports_unconfigured_storage(client, admin_headers, storage):
    from services.cloudinary_service import StorageNotConfiguredError

    def not_configured(file):
        raise StorageNotConfiguredError("x")

    storage.upload_pdf = not_configured
    assert _upload(client, admin_headers, _pdf_bytes()).status_code == 503


def test_delete_outside_managed_folder_is_rejected(client, admin_headers, storage):
    response = client.delete("/api/pdfs/other_folder/secret", headers=admin_headers)
    assert response.status_code == 400
    assert storage.deleted == []


def test_delete_removes_document_vectors(client, admin_headers, storage, knowledge_base):
    public_id = "student_chatbot/pdfs/guide_abc12345"
    response = client.delete(f"/api/pdfs/{public_id}", headers=admin_headers)
    assert response.status_code == 200
    assert storage.deleted == [public_id]
    assert knowledge_base.deleted == [public_id]


# --- Index integrity -----------------------------------------------------------------
@pytest.fixture
def index():
    return FakeIndex()


@pytest.fixture
def kb(index):
    return KnowledgeBase({"PINECONE_NAMESPACE": "test"}, vectorstore=FakeVectorStore(index), index=index)


def _doc(source_id, paragraphs):
    text = "\n\n".join(f"Paragraph {i} of {source_id}. " + "word " * 150 for i in range(paragraphs))
    return SourceDocument(source_id=source_id, title=source_id.split("/")[-1], text=text)


def test_rebuild_uses_deterministic_ids_and_document_metadata(kb, index):
    summary = kb.rebuild([_doc("kb/a", 3)])
    assert summary["documents_indexed"] == 1
    assert vector_id("kb/a", 0) in index.ids
    text, metadata = kb._vectorstore.records[vector_id("kb/a", 0)]
    assert metadata["source_id"] == "kb/a" and metadata["title"] == "a"


def test_rebuilding_twice_creates_no_duplicates(kb, index):
    kb.rebuild([_doc("kb/a", 3)])
    first = set(index.ids)
    kb.rebuild([_doc("kb/a", 3)])
    assert index.ids == first


def test_rebuild_removes_stale_and_legacy_vectors(kb, index):
    index.ids.update({"3f2a1c9e-legacy-random-uuid", vector_id("kb/deleted", 0)})
    kb.rebuild([_doc("kb/a", 2)])
    assert "3f2a1c9e-legacy-random-uuid" not in index.ids
    assert vector_id("kb/deleted", 0) not in index.ids
    assert all(i.startswith("kb/a#chunk-") for i in index.ids)


def test_rebuild_removes_extra_chunks_when_document_shrinks(kb, index):
    kb.rebuild([_doc("kb/a", 6)])
    large = len(index.ids)
    kb.rebuild([_doc("kb/a", 1)])
    assert len(index.ids) < large


def test_rebuild_keeps_vectors_of_documents_that_failed_to_download(kb, index):
    kb.rebuild([_doc("kb/a", 1), _doc("kb/b", 1)])
    kb.rebuild([_doc("kb/a", 1)], failed_source_ids=["kb/b"])
    assert any(i.startswith("kb/b#chunk-") for i in index.ids)


def test_rebuild_with_no_text_leaves_index_untouched(kb, index):
    index.ids.add(vector_id("kb/a", 0))
    with pytest.raises(KnowledgeBaseError):
        kb.rebuild([SourceDocument("kb/empty", "empty", "")])
    assert index.ids == {vector_id("kb/a", 0)}
    assert index.deleted == []


def test_delete_document_removes_only_its_vectors(kb, index):
    kb.rebuild([_doc("kb/a", 2), _doc("kb/ab", 2)])
    removed = kb.delete_document("kb/a")
    assert removed > 0
    assert not any(i.startswith("kb/a#") for i in index.ids)
    assert any(i.startswith("kb/ab#") for i in index.ids)


def test_rebuild_from_storage_skips_unreadable_documents(kb, index):
    storage = FakeStorage()
    good = _pdf_bytes()
    storage.resources = [
        {"public_id": "kb/blank", "_bytes": good},
        {"public_id": "kb/broken", "_bytes": b"not a pdf"},
    ]
    # A blank page has no text, so nothing can be indexed and the index is preserved.
    with pytest.raises(KnowledgeBaseError):
        rebuild_from_storage(kb, storage)
    assert index.ids == set()


def test_normalize_text_keeps_non_english_characters():
    assert normalize_text("Café  Nairobi — résumé\x00") == "Café Nairobi — résumé"
