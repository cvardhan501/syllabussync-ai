import uuid
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ValidationWarning(BaseModel):
    code: str = Field(description="Unique error code (e.g., METADATA_LEAKAGE, SENTENCE_FRAGMENT)")
    severity: str = Field(description="'high', 'medium', or 'low'")
    message: str = Field(description="Actionable explanation of the issue")
    module_id: Optional[str] = Field(default=None, description="ID of affected module if applicable")
    module_title: Optional[str] = Field(default=None, description="Title of affected module")
    topic_id: Optional[str] = Field(default=None, description="ID of affected topic if applicable")
    topic_title: Optional[str] = Field(default=None, description="Title of affected topic")
    suggested_action: str = Field(
        default="edit",
        description="Suggested user action: 'remove', 'merge', 'edit', 'split', 'add_topic'"
    )


class ValidationReport(BaseModel):
    is_valid: bool = Field(default=True, description="Whether syllabus meets minimum structure criteria")
    quality_score: int = Field(default=100, description="Overall quality score from 0 to 100")
    needs_confirmation: bool = Field(default=False, description="True if low confidence or high warnings require student confirmation")
    total_warnings_count: int = Field(default=0)
    warnings: List[ValidationWarning] = Field(default_factory=list)
    summary: str = Field(default="Syllabus structure verified.")


class SubtopicItem(BaseModel):
    id: str = Field(default_factory=lambda: f"sub_{uuid.uuid4().hex[:8]}", description="Stable unique ID for the subtopic")
    title: str = Field(default="Untitled Subtopic", description="Subtopic title")


class TopicItem(BaseModel):
    id: str = Field(default_factory=lambda: f"top_{uuid.uuid4().hex[:8]}", description="Stable unique ID for the topic")
    title: str = Field(default="Untitled Topic", description="Topic title")
    explanation: str = Field(default="", description="Short explanation or learning objective")
    estimated_minutes: int = Field(default=60, description="Estimated study time in minutes (clearly marked as estimate)")
    difficulty: Literal["easy", "medium", "hard"] = Field(default="medium", description="Suggested difficulty level")
    prerequisites: List[str] = Field(default_factory=list, description="Explicit or inferred prerequisites")
    subtopics: List[SubtopicItem] = Field(default_factory=list, description="Subtopics explicitly mentioned in syllabus")
    source_evidence: Optional[str] = Field(default=None, description="Direct syllabus excerpt or section reference")
    confidence_notes: Optional[str] = Field(default=None, description="Confidence or uncertainty notes")
    order_index: int = Field(default=0, description="Order within the module")


class ModuleItem(BaseModel):
    id: str = Field(default_factory=lambda: f"mod_{uuid.uuid4().hex[:8]}", description="Stable unique ID for the module")
    title: str = Field(default="Untitled Module", description="Module or unit name")
    order_index: int = Field(default=0, description="Order index of the module")
    official_hours: Optional[float] = Field(default=None, description="Official delivery hours specified in syllabus")
    official_minutes: Optional[int] = Field(default=None, description="Official delivery duration in minutes")
    topics: List[TopicItem] = Field(default_factory=list, description="Topics belonging to this module")


class SyllabusHierarchy(BaseModel):
    course_name: Optional[str] = Field(default=None, description="Course or subject name identified in syllabus")
    course_code: Optional[str] = Field(default=None, description="Course code (e.g. CS101, MATH240)")
    term: Optional[str] = Field(default=None, description="Term or semester if found")
    credits: Optional[str] = Field(default=None, description="Extracted credit or hour allocation")
    course_objectives: List[str] = Field(default_factory=list, description="Explicit pedagogical goals separated from topics")
    course_outcomes: List[str] = Field(default_factory=list, description="Expected student outcomes (COs/POs) separated from topics")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisite course knowledge")
    textbooks: List[str] = Field(default_factory=list, description="Recommended textbooks and citations")
    reference_books: List[str] = Field(default_factory=list, description="Prescribed reference books")
    online_resources: List[str] = Field(default_factory=list, description="Prescribed web and online resources")
    assignments: List[str] = Field(default_factory=list, description="Explicit assignments, project work, case studies")
    lab_experiments: List[str] = Field(default_factory=list, description="Indicative laboratory experiments if embedded lab present")
    has_lab_component: bool = Field(default=False, description="True if document contains laboratory component")
    assessment_info: Optional[str] = Field(default=None, description="Grading and assessment scheme")
    modules: List[ModuleItem] = Field(default_factory=list, description="Extracted module and topic hierarchy")
    ambiguous_sections: List[str] = Field(
        default_factory=list,
        description="Ambiguous, poorly formatted, or unreadable sections that need student review"
    )
    ai_status: str = Field(
        default="completed",
        description="Status of AI analysis: 'completed', 'temporarily_unavailable', or 'local_extraction'"
    )
    ai_status_message: Optional[str] = Field(
        default=None,
        description="User-facing explanation of the analysis status"
    )


