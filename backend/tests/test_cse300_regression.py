"""
Regression Test Suite for CSE300 Operating System with Linux Internals
======================================================================
Verifies:
- Accurate course title and code detection without truncation
- Exact 5/6/5/5/5/5/1 module topic distribution
- Theory vs. Lab separation (5 objectives, 5 outcomes, 15 lab experiments)
- Official delivery hours (300, 300, 300, 300, 300, 180, 120 = 1,800 minutes / 30.0 hours)
- Duration allocation math (topic minutes sum to module delivery hours)
- Separate literature (2 textbooks, 2 reference books, 7 online resources, 2 case studies)
"""

import os
import pytest
from app.services.syllabus_parser import SyllabusParserService
from app.services.syllabus_extractor import SyllabusStructureExtractor
from app.agents.syllabus_analyzer import SyllabusAnalyzerAgent

PDF_PATH = "C:/Users/cvard/Desktop/sem_3/Operating System with Linux Internals_Syllabus.pdf"


@pytest.fixture(scope="module")
def os_syllabus_text():
    assert os.path.exists(PDF_PATH), f"Fixture not found at {PDF_PATH}"
    with open(PDF_PATH, "rb") as f:
        text, _, _, _ = SyllabusParserService._extract_pdf_text(f.read())
    return text


def test_cse300_course_identity(os_syllabus_text):
    """Course title must not be truncated; course code must be CSE300."""
    extracted = SyllabusStructureExtractor.extract_structure(os_syllabus_text)
    assert extracted.course_name == "Operating System with Linux Internals"
    assert extracted.course_code == "CSE300"


def test_cse300_theory_vs_lab_separation(os_syllabus_text):
    """Theory objectives, outcomes, and lab experiments must be strictly partitioned."""
    extracted = SyllabusStructureExtractor.extract_structure(os_syllabus_text)

    # Theory objectives must be exactly 5, not doubled by lab objectives
    assert len(extracted.objectives) == 5, f"Expected 5 theory objectives, got {len(extracted.objectives)}"

    # Theory outcomes must be exactly 5, not inflated
    assert len(extracted.outcomes) == 5, f"Expected 5 theory outcomes, got {len(extracted.outcomes)}"

    # Embedded lab component detected
    assert extracted.has_lab_component is True

    # 15 Indicative Lab experiments segregated from theory
    assert len(extracted.lab_experiments) == 15, f"Expected 15 lab experiments, got {len(extracted.lab_experiments)}"
    assert "Install and configure a Linux OS" in extracted.lab_experiments[0]
    assert "Project Evaluation" in extracted.lab_experiments[14]


def test_cse300_literature_and_assignments(os_syllabus_text):
    """Separate textbooks, references, online resources, and assignments."""
    extracted = SyllabusStructureExtractor.extract_structure(os_syllabus_text)

    # Exactly 2 textbooks (Silberschatz + Tanenbaum)
    assert len(extracted.textbooks) == 2, f"Expected 2 textbooks, got {len(extracted.textbooks)}"
    assert any("Silberschatz" in tb for tb in extracted.textbooks)
    assert any("Tanenbaum" in tb for tb in extracted.textbooks)

    # Exactly 2 reference books (Singhal & Shivaratri + Pradeep K. Sinha)
    assert len(extracted.reference_books) == 2, f"Expected 2 reference books, got {len(extracted.reference_books)}"
    assert any("Singhal" in rb for rb in extracted.reference_books)
    assert any("Sinha" in rb for rb in extracted.reference_books)

    # Exactly 7 online resources
    assert len(extracted.online_resources) == 7, f"Expected 7 online resources, got {len(extracted.online_resources)}"

    # Exactly 2 case study assignments
    assert len(extracted.assignments) == 2, f"Expected 2 assignments, got {len(extracted.assignments)}"
    assert any("Case Study 1 on Module 3" in a for a in extracted.assignments)
    assert any("Case Study 2 on Module 6" in a for a in extracted.assignments)


def test_cse300_module_topic_distribution(os_syllabus_text):
    """Module topics must follow exact 5/6/5/5/5/5/1 distribution."""
    extracted = SyllabusStructureExtractor.extract_structure(os_syllabus_text)
    assert len(extracted.modules) == 7

    topic_counts = [len(m["topics"]) for m in extracted.modules]
    assert topic_counts == [5, 6, 5, 5, 5, 5, 1], f"Expected [5, 6, 5, 5, 5, 5, 1], got {topic_counts}"


def test_cse300_delivery_hours_and_duration_math(os_syllabus_text):
    """Total course duration must be 1,800 minutes (30.0 hours), and topic minutes must sum to module minutes."""
    extracted = SyllabusStructureExtractor.extract_structure(os_syllabus_text)

    expected_official_minutes = [300, 300, 300, 300, 300, 180, 120]
    total_allocated = 0

    for idx, mod in enumerate(extracted.modules):
        exp_mins = expected_official_minutes[idx]
        assert mod["official_minutes"] == exp_mins, f"Module {idx+1} expected {exp_mins}m, got {mod['official_minutes']}m"

        mod_topic_sum = sum(t["estimated_minutes"] for t in mod["topics"])
        assert mod_topic_sum == exp_mins, f"Module {idx+1} topics sum to {mod_topic_sum}m, expected {exp_mins}m"
        total_allocated += mod_topic_sum

    # Total must be strictly 1,800 minutes (30 hours), not 34 hours!
    assert total_allocated == 1800, f"Expected 1800 total minutes (30.0 hrs), got {total_allocated}"


def test_cse300_subtopics_extraction(os_syllabus_text):
    """Subtopics must be extracted where present, without phantom items."""
    extracted = SyllabusStructureExtractor.extract_structure(os_syllabus_text)

    # Module 1 topic 3: Operating-System Structures has 4 subtopics
    m1_t3 = extracted.modules[0]["topics"][2]
    assert "Operating-System Structures" in m1_t3["title"]
    sub_titles = [s["title"] for s in m1_t3["subtopics"]]
    assert len(sub_titles) == 4
    assert "Monolithic" in sub_titles
    assert "Microkernel" in sub_titles
    assert "Layers" in sub_titles
    assert "Modules" in sub_titles


def test_cse300_hierarchy_agent_integration(os_syllabus_text):
    """SyllabusAnalyzerAgent must preserve all components in SyllabusHierarchy."""
    hierarchy = SyllabusAnalyzerAgent._generate_deterministic_dev_fallback(
        os_syllabus_text,
        fallback_category="DEV_FALLBACK"
    )

    assert hierarchy.course_name == "Operating System with Linux Internals"
    assert hierarchy.course_code == "CSE300"
    assert len(hierarchy.course_objectives) == 5
    assert len(hierarchy.course_outcomes) == 5
    assert len(hierarchy.textbooks) == 2
    assert len(hierarchy.reference_books) == 2
    assert len(hierarchy.online_resources) == 7
    assert len(hierarchy.assignments) == 2
    assert hierarchy.has_lab_component is True
    assert len(hierarchy.lab_experiments) == 15
    assert len(hierarchy.modules) == 7

    total_mins = sum(sum(t.estimated_minutes for t in m.topics) for m in hierarchy.modules)
    assert total_mins == 1800

