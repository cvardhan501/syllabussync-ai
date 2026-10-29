from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
from app.schemas.syllabus import (
    SyllabusUploadResponse,
    SyllabusAnalysisResponse,
    TopicUpdateRequest,
)
from app.services.syllabus_parser import SyllabusParserService
from app.agents.syllabus_analyzer import SyllabusAnalyzerAgent
from app.models.database import (
    save_syllabus_hierarchy,
    get_syllabus_record,
    get_syllabus_hierarchy,
)

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
    and returns document summary metrics, assigned syllabus_id, and preview text.
    """
    return await SyllabusParserService.parse_uploaded_file(file)


@router.post(
    "/analyze",
    response_model=SyllabusAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze syllabus with Strands Agents SDK to produce structured modules and topics"
)
async def analyze_syllabus(
    file: Optional[UploadFile] = File(None),
    syllabus_id: Optional[str] = Form(None),
):
    """
    Analyzes syllabus content using the Strands Agents SDK.
    Accepts either a new file upload OR an existing syllabus_id from a prior upload.
    Returns a verified module and topic hierarchy with study times, difficulty, and source evidence.
    """
    if not file and not syllabus_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide either a syllabus document file or an existing syllabus_id."
        )

    if file:
        (
            s_id,
            filename,
            file_type,
            file_size,
            char_count,
            word_count,
            raw_text,
            unit_count,
            unit_label,
            preview,
            notes,
        ) = await SyllabusParserService.extract_text_and_metadata(file)
    else:
        # Fetch from existing saved record
        record = get_syllabus_record(syllabus_id)  # type: ignore
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Syllabus with ID '{syllabus_id}' was not found."
            )
        s_id = record["id"]
        filename = record["filename"]
        file_type = record["file_type"]
        char_count = record["char_count"]
        word_count = record["word_count"]
        raw_text = record["raw_text"]

    # Run Strands Agent Analysis
    hierarchy, is_fallback, analysis_engine = await SyllabusAnalyzerAgent.analyze_syllabus(raw_text)

    # Persist structured hierarchy in SQLite
    save_syllabus_hierarchy(
        syllabus_id=s_id,
        hierarchy_dict=hierarchy.model_dump(),
        is_fallback=is_fallback,
        analysis_engine=analysis_engine,
    )

    total_topics = sum(len(m.topics) for m in hierarchy.modules)
    total_minutes = sum(
        sum(t.estimated_minutes for t in m.topics) for m in hierarchy.modules
    )

    return SyllabusAnalysisResponse(
        status="success",
        syllabus_id=s_id,
        filename=filename,
        file_type=file_type,
        char_count=char_count,
        word_count=word_count,
        course_name=hierarchy.course_name,
        course_code=hierarchy.course_code,
        modules=hierarchy.modules,
        ambiguous_sections=hierarchy.ambiguous_sections,
        total_topics_count=total_topics,
        total_estimated_minutes=total_minutes,
        is_fallback=is_fallback,
        analysis_engine=analysis_engine,
        message=f"Extracted {len(hierarchy.modules)} modules and {total_topics} topics for {hierarchy.course_name or filename}."
    )


@router.get(
    "/{syllabus_id}",
    response_model=SyllabusAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve saved syllabus and topic hierarchy"
)
async def get_syllabus(syllabus_id: str):
    """Retrieves an existing syllabus record and its structured topic hierarchy."""
    record = get_syllabus_record(syllabus_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Syllabus with ID '{syllabus_id}' was not found."
        )

    hierarchy_data = get_syllabus_hierarchy(syllabus_id)
    if not hierarchy_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hierarchy for syllabus '{syllabus_id}' has not been generated yet."
        )

    modules = hierarchy_data.get("modules", [])
    total_topics = sum(len(m.get("topics", [])) for m in modules)
    total_minutes = sum(
        sum(t.get("estimated_minutes", 60) for t in m.get("topics", [])) for m in modules
    )

    return SyllabusAnalysisResponse(
        status="success",
        syllabus_id=record["id"],
        filename=record["filename"],
        file_type=record["file_type"],
        char_count=record["char_count"],
        word_count=record["word_count"],
        course_name=record.get("course_name") or hierarchy_data.get("course_name"),
        course_code=record.get("course_code") or hierarchy_data.get("course_code"),
        modules=modules,
        ambiguous_sections=hierarchy_data.get("ambiguous_sections", []),
        total_topics_count=total_topics,
        total_estimated_minutes=total_minutes,
        is_fallback=bool(record.get("is_fallback", 0)),
        analysis_engine=record.get("analysis_engine") or "Stored Database Record",
        message=f"Loaded syllabus '{record['filename']}' ({total_topics} topics)."
    )


@router.put(
    "/{syllabus_id}/topics",
    response_model=SyllabusAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Save student-approved topic edits"
)
async def update_syllabus_topics(syllabus_id: str, payload: TopicUpdateRequest):
    """
    Updates the modules and topics for a syllabus after student editing.
    Allows updating titles, reordering topics, adding/deleting topics/modules,
    and adjusting estimated study minutes or difficulty.
    """
    record = get_syllabus_record(syllabus_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Syllabus with ID '{syllabus_id}' was not found."
        )

    # Validate that at least one module exists
    if not payload.modules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A syllabus must have at least one module/unit."
        )

    # Save changes to SQLite
    hierarchy_dict = {
        "course_name": payload.course_name or record.get("course_name"),
        "course_code": record.get("course_code"),
        "modules": [m.model_dump() for m in payload.modules],
        "ambiguous_sections": payload.ambiguous_sections,
    }

    save_syllabus_hierarchy(
        syllabus_id=syllabus_id,
        hierarchy_dict=hierarchy_dict,
        is_fallback=bool(record.get("is_fallback", 0)),
        analysis_engine=record.get("analysis_engine") or "User Edited",
    )

    total_topics = sum(len(m.topics) for m in payload.modules)
    total_minutes = sum(
        sum(t.estimated_minutes for t in m.topics) for m in payload.modules
    )

    return SyllabusAnalysisResponse(
        status="success",
        syllabus_id=record["id"],
        filename=record["filename"],
        file_type=record["file_type"],
        char_count=record["char_count"],
        word_count=record["word_count"],
        course_name=hierarchy_dict["course_name"],
        course_code=hierarchy_dict["course_code"],
        modules=payload.modules,
        ambiguous_sections=payload.ambiguous_sections,
        total_topics_count=total_topics,
        total_estimated_minutes=total_minutes,
        is_fallback=bool(record.get("is_fallback", 0)),
        analysis_engine="User Modified & Verified",
        message="Syllabus topics updated successfully."
    )