class SyllabusUploadResponse(BaseModel):
    status: str = Field(default="success", description="Status of the upload operation")
    syllabus_id: Optional[str] = Field(default=None, description="ID of saved syllabus record in database")
    owner_user_id: Optional[str] = Field(default=None, description="Owner user UUID for multi-tenant tenancy")
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
    course_name_suggestion: Optional[str] = Field(
        default=None,
        description="Candidate course name extracted from document header"
    )
    course_code_suggestion: Optional[str] = Field(
        default=None,
        description="Candidate course code extracted from document header"
    )
    message: str = Field(description="User-facing summary message")


class SyllabusAnalysisResponse(BaseModel):
    status: str = Field(default="success")
    syllabus_id: str = Field(description="Unique identifier of the parsed syllabus")
    owner_user_id: Optional[str] = Field(default=None, description="Owner user UUID")
    filename: str = Field(description="Filename of the syllabus")
    file_type: str = Field(description="Document format (pdf or docx)")
    char_count: int = Field(description="Character count")
    word_count: int = Field(description="Word count")
    course_name: Optional[str] = Field(default=None)
    course_code: Optional[str] = Field(default=None)
    term: Optional[str] = Field(default=None)
    credits: Optional[str] = Field(default=None)
    course_objectives: List[str] = Field(default_factory=list)
    course_outcomes: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    textbooks: List[str] = Field(default_factory=list)
    reference_books: List[str] = Field(default_factory=list)
    online_resources: List[str] = Field(default_factory=list)
    assignments: List[str] = Field(default_factory=list)
    lab_experiments: List[str] = Field(default_factory=list)
    has_lab_component: bool = Field(default=False)
    assessment_info: Optional[str] = Field(default=None)
    modules: List[ModuleItem] = Field(default_factory=list)
    ambiguous_sections: List[str] = Field(default_factory=list)
    total_topics_count: int = Field(default=0)
    total_estimated_minutes: int = Field(default=0)
    validation_report: Optional[ValidationReport] = Field(
        default=None,
        description="Structure and quality validation audit results"
    )
    is_fallback: bool = Field(default=False, description="True if generated by dev fallback because no model credentials were set")
    analysis_engine: str = Field(description="Engine or model that processed the syllabus")
    ai_status: str = Field(
        default="completed",
        description="Status of AI analysis: 'completed', 'temporarily_unavailable', or 'local_extraction'"
    )
    ai_status_message: Optional[str] = Field(
        default=None,
        description="User-facing explanation of the analysis status"
    )
    message: str = Field(description="User summary message")


class TopicUpdateRequest(BaseModel):
    course_name: Optional[str] = None
    course_code: Optional[str] = None
    modules: List[ModuleItem]
    ambiguous_sections: List[str] = Field(default_factory=list)
    course_objectives: List[str] = Field(default_factory=list)
    course_outcomes: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    textbooks: List[str] = Field(default_factory=list)
    reference_books: List[str] = Field(default_factory=list)
    online_resources: List[str] = Field(default_factory=list)
    assignments: List[str] = Field(default_factory=list)
    lab_experiments: List[str] = Field(default_factory=list)
    has_lab_component: bool = Field(default=False)
