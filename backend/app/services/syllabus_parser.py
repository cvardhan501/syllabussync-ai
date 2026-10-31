import io
import uuid
from typing import Tuple, Optional
from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader
from pypdf.errors import PdfReadError
import docx

from app.core.config import settings
from app.schemas.syllabus import SyllabusUploadResponse
from app.models.database import save_raw_syllabus

# Accepted file extensions and MIME patterns
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/vnd.pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/zip",
    "application/octet-stream",  # Browsers sometimes use generic binary stream
}


class SyllabusParserService:
    @staticmethod
    def validate_file_metadata(file: UploadFile) -> Tuple[str, str]:
        """
        Validates file presence, filename, and extension.
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

        return filename, extension

    @classmethod
    async def extract_text_and_metadata(cls, file: UploadFile, owner_user_id: Optional[str] = None) -> Tuple[str, str, str, int, int, int, str, int, str, str]:
        """
        Validates and extracts raw text from an UploadFile.
        Returns:
        (syllabus_id, filename, file_type, file_size, char_count, word_count, full_text, unit_count, unit_label, preview_text)
        """
        filename, extension = cls.validate_file_metadata(file)

        # Read file contents safely
        try:
            content = await file.read()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to read the uploaded file data."
            )

        file_size = len(content)

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty (0 bytes). Please upload a valid syllabus document."
            )

        if file_size > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File size ({file_size / (1024 * 1024):.2f} MB) exceeds the maximum limit of {settings.max_upload_size_mb} MB."
            )

        syllabus_id = str(uuid.uuid4())

        if extension == ".pdf":
            file_type = "pdf"
            full_text, unit_count, unit_label, notes = cls._extract_pdf_text(content)
        elif extension == ".docx":
            file_type = "docx"
            full_text, unit_count, unit_label, notes = cls._extract_docx_text(content)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported document format."
            )

        words = full_text.split()
        word_count = len(words)
        char_count = len(full_text)

        preview = full_text[:1200]
        if len(full_text) > 1200:
            preview += "..."

        # Persist raw syllabus record in database
        save_raw_syllabus(
            syllabus_id=syllabus_id,
            filename=filename,
            file_type=file_type,
            file_size_bytes=file_size,
            char_count=char_count,
            word_count=word_count,
            raw_text=full_text,
            owner_user_id=owner_user_id,
        )

        return (
            syllabus_id,
            filename,
            file_type,
            file_size,
            char_count,
            word_count,
            full_text,
            unit_count,
            unit_label,
            preview,
            notes
        )

    @classmethod
    async def parse_uploaded_file(cls, file: UploadFile, owner_user_id: Optional[str] = None) -> SyllabusUploadResponse:
        """Endpoint handler for POST /api/syllabus/upload."""
        (
            syllabus_id,
            filename,
            file_type,
            file_size,
            char_count,
            word_count,
            full_text,
            unit_count,
            unit_label,
            preview,
            notes
        ) = await cls.extract_text_and_metadata(file, owner_user_id=owner_user_id)

        # Extract candidate course name and code from header lines
        course_name_sugg = None
        course_code_sugg = None
        try:
            from app.services.syllabus_extractor import SyllabusStructureExtractor, ExtractedSyllabusData
            lines = SyllabusStructureExtractor.clean_and_unwrap_lines(full_text)
            temp_data = ExtractedSyllabusData()
            SyllabusStructureExtractor._extract_header_metadata(lines[:25], temp_data)
            if temp_data.course_name and temp_data.course_name != "Course Syllabus":
                course_name_sugg = temp_data.course_name
            if temp_data.course_code:
                course_code_sugg = temp_data.course_code
        except Exception:
            pass

        return SyllabusUploadResponse(
            status="success",
            syllabus_id=syllabus_id,
            owner_user_id=owner_user_id,
            filename=filename,
            file_type=file_type,  # type: ignore
            file_size_bytes=file_size,
            char_count=char_count,
            word_count=word_count,
            unit_count=unit_count,
            unit_label=unit_label,
            preview_text=preview,
            full_text_length=char_count,
            extraction_notes=notes,
            course_name_suggestion=course_name_sugg,
            course_code_suggestion=course_code_sugg,
            message=f"Syllabus '{filename}' parsed successfully ({unit_count} {unit_label}, {word_count:,} words)."
        )

    @classmethod
    def _extract_pdf_text(cls, content: bytes) -> Tuple[str, int, str, str]:
        try:
            pdf_stream = io.BytesIO(content)
            reader = PdfReader(pdf_stream)

            if reader.is_encrypted:
                try:
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
            for page in reader.pages:
                page_text = page.extract_text() or ""
                cleaned = page_text.strip()
                if cleaned:
                    extracted_chunks.append(cleaned)

            full_text = "\n\n".join(extracted_chunks).strip()

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

            notes = f"Successfully extracted digital text from all {num_pages} page(s)."
            return full_text, num_pages, "pages", notes

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
    def _extract_docx_text(cls, content: bytes) -> Tuple[str, int, str, str]:
        try:
            docx_stream = io.BytesIO(content)
            doc = docx.Document(docx_stream)

            extracted_chunks = []
            para_count = 0

            for p in doc.paragraphs:
                text = p.text.strip()
                if text:
                    extracted_chunks.append(text)
                    para_count += 1

            table_row_count = 0
            for table in doc.tables:
                for row in table.rows:
                    seen_tc = set()
                    row_cells = []
                    for cell in row.cells:
                        text = cell.text.strip()
                        if not text:
                            continue
                        tc_elem = getattr(cell, '_tc', None)
                        if tc_elem is not None:
                            if tc_elem in seen_tc:
                                continue
                            seen_tc.add(tc_elem)
                            row_cells.append(text)
                        else:
                            if not row_cells or row_cells[-1] != text:
                                row_cells.append(text)
                    if row_cells:
                        extracted_chunks.append(" | ".join(row_cells))
                        table_row_count += 1

            full_text = "\n\n".join(extracted_chunks).strip()

            if not full_text:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The uploaded DOCX document does not contain readable text."
                )

            notes = f"Extracted {para_count} text paragraph(s)"
            if table_row_count > 0:
                notes += f" and {table_row_count} table row(s)"

            total_units = para_count + table_row_count
            return full_text, total_units, "paragraphs & table rows", notes

        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The DOCX file appears to be corrupted, malformed, or cannot be read."
            )
