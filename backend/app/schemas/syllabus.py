from typing import Optional
from pydantic import BaseModel, Field


class SyllabusUploadResponse(BaseModel):
    status: str = Field(default="success", description="Status of the upload operation")
    filename: str = Field(description="Original filename uploaded")
    file_type: str = Field(description="Normalized file type: 'pdf' or 'docx'")
    file_size_bytes: int = Field(description="Size of the uploaded file in bytes")
    char_count: int = Field(description="Total extracted character count")
    word_count: int = Field(description="Total estimated word count")
    unit_count: int = Field(description="Count of structural units (pages for PDF, paragraphs for DOCX)")
    unit_label: str = Field(description="Label for units (pages / paragraphs)")
    preview_text: str = Field(description="Initial preview of extracted syllabus text")
    full_text_length: int = Field(description="Length of entire extracted text")
    extraction_notes: Optional[str] = Field(
        default=None,
        description="Informational notes regarding document parsing or layout warnings"
    )
    message: str = Field(description="User-facing summary message")
