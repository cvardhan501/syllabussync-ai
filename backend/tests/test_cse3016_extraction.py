"""
Automated tests for CSE3016 university syllabus extraction and Bedrock diagnostic fallback.
Verifies:
1. Clean 7-module extraction with stated teaching hours (summing to 45.0 hours).
2. Elimination of assignment instructions and table delivery boilerplate.
3. Multi-line module headings and split PDF line unwrapping.
4. Error classification distinguishing missing config from unavailable models.
"""

import pytest
from app.services.syllabus_extractor import SyllabusStructureExtractor
from app.agents.syllabus_analyzer import SyllabusAnalyzer
from app.services.syllabus_validator import SyllabusValidatorService


CSE3016_SAMPLE_SNIPPET = """
Syllabus format for a Theory alone Course (or) Theory Component of an Embedded Course 
Course Code: 
CSE3016 
Course Title:  
Object Oriented Modelling and Design using UML 
TPC 3 0 3 
Version No. 1.00 
Course Pre-
requisites/ Co-
requisites/ Anti-
requisites 
Nil 
Course Objectives: 1. Describe the concepts involved in Object-Oriented modelling and their benefits.  
2. Demonstrate concept of use -case model, sequence model and state chart model for a given problem.  
Expected Outcome: 1. Understand and Apply Advanced Object-Oriented Concepts and State Modelling 
2. Perform Use Case Modelling and Requirement Analysis for System Development 
Module 1 Module title:  
Introduction to 
Object-Oriented 
Concepts 
Assignment to be given      Module delivery (in 
hours) 
 6 hrs. 
Object-Oriented Development and Modelling Concepts, Object-Oriented Methodology, Advanced 
Link and Association Concepts Generalization, Inheritance, and Grouping Constructs, Sample Object 
Models, A sample class model; Navigation of class models 
Module 2 Module title:  
Advanced class 
concepts and State 
Modelling 
Assignment to be given/ 
Tools to be used (A1) 
Module delivery (in 
hours) 9 hrs. 
Advanced object and class concepts; Association ends; N-array associations; Aggregation; Abstract 
classes; Multiple inheritance; Metadata; Reification; Constraints; Derived data; Packages. 
State Modelling: Events, States, Transitions and Conditions; State diagrams; State diagram 
behaviour; Practical tips. 
Advanced State Modelling: Nested state diagrams; Nested states; Signal generalization; 
Concurrency; A sample state model; Relation of class and state models 
Module 3 Module title: 
UseCase Modelling 
and Detailed 
Requirements 
Assignment to be 
given/ Tools to be 
used 
Module delivery  (in 
hours) 7 hrs. 
Detailed object-oriented Requirements definitions; System Processes-A use case/Scenario view; 
Identifying Input and outputs -The System sequence diagram; Identifying Object Behaviour -The 
state chart Diagram; Integrated Object-oriented Models. 
Module 4 Module title : 
Interaction Modelling 
and System 
Conception 
Assignment to be given  
(A2) 
Module delivery  (in 
hours) 7 hrs. 
Interaction Modelling: Use case models; Sequence models; Activity models. Use case 
relationships; Procedural sequence models; Special constructs for activity models. Process 
Overview: Development stages; Development life Cycle. System Conception: Devising a system 
concept; elaborating a concept; preparing a problem statement. 
Module 5 Module title : 
Domain Analysis 
and System Design 
Assignment to be 
given/ Tools to be 
used 
Module delivery  (in 
hours) 7 hrs 
Overview of analysis; Domain class model; Domain state model; Domain  interaction model; 
Iterating the analysis. Overview of system design; Estimating performance; Making a reuse plan; 
Breaking a system in to sub -systems; Identifying concurrency; Allocation of sub -systems; 
Management of data storage; Handling global resources; Choosing a software control strategy; 
Handling boundary conditions. 
Module 6 Module title: Design 
Patterns 
Assignment to be given 
(A3) 
Module delivery (in 
hours) 7 hrs. 
Introduction to Design Patterns, describing  design patterns, the  catalogue of design patterns, 
Organizing the catalogue, how design patterns solve design  problems, how to select a design 
patterns, how to use a design pattern; Creational patterns: prototype and singleton; structural 
patterns adaptor and proxy. 
Module 7 Module title:  Assignment to be given/ 
Tools to be used 
Module delivery (in 
hours)  2hrs 
Contemporary developments in the area related to this course. 
Outline of the Assignment/ Project work/ Tools to be used/ Software used, etc. (if any): 
Three Assignments after every two modules. 
Textbook:  
1. Object-Oriented Modeling and Design with UML – Michael Blaha, James Rumbaugh, Pearson, 2nd Edition, 2011.  
Reference book(s): 
1. The Unified Modeling Language User Guide – Grady Booch, Pearson, 2005. 
"""


