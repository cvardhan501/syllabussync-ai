from fastapi import APIRouter, File, UploadFile, status
from app.schemas.syllabus import SyllabusUploadResponse
from app.services.syllabus_parser import SyllabusParserService

router = APIRouter(prefix="/syllabus", tags=["Syllabus"])


@router.post(
    "/upload",
    response_model=SyllabusUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and parse a syllabus document (PDF or DOCX)"
)
async def upload_syllabus(file: UploadFile = File(...)):
    """
    Accepts a syllabus file in PDF (.pdf) or DOCX (.docx) format.
    Validates file format, restricts size to 10 MB, extracts extractable text,
    and returns document summary metrics and preview text.
    
    Returns 400 for invalid formats, empty files, scanned PDFs without digital text,
    or corrupted files. Returns 413 if the file exceeds 10 MB.
    """
    return await SyllabusParserService.parse_uploaded_file(file)
