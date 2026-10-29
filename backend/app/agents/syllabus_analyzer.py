"""
Syllabus Analyzer Agent Extension Point
======================================
This module defines the planned interface and extension point for the
Strands Agents SDK-powered Syllabus Analyzer to be implemented in Phase 2.

In Phase 2, this module will:
1. Initialize the Strands Agents SDK workflow.
2. Accept the extracted syllabus text from SyllabusParserService.
3. Prompt or orchestrate the agent to structure the syllabus into a hierarchy:
   - Course metadata (Course Name, Code, Instructor, Term)
   - Units/Modules
   - Discrete, testable topics with difficulty and time estimates
   - Key exam or assignment milestones
4. Provide structured topic lists that the student can review and edit in the UI.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class TopicItem(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    module_or_unit: Optional[str] = None
    estimated_hours: float = 1.0
    difficulty: str = "medium"


class SyllabusStructure(BaseModel):
    course_title: Optional[str] = None
    course_code: Optional[str] = None
    term: Optional[str] = None
    topics: List[TopicItem] = Field(default_factory=list)


class SyllabusAnalyzerAgentStub:
    """
    Extension stub for Phase 2 integration.
    Do not invoke or fake responses until Strands Agents SDK is wired in Phase 2.
    """
    @classmethod
    async def analyze_syllabus_text(cls, raw_text: str) -> SyllabusStructure:
        raise NotImplementedError(
            "Strands Agents SDK Syllabus Analyzer will be implemented in Phase 2. "
            "Phase 1 provides raw parsing and text validation."
        )