def test_cse3016_full_extraction_modules_and_hours():
    """Verifies that CSE3016 produces 7 modules with stated hours summing to 45.0 hours."""
    data = SyllabusStructureExtractor.extract_structure(CSE3016_SAMPLE_SNIPPET)

    # 1. Identity
    assert data.course_code == "CSE3016"
    assert "Object Oriented Modelling and Design using UML" in data.course_name
    assert "TPC 3 0 3" in data.credits
    assert data.prerequisites == []

    # 2. Module Count
    assert len(data.modules) == 7

    # 3. Module Titles
    titles = [m["title"] for m in data.modules]
    assert any("Introduction to Object-Oriented Concepts" in t for t in titles)
    assert any("Advanced class concepts and State Modelling" in t for t in titles)
    assert any("UseCase Modelling and Detailed Requirements" in t for t in titles)
    assert any("Interaction Modelling and System Conception" in t for t in titles)
    assert any("Domain Analysis and System Design" in t for t in titles)
    assert any("Design Patterns" in t for t in titles)
    assert any("Contemporary developments" in t for t in titles)

    # 4. Teaching Hours Consistency: 6 + 9 + 7 + 7 + 7 + 7 + 2 = 45 hours (2700 minutes)
    total_minutes = sum(
        sum(t["estimated_minutes"] for t in m["topics"]) for m in data.modules
    )
    assert total_minutes == 2700
    assert total_minutes / 60 == 45.0

    # 5. Check individual module durations and Module 1 6-topic extraction
    m1_topics = data.modules[0]["topics"]
    assert len(m1_topics) == 6
    assert m1_topics[0]["title"] == "Object-Oriented Development and Modelling Concepts"
    assert m1_topics[1]["title"] == "Object-Oriented Methodology"
    assert m1_topics[2]["title"] == "Advanced Link and Association Concepts"
    assert m1_topics[3]["title"] == "Generalization, Inheritance, and Grouping Constructs"
    assert m1_topics[4]["title"] == "Sample Object Models"
    assert m1_topics[5]["title"] == "A sample class model; Navigation of class models"

    # All 6 topics receive 60 min each, summing to exactly 360 min
    for t in m1_topics:
        assert t["estimated_minutes"] == 60

    m1_mins = sum(t["estimated_minutes"] for t in data.modules[0]["topics"])
    assert m1_mins == 360  # 6.0 hours

    m2_mins = sum(t["estimated_minutes"] for t in data.modules[1]["topics"])
    assert m2_mins == 540  # 9.0 hours

    m7_mins = sum(t["estimated_minutes"] for t in data.modules[6]["topics"])
    assert m7_mins == 120  # 2.0 hours


def test_zero_assignment_and_boilerplate_leakage():
    """Verifies that assignment instructions and table boilerplate are never treated as topics."""
    data = SyllabusStructureExtractor.extract_structure(CSE3016_SAMPLE_SNIPPET)

    all_topic_titles = [
        t["title"] for m in data.modules for t in m["topics"]
    ]

    for title in all_topic_titles:
        lower = title.lower()
        assert "assignment to be given" not in lower
        assert "tools to be used" not in lower
        assert "(a1)" not in lower
        assert "(a2)" not in lower
        assert "(a3)" not in lower
        assert "module delivery" not in lower
        assert not lower.endswith("hrs.")
        assert not lower.endswith("hours)")
        assert "three assignments after every two modules" not in lower


def test_split_module_headings_across_lines():
    """Verifies that module titles split across multiple lines in table cells are properly combined."""
    snippet = """
    Module 1 Module title:
    Cloud
    Computing
    Architecture
    Module delivery (in hours) 4 hrs.
    Virtualization; Containers; Microservices.
    """
    data = SyllabusStructureExtractor.extract_structure(snippet)
    assert len(data.modules) == 1
    assert "Cloud Computing Architecture" in data.modules[0]["title"]
    assert "4 hours" in data.modules[0]["title"]
    assert len(data.modules[0]["topics"]) == 3
    # 4 hours = 240 minutes, 80 min each
    assert sum(t["estimated_minutes"] for t in data.modules[0]["topics"]) == 240


