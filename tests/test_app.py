"""Tests for the FastAPI application routes."""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary directories for app data."""
    upload_dir = tmp_path / "pdfs"
    render_dir = tmp_path / "rendered"
    db_path = tmp_path / "test.db"
    upload_dir.mkdir()
    render_dir.mkdir()
    return tmp_path, upload_dir, render_dir, db_path


@pytest.fixture
def client(temp_data_dir):
    """Create a test client with isolated data directories."""
    tmp_path, upload_dir, render_dir, db_path = temp_data_dir

    # Patch paths before importing app
    with patch("frontier.app.UPLOAD_DIR", upload_dir), \
         patch("frontier.app.RENDER_DIR", render_dir), \
         patch("frontier.app.DATABASE_PATH", db_path), \
         patch("frontier.database.DATABASE_PATH", db_path):

        from frontier.database import init_db, seed_defaults
        init_db(db_path)
        seed_defaults(db_path)

        # Need to re-mount static files for rendered dir
        from frontier.app import app
        from fastapi.staticfiles import StaticFiles
        # Remove old rendered mount and add new one
        app.routes[:] = [r for r in app.routes if getattr(r, 'path', '') != '/rendered']
        app.mount("/rendered", StaticFiles(directory=str(render_dir)), name="rendered_test")

        yield TestClient(app)


@pytest.fixture
def sample_pdf():
    """Path to the test PDF if it exists."""
    pdf_path = Path("datasets/pdfs/A700_door_schedule.pdf")
    if pdf_path.exists():
        return pdf_path
    return None


class TestDashboard:
    def test_dashboard_loads(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "Frontier" in response.text
        assert "Dashboard" in response.text

    def test_dashboard_shows_zero_docs(self, client):
        response = client.get("/")
        assert "0" in response.text or "No documents" in response.text


class TestDocumentList:
    def test_documents_page_loads(self, client):
        response = client.get("/documents")
        assert response.status_code == 200
        assert "Documents" in response.text
        assert "Upload" in response.text

    def test_empty_document_list(self, client):
        response = client.get("/documents")
        assert "No documents uploaded" in response.text


class TestDocumentUpload:
    def test_upload_pdf(self, client, sample_pdf):
        if sample_pdf is None:
            pytest.skip("No test PDF available")

        with open(sample_pdf, "rb") as f:
            response = client.post(
                "/documents/upload",
                files={"file": ("A700_door_schedule.pdf", f, "application/pdf")},
                data={"doc_type": "schedule"},
                follow_redirects=False,
            )
        assert response.status_code == 303
        assert "/documents/1" in response.headers["location"]

    def test_upload_then_view(self, client, sample_pdf):
        if sample_pdf is None:
            pytest.skip("No test PDF available")

        with open(sample_pdf, "rb") as f:
            client.post(
                "/documents/upload",
                files={"file": ("A700_door_schedule.pdf", f, "application/pdf")},
                data={"doc_type": "schedule"},
            )

        # Document should appear in list
        response = client.get("/documents")
        assert "A700_door_schedule.pdf" in response.text
        assert "schedule" in response.text

    def test_upload_then_detail(self, client, sample_pdf):
        if sample_pdf is None:
            pytest.skip("No test PDF available")

        with open(sample_pdf, "rb") as f:
            client.post(
                "/documents/upload",
                files={"file": ("A700_door_schedule.pdf", f, "application/pdf")},
                data={"doc_type": "schedule"},
            )

        response = client.get("/documents/1")
        assert response.status_code == 200
        assert "A700_door_schedule.pdf" in response.text
        assert "Page 1" in response.text


class TestDocumentDetail:
    def test_404_for_missing_document(self, client):
        response = client.get("/documents/9999")
        assert response.status_code == 404


class TestDocumentTag:
    def test_update_tag(self, client, sample_pdf):
        if sample_pdf is None:
            pytest.skip("No test PDF available")

        with open(sample_pdf, "rb") as f:
            client.post(
                "/documents/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
                data={"doc_type": ""},
            )

        response = client.post(
            "/documents/1/tag",
            data={"doc_type": "plan"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert "plan" in response.text


class TestDocumentDelete:
    def test_delete_document(self, client, sample_pdf):
        if sample_pdf is None:
            pytest.skip("No test PDF available")

        with open(sample_pdf, "rb") as f:
            client.post(
                "/documents/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
                data={"doc_type": "schedule"},
            )

        response = client.post("/documents/1/delete", follow_redirects=True)
        assert response.status_code == 200
        assert "No documents uploaded" in response.text
