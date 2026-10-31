"""
Automated regression tests for CSE2001 (Data Structures and Algorithms) syllabus extraction.
Verifies:
1. Exact course identity extraction: CSE2001 — Data Structures and Algorithms (never 'Independent Lab').
2. Clean 7-module structure with pristine titles and zero metadata leakage.
3. Module 5 title 'AVL Trees and Heap' correctly extracted (not missing or placeholder).
4. Official teaching hours totaling 46.0 hours (2,760 minutes), distributed across discrete topics.
5. Zero assignment leakage into study topics (Case Study 1, 2, 3 placed in assignments).
6. Segregated specifications deduplicated from 320 down to genuine items (5 objectives, 4 outcomes, 4 textbooks, 3 references, 5 online resources, 18 lab experiments).
"""

import os
import sqlite3
import pytest
from app.services.syllabus_extractor import SyllabusStructureExtractor, ExtractedSyllabusData


@pytest.fixture(scope="module")
def cse2001_raw_text() -> str:
    """Loads the actual uploaded CSE2001 raw text from the SQLite database."""
    db_path = "backend/syllabus_sync.db" if os.path.exists("backend/syllabus_sync.db") else "syllabus_sync.db"
    if not os.path.exists(db_path):
        pytest.skip(f"Database not found at {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    row = cur.execute(
        "SELECT raw_text FROM syllabi WHERE filename LIKE '%CSE2001%' LIMIT 1"
    ).fetchone()
    conn.close()

    if not row or not row[0]:
        pytest.skip("CSE2001 syllabus record not found in database")

    return row[0]


def test_cse2001_course_identity(cse2001_raw_text):
    """Verifies that course name is 'Data Structures and Algorithms' and code is 'CSE2001'."""
    data = SyllabusStructureExtractor.extract_structure(cse2001_raw_text)

    assert data.course_code == "CSE2001"
    assert data.course_name == "Data Structures and Algorithms"
    assert "Independent Lab" not in data.course_name
    assert data.course_name != "Course Syllabus"


def test_cse2001_module_count_and_titles(cse2001_raw_text):
    """Verifies that exactly 7 modules are extracted with pristine titles and no metadata."""
    data = SyllabusStructureExtractor.extract_structure(cse2001_raw_text)

    assert len(data.modules) == 7

    expected_modules = [
        (1, "Pointers, dynamic Memory allocation and Data Structures", 9.0),
        (2, "Linked List, Stack and Queue", 7.0),
        (3, "Searching and Sorting", 7.0),
        (4, "Trees", 6.0),
        (5, "AVL Trees and Heap", 7.0),
        (6, "Hashing and Indexing", 7.0),
        (7, "Contemporary Developments & Advanced Topics", 3.0),
    ]

    for idx, (exp_num, exp_title, exp_hours) in enumerate(expected_modules):
        mod = data.modules[idx]
        assert exp_title in mod["title"], f"Module {exp_num} title mismatch: {mod['title']}"
        assert f"{int(exp_hours)} hours" in mod["title"]
        assert mod["official_hours"] == exp_hours
        assert mod["official_minutes"] == int(exp_hours * 60)

        # Ensure no metadata boilerplate in module title
        mod_title_lower = mod["title"].lower()
        assert "module title" not in mod_title_lower
        assert "assignment to be given" not in mod_title_lower
        assert "tools to be used" not in mod_title_lower
        assert "case study" not in mod_title_lower
        # Verify 'module delivery (in hours) 7 hrs' is not repeated in title
        assert mod_title_lower.count("delivery") == 0
        assert mod_title_lower.count("hrs") == 0


def test_cse2001_module_5_title_not_missing(cse2001_raw_text):
    """Verifies that Module 5 has its genuine title 'AVL Trees and Heap'."""
    data = SyllabusStructureExtractor.extract_structure(cse2001_raw_text)

    mod5 = data.modules[4]
    assert "AVL Trees and Heap" in mod5["title"]
    assert "Module title" not in mod5["title"]
    assert mod5["official_hours"] == 7.0


def test_cse2001_total_hours_and_minute_distribution(cse2001_raw_text):
    """Verifies that official hours sum to 46.0 hours (2,760 minutes), not 22.8 hours."""
    data = SyllabusStructureExtractor.extract_structure(cse2001_raw_text)

    total_official_hours = sum(m["official_hours"] for m in data.modules)
    assert total_official_hours == 46.0

    total_official_minutes = sum(m["official_minutes"] for m in data.modules)
    assert total_official_minutes == 2760

    # Verify that the sum of topic estimated_minutes strictly matches the module minutes
    for mod in data.modules:
        topic_mins = sum(t["estimated_minutes"] for t in mod["topics"])
        assert topic_mins == mod["official_minutes"], (
            f"Module {mod['title']} topic minutes ({topic_mins}) does not match module official minutes ({mod['official_minutes']})"
        )


def test_cse2001_zero_assignment_leakage_into_topics(cse2001_raw_text):
    """Verifies that Case Study 1, 2, 3 are in assignments, never in study topics."""
    data = SyllabusStructureExtractor.extract_structure(cse2001_raw_text)

    all_topic_titles = [t["title"] for m in data.modules for t in m["topics"]]

    for title in all_topic_titles:
        lower = title.lower()
        assert "case study" not in lower, f"Topic '{title}' contains leaked Case Study instruction"
        assert "module delivery" not in lower
        assert "assignment to be given" not in lower

    # Verify that assignments were captured
    assert len(data.assignments) >= 3
    assignments_text = " ".join(data.assignments).lower()
    assert "case study 1" in assignments_text
    assert "case study 2" in assignments_text
    assert "case study 3" in assignments_text


def test_cse2001_segregated_specifications_clean_count(cse2001_raw_text):
    """Verifies that specifications are deduplicated to genuine items (< 45 total, not 320)."""
    data = SyllabusStructureExtractor.extract_structure(cse2001_raw_text)

    # 1. Course Objectives: 5 unique items
    assert len(data.objectives) == 5
    assert any("linear data structures" in o.lower() for o in data.objectives)
    assert any("algorithmic complexity" in o.lower() for o in data.objectives)

    # 2. Course Outcomes: 4 unique items
    assert len(data.outcomes) == 4
    assert any("properties and operations" in o.lower() for o in data.outcomes)

    # 3. Textbooks: 4 unique books
    assert len(data.textbooks) == 4
    assert any("horowitz" in b.lower() for b in data.textbooks)
    assert any("karumanchi" in b.lower() for b in data.textbooks)

    # 4. Reference Books: 3 unique books
    assert len(data.reference_books) == 3
    assert any("cormen" in b.lower() or "clrs" in b.lower() for b in data.reference_books)
    assert any("sedgewick" in b.lower() for b in data.reference_books)

    # 5. Online Resources: 5 distinct URLs
    assert len(data.online_resources) == 5
    assert any("freecodecamp.org" in u for u in data.online_resources)
    assert any("nptel.ac.in" in u for u in data.online_resources)
    assert any("visualgo.net" in u for u in data.online_resources)

    # 6. Indicative Lab Experiments: 18 lab experiments
    assert data.has_lab_component is True
    assert len(data.lab_experiments) >= 15
    assert len(data.lab_experiments) <= 20

    # Total segregated items: 5 + 4 + 4 + 3 + 5 + 18 = 39 items
    total_specs = (
        len(data.objectives)
        + len(data.outcomes)
        + len(data.textbooks)
        + len(data.reference_books)
        + len(data.online_resources)
        + len(data.lab_experiments)
    )
    assert total_specs < 45, f"Specification count too high: {total_specs} (indicates table column duplication)"