def test_error_classification_bedrock_model_not_available():
    """Verifies that AccessDeniedException for unavailable model is classified accurately."""
    class MockAccessDeniedException(Exception):
        pass

    err = MockAccessDeniedException(
        "An error occurred (AccessDeniedException) when calling the Converse operation: "
        "anthropic.claude-sonnet-5 is not available for this account. You can explore other available models on Amazon Bedrock."
    )
    category, reason = SyllabusAnalyzer.classify_model_error(err)
    assert category == "MODEL_NOT_AVAILABLE"
    assert "not available for this AWS account" in reason


def test_error_classification_anthropic_form_missing():
    """Verifies that missing Anthropic Use Case details form is classified as MODEL_NOT_AVAILABLE."""
    class MockResourceNotFoundException(Exception):
        pass

    err = MockResourceNotFoundException(
        "Model use case details have not been submitted for this account. "
        "Fill out the Anthropic use case details form before using the model."
    )
    category, reason = SyllabusAnalyzer.classify_model_error(err)
    assert category == "MODEL_NOT_AVAILABLE"
    assert "Anthropic Use Case Details form" in reason


def test_error_classification_authorization_failure():
    """Verifies IAM permission denials are classified as AUTHORIZATION_FAILURE."""
    class MockAccessDeniedException(Exception):
        pass

    err = MockAccessDeniedException(
        "User: arn:aws:iam::123:user/test is not authorized to perform: bedrock:InvokeModel on resource: arn:..."
    )
    category, reason = SyllabusAnalyzer.classify_model_error(err)
    assert category == "AUTHORIZATION_FAILURE"
    assert "authorization failure" in reason.lower()


def test_dev_fallback_never_inserts_technical_errors_into_ambiguities():
    """Verifies fallback hierarchy sets ai_status cleanly and NEVER injects technical errors into ambiguous_sections."""
    hierarchy = SyllabusAnalyzer._generate_deterministic_dev_fallback(
        CSE3016_SAMPLE_SNIPPET,
        fallback_category="MODEL_NOT_AVAILABLE",
        fallback_reason="Bedrock model au.anthropic.claude-sonnet-5 is not available for this AWS account.",
        ai_status="temporarily_unavailable",
    )
    # Technical error and fallback tags must NEVER leak into ambiguous_sections
    for section in hierarchy.ambiguous_sections:
        assert "[DEVELOPMENT FALLBACK" not in section
        assert "MODEL_NOT_AVAILABLE" not in section
        assert "claude-sonnet" not in section
    # User-friendly AI status must be cleanly set
    assert hierarchy.ai_status == "temporarily_unavailable"
    assert hierarchy.ai_status_message == "AI analysis temporarily unavailable"
    # Extracted content must remain completely intact
    assert len(hierarchy.modules) == 7
    assert hierarchy.course_code == "CSE3016"


def test_fallback_quality_score_capped_and_warns():
    """Verifies fallback analysis cannot falsely appear as 100/100 successfully AI-validated."""
    hierarchy = SyllabusAnalyzer._generate_deterministic_dev_fallback(
        CSE3016_SAMPLE_SNIPPET,
        fallback_category="MODEL_TOOL_USE_ERROR",
        fallback_reason="Model emitted an invalid tool sequence during streaming.",
        ai_status="temporarily_unavailable",
    )
    report = SyllabusValidatorService.validate_hierarchy(hierarchy.model_dump(), is_fallback=True)

    # Score must be capped (< 75) and flagged for student confirmation
    assert report.quality_score <= 70
    assert report.quality_score != 100
    assert report.needs_confirmation is True
    assert any(w.code == "FALLBACK_ACTIVE" for w in report.warnings)


def test_error_classification_eventstream_tooluse_error():
    """Verifies botocore EventStreamError with modelStreamErrorException is classified cleanly."""
    class MockEventStreamError(Exception):
        def __init__(self, message, error_code="modelStreamErrorException"):
            super().__init__(message)
            self.response = {"Error": {"Code": error_code, "Message": message}}

    err = MockEventStreamError(
        "An error occurred (modelStreamErrorException) when calling the ConverseStream operation: "
        "Model produced invalid sequence as part of ToolUse. Please refer to the model tool use troubleshooting guide."
    )
    category, reason = SyllabusAnalyzer.classify_model_error(err)
    assert category == "MODEL_TOOL_USE_ERROR"
    assert "invalid tool" in reason.lower() or "tool sequence" in reason.lower()


