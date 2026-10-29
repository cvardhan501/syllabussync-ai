import io
from fastapi.testclient import TestClient
from pypdf import PdfWriter
import docx

from app.main import app

client = TestClient(app)


def create_sample_docx(text: str = "Week 1: Foundations of Algorithms. Week 2: Sorting and Searching.") -> bytes:
    doc = docx.Document()
    doc.add_heading("CS200: Algorithms & Data Structures", level=1)
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def create_blank_docx() -> bytes:
    doc = docx.Document()
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def create_sample_pdf(text: str = "Physics 101: Mechanics, Thermodynamics, Electromagnetism.") -> bytes:
    # A valid PDF structure containing stream text
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length 70 >>\nstream\n"
        b"BT\n/F1 12 Tf\n100 700 Td\n(" + text.encode("utf-8") + b") Tj\nET\n"
        b"endstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000224 00000 n \n"
        b"0000000345 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n418\n%%EOF"
    )
    return pdf_content


def create_blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_upload_valid_docx():
    """Valid DOCX file returns 200 with extracted metrics and text preview."""
    docx_bytes = create_sample_docx()
    response = client.post(
        "/api/syllabus/upload",
        files={"file": ("cs200_syllabus.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["filename"] == "cs200_syllabus.docx"
    assert data["file_type"] == "docx"
    assert data["word_count"] > 5
    assert "Algorithms" in data["preview_text"]


def test_upload_valid_pdf():
    """Valid text PDF returns 200 with extracted text and correct metadata."""
    pdf_bytes = create_sample_pdf()
    response = client.post(
        "/api/syllabus/upload",
        files={"file": ("physics101.pdf", pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["filename"] == "physics101.pdf"
    assert data["file_type"] == "pdf"
    assert data["unit_count"] == 1
    assert "Physics" in data["preview_text"]


def test_upload_unsupported_file_extension():
    """Files with unsupported extensions (like .txt, .zip, .exe) return 400 Bad Request."""
    response = client.post(
        "/api/syllabus/upload",
        files={"file": ("notes.txt", b"Just some plain text notes", "text/plain")}
    )
    assert response.status_code == 400
    data = response.json()
    assert "Unsupported file format" in data["detail"]
    assert ".pdf" in data["detail"]


def test_upload_empty_file():
    """Zero-byte files return 400 Bad Request with explicit message."""
    response = client.post(
        "/api/syllabus/upload",
        files={"file": ("empty_syllabus.pdf", b"", "application/pdf")}
    )
    assert response.status_code == 400
    data = response.json()
    assert "empty" in data["detail"].lower()


def test_upload_blank_scanned_pdf():
    """PDFs with no extractable text trigger a helpful error message clarifying that OCR is not performed."""
    blank_pdf = create_blank_pdf()
    response = client.post(
        "/api/syllabus/upload",
        files={"file": ("scanned_scan.pdf", blank_pdf, "application/pdf")}
    )
    assert response.status_code == 400
    data = response.json()
    assert "does not contain extractable" in data["detail"]
    assert "OCR is not performed" in data["detail"]


def test_upload_empty_docx():
    """DOCX without text paragraphs or content returns 400 Bad Request."""
    blank_docx = create_blank_docx()
    response = client.post(
        "/api/syllabus/upload",
        files={"file": ("empty.docx", blank_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert response.status_code == 400
    data = response.json()
    assert "does not contain readable text" in data["detail"]


def test_upload_oversized_file():
    """Files exceeding size limit return 413 Payload Too Large."""
    # 11 MB of dummy data
    large_content = b"a" * (11 * 1024 * 1024)
    response = client.post(
        "/api/syllabus/upload",
        files={"file": ("oversized.pdf", large_content, "application/pdf")}
    )
    assert response.status_code == 413
    data = response.json()
    assert "exceeds the maximum limit" in data["detail"]

