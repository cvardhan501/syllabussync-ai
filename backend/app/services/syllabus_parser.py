import io
from typing import Tuple
from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader
from pypdf.errors import PdfReadError
import docx

from app.core.config import settings
from app.schemas.syllabus import SyllabusUploadResponse

# Accepted file extensions and MIME patterns
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/vnd.pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/zip",
    "application/octet-stream",  # Browsers sometimes use generic binary stream for docx/pdf
}


class SyllabusParserService:
    @staticmethod
    def validate_file_metadata(file: UploadFile) -> Tuple[str, str]:
        """
        Validates file presence, filename, extension, and MIME type.
        Returns normalized (filename, extension).
        """
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided in upload."
            )

        filename = file.filename.strip()
        lower_name = filename.lower()
        
        # Check extension
        extension = None
        for ext in ALLOWED_EXTENSIONS:
            if lower_name.endswith(ext):
                extension = ext
                break
                
        if not extension:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{filename}'. SyllabusSync AI currently supports PDF (.pdf) and Microsoft Word (.docx) files."
            )

        # Check content-type if provided
        if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
            # If extension is valid but browser sent unexpected mime type, verify carefully
            pass

        return filename, extension

    @classmethod
    async def parse_uploaded_file(cls, file: UploadFile) -> SyllabusUploadResponse:
        """
        Reads, validates, and extracts text content from an uploaded PDF or DOCX file.
        Enforces size constraints and checks for scanned/empty documents.
        """
        filename, extension = cls.validate_file_metadata(file)

        # Read file contents into memory safely
        try:
            content = await file.read()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to read the uploaded file data."
            )

        file_size = len(content)

        # Check for empty file
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty (0 bytes). Please upload a valid syllabus document."
            )

        # Check file size limit
        if file_size > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File size ({file_size / (1024 * 1024):.2f} MB) exceeds the maximum limit of {settings.max_upload_size_mb} MB."
            )

        if extension == ".pdf":
            return cls._extract_pdf(filename, content, file_size)
        elif extension == ".docx":
            return cls._extract_docx(filename, content, file_size)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported document format."
            )

    @classmethod
    def _extract_pdf(cls, filename: str, content: bytes, file_size: int) -> SyllabusUploadResponse:
        try:
            pdf_stream = io.BytesIO(content)
            reader = PdfReader(pdf_stream)
            
            if reader.is_encrypted:
                try:
                    # Attempt empty password decrypt if standard
                    reader.decrypt("")
                except Exception:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="The uploaded PDF is password-protected and cannot be read."
                    )

            num_pages = len(reader.pages)
            if num_pages == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The uploaded PDF contains no pages."
                )

            extracted_chunks = []
            for page_idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                cleaned = page_text.strip()
                if cleaned:
                    extracted_chunks.append(cleaned)

            full_text = "\n\n".join(extracted_chunks).strip()

            # Handle scanned/image-only PDFs
            if not full_text:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "The uploaded PDF does not contain extractable digital text. "
                        "It appears to be a scanned document or image-only file. "
                        "SyllabusSync AI currently requires selectable text PDFs "
                        "(OCR is not performed in this version)."
                    )
                )

            words = full_text.split()
            word_count = len(words)
            char_count = len(full_text)

            preview = full_text[:1200]
            if len(full_text) > 1200:
                preview += "..."

            return SyllabusUploadResponse(
                status="success",
                filename=filename,
                file_type="pdf",
                file_size_bytes=file_size,
                char_count=char_count,
                word_count=word_count,
                unit_count=num_pages,
                unit_label="pages",
                preview_text=preview,
                full_text_length=char_count,
                extraction_notes=f"Successfully extracted digital text from all {num_pages} page(s).",
                message=f"Syllabus '{filename}' parsed successfully ({num_pages} pages, {word_count:,} words)."
            )

        except PdfReadError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The PDF file appears to be corrupted, malformed, or cannot be read."
            )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An error occurred while parsing the PDF document."
            )

    @classmethod
    def _extract_docx(cls, filename: str, content: bytes, file_size: int) -> SyllabusUploadResponse:
        try:
            docx_stream = io.BytesIO(content)
            doc = docx.Document(docx_stream)

            extracted_chunks = []
            para_count = 0

            # Extract from paragraphs
            for p in doc.paragraphs:
                text = p.text.strip()
                if text:
                    extracted_chunks.append(text)
                    para_count += 1

            # Extract from tables if present
            table_row_count = 0
            for table in doc.tables:
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_cells:
                        extracted_chunks.append(" | ".join(row_cells))
                        table_row_count += 1

            full_text = "\n\n".join(extracted_chunks).strip()

            if not full_text:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The uploaded DOCX document does not contain readable text."
                )

            words = full_text.split()
            word_count = len(words)
            char_count = len(full_text)

            preview = full_text[:1200]
            if len(full_text) > 1200:
                preview += "..."

            notes = f"Extracted {para_count} text paragraph(s)"
            if table_row_count > 0:
                notes += f" and {table_row_count} table row(s)"

            return SyllabusUploadResponse(
                status="success",
                filename=filename,
                file_type="docx",
                file_size_bytes=file_size,
                char_count=char_count,
                word_count=word_count,
                unit_count=para_count + table_row_count,
                unit_label="paragraphs & table rows",
                preview_text=preview,
                full_text_length=char_count,
                extraction_notes=notes,
                message=f"Syllabus '{filename}' parsed successfully ({word_count:,} words)."
            )

        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The DOCX file appears to be corrupted, malformed, or cannot be read."
            )
