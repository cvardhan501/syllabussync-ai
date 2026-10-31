from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
import datetime


class AssessmentItem(BaseModel):
    id: str = Field(description="Unique assessment identifier")
    course_id: str = Field(description="Associated course identifier")
    name: str = Field(description="Assessment name, e.g. CA1, Mid-Sem, Final Exam")
    exam_date: str = Field(description="Target exam date in YYYY-MM-DD")
    assessment_type: Literal["internal", "mid_sem", "end_sem", "custom"] = Field(
        default="internal",
        description="Assessment category"
    )
    scope: Literal["internal", "end_sem", "both"] = Field(
        default="both",
        description="Scope covered by this assessment"
    )
    weightage: float = Field(default=0.0, description="Weightage percentage")
    order_index: int = Field(default=0)
    days_remaining: int = Field(default=0, description="Days remaining until the exam date")
    is_past: bool = Field(default=False, description="True if the assessment date is in the past")


class AssessmentCreate(BaseModel):
    id: Optional[str] = None
    name: str = Field(description="Assessment name, e.g. CA1, Mid-Sem, Final Exam")
    exam_date: str = Field(description="Target exam date in YYYY-MM-DD")
    assessment_type: Literal["internal", "mid_sem", "end_sem", "custom"] = Field(default="internal")
    scope: Literal["internal", "end_sem", "both"] = Field(default="both")
    weightage: float = Field(default=0.0)
    order_index: int = Field(default=0)

    @field_validator("exam_date")
    @classmethod
    def validate_future_exam_date(cls, v: str) -> str:
        try:
            d = datetime.date.fromisoformat(v)
            if d < datetime.date.today():
                raise ValueError("Exam date cannot be in the past.")
        except ValueError as err:
            if "Exam date cannot be in the past" in str(err):
                raise
            raise ValueError("Invalid date format. Expected YYYY-MM-DD.")
        return v


class CourseCreateRequest(BaseModel):
    course_name: str = Field(description="Course or subject name")
    course_code: Optional[str] = Field(default="", description="Course code (e.g. CSE3016, CS101)")
    owner_user_id: Optional[str] = Field(default=None, description="Owner user UUID for multi-tenant isolation")
    syllabus_id: Optional[str] = Field(default=None, description="Linked parsed syllabus ID")
    language: str = Field(default="English", description="Preferred learning / content language")
    lesson_style: Literal["Beginner-friendly", "In-depth", "Fast-paced", "Practical"] = Field(
        default="In-depth",
        description="Preferred lesson teaching style"
    )
    daily_study_availability: Literal["30-60 minutes", "1-2 hours", "2-4 hours", "4+ hours"] = Field(
        default="2-4 hours",
        description="Daily available study time"
    )
    daily_target_minutes: int = Field(default=120, description="Daily target in minutes")
    assessment_system_type: Literal["autonomous", "university", "custom"] = Field(
        default="autonomous",
        description="Assessment structure type"
    )
    assessment_scope: Literal["internal", "end_sem", "both"] = Field(default="both")
    color_theme: str = Field(default="blue")
    assessments: List[AssessmentCreate] = Field(default_factory=list)


class CourseUpdateRequest(BaseModel):
    course_name: Optional[str] = None
    course_code: Optional[str] = None
    owner_user_id: Optional[str] = None
    language: Optional[str] = None
    lesson_style: Optional[Literal["Beginner-friendly", "In-depth", "Fast-paced", "Practical"]] = None
    daily_study_availability: Optional[Literal["30-60 minutes", "1-2 hours", "2-4 hours", "4+ hours"]] = None
    daily_target_minutes: Optional[int] = None
    assessment_system_type: Optional[Literal["autonomous", "university", "custom"]] = None
    assessment_scope: Optional[Literal["internal", "end_sem", "both"]] = None
    color_theme: Optional[str] = None
    is_archived: Optional[bool] = None
    assessments: Optional[List[AssessmentCreate]] = None


class CourseResponse(BaseModel):
    status: str = Field(default="success")
    id: str
    owner_user_id: Optional[str] = None
    syllabus_id: Optional[str] = None
    course_name: str
    course_code: Optional[str] = None
    language: str = "English"
    lesson_style: str = "In-depth"
    daily_study_availability: str = "2-4 hours"
    daily_target_minutes: int = 120
    assessment_system_type: str = "autonomous"
    assessment_scope: str = "both"
    color_theme: str = "blue"
    is_archived: bool = False
    filename: Optional[str] = None
    file_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    total_topics: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    total_minutes: int = 0
    completed_minutes: int = 0
    progress_percentage: float = 0.0
    overdue_tasks_count: int = 0
    assessments: List[AssessmentItem] = Field(default_factory=list)
    next_assessment: Optional[AssessmentItem] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CourseListResponse(BaseModel):
    status: str = Field(default="success")
    total_count: int
    courses: List[CourseResponse]


class UpcomingAssessmentItem(BaseModel):
    id: str
    course_id: str
    course_name: str
    course_code: Optional[str] = None
    name: str
    exam_date: str
    days_remaining: int
    assessment_type: str = "internal"
    scope: str = "both"


class SemesterOverviewResponse(BaseModel):
    status: str = Field(default="success")
    total_courses: int
    total_topics: int
    total_tasks: int
    completed_tasks: int
    overall_percentage: float
    overdue_tasks_count: int
    upcoming_assessments: List[UpcomingAssessmentItem]
    courses: List[CourseResponse]


class SyllabusSetupRequest(BaseModel):
    syllabus_id: str = Field(description="ID of uploaded syllabus document")
    owner_user_id: Optional[str] = Field(default=None, description="Owner user UUID for multi-tenant isolation")
    course_name: str = Field(description="Verified course name")
    course_code: Optional[str] = Field(default="", description="Course code")
    language: str = Field(default="English", description="Preferred syllabus / content language")
    lesson_style: Literal["Beginner-friendly", "In-depth", "Fast-paced", "Practical"] = Field(
        default="In-depth",
        description="Preferred lesson style"
    )
    daily_study_availability: Literal["30-60 minutes", "1-2 hours", "2-4 hours", "4+ hours"] = Field(
        default="2-4 hours",
        description="Daily study availability"
    )
    assessment_system_type: Literal["autonomous", "university", "custom"] = Field(
        default="autonomous",
        description="Assessment system pattern"
    )
    assessment_scope: Literal["internal", "end_sem", "both"] = Field(default="both")
    assessments: List[AssessmentCreate] = Field(
        default_factory=list,
        description="Assessment milestones with future dates"
    )


class ReplaceSyllabusRequest(BaseModel):
    new_syllabus_id: str = Field(description="ID of newly uploaded syllabus to replace existing document")
    preserve_matching_completions: bool = Field(
        default=True,
        description="Whether to preserve completion status and notes for matching topic titles"
    )

