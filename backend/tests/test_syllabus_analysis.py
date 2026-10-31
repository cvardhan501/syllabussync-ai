import io
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import docx

from app.main import app
from app.schemas.syllabus import SyllabusHierarchy, ModuleItem, TopicItem
from app.core.config import Settings, settings

client = TestClient(app)


def create_sample_docx(text: str = "Week 1: Foundations of Algorithms. Week 2: Sorting and Searching.") -> bytes:
    doc = docx.Document()
    doc.add_heading("CS200: Algorithms & Data Structures", level=1)
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_analyze_syllabus_with_file_dev_fallback():
    """Verify POST /api/syllabus/analyze parses document and returns structured hierarchy."""
    docx_bytes = create_sample_docx()
    with patch.object(Settings, "has_strands_credentials", return_value=False):
        response = client.post(
            "/api/syllabus/analyze",
            files={"file": ("cs200_syllabus.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "syllabus_id" in data
        assert len(data["modules"]) >= 1
        assert data["total_topics_count"] >= 1
        assert data["total_estimated_minutes"] > 0
        assert data["ai_status"] == "local_extraction"
        assert data["is_fallback"] is True
        # Ambiguous sections must never have technical errors or fallback tags
        for sec in data.get("ambiguous_sections", []):
            assert "[DEVELOPMENT FALLBACK" not in sec
            assert "CONFIG_MISSING" not in sec
        # Check topic fields
        first_topic = data["modules"][0]["topics"][0]
        assert "id" in first_topic
        assert "title" in first_topic
        assert "estimated_minutes" in first_topic
        assert first_topic["difficulty"] in ["easy", "medium", "hard"]


def test_analyze_empty_syllabus_rejects():
    """Verify empty document cannot be analyzed."""
    response = client.post(
        "/api/syllabus/analyze",
        files={"file": ("empty.pdf", b"", "application/pdf")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_analyze_missing_input_rejects():
    """Verify error when neither file nor syllabus_id is passed."""
    response = client.post("/api/syllabus/analyze")
    assert response.status_code == 400
    assert "either a syllabus document file or an existing syllabus_id" in response.json()["detail"]


def test_analyze_nonexistent_syllabus_id_returns_404():
    """Verify 404 when analyzing non-existent syllabus_id."""
    response = client.post(
        "/api/syllabus/analyze",
        data={"syllabus_id": "nonexistent-id-12345"}
    )
    assert response.status_code == 404


def test_credentials_missing_and_fallback_disabled_returns_503():
    """When credentials are not set and fallback is explicitly disabled, returns 503."""
    docx_bytes = create_sample_docx()
    with patch.object(Settings, "has_strands_credentials", return_value=False):
        # Temporarily disable dev fallback flag
        original_fallback = settings.allow_dev_fallback_analysis
        settings.allow_dev_fallback_analysis = False
        try:
            response = client.post(
                "/api/syllabus/analyze",
                files={"file": ("test.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            )
            assert response.status_code == 503
            assert "Strands Agents SDK is not configured" in response.json()["detail"]
        finally:
            settings.allow_dev_fallback_analysis = original_fallback


def test_mocked_strands_agent_call():
    """Verify that structured output from Strands Agent is correctly parsed and saved."""
    docx_bytes = create_sample_docx("Module 1: Graphs. Module 2: Dynamic Programming.")
    
    mock_hierarchy = SyllabusHierarchy(
        course_name="CS300: Advanced Algorithms",
        course_code="CS300",
        modules=[
            ModuleItem(
                id="mod_1",
                title="Module 1: Graph Theory",
                order_index=0,
                topics=[
                    TopicItem(
                        id="top_1_1",
                        title="Breadth First Search",
                        explanation="Graph traversal algorithm",
                        estimated_minutes=75,
                        difficulty="medium",
                        prerequisites=["Basic Graphs"],
                        source_evidence="Module 1: Graphs",
                        order_index=0,
                    )
                ]
            )
        ],
        ambiguous_sections=[]
    )

    mock_result = MagicMock()
    mock_result.structured_output = mock_hierarchy

    with patch.object(Settings, "has_strands_credentials", return_value=True):
        with patch("strands.Agent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.return_value = mock_result
            MockAgent.return_value = mock_instance

            response = client.post(
                "/api/syllabus/analyze",
                files={"file": ("cs300.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["course_name"] == "CS300: Advanced Algorithms"
            assert data["is_fallback"] is False
            assert data["ai_status"] == "completed"
            assert len(data["modules"]) == 1
            assert data["modules"][0]["topics"][0]["title"] == "Breadth First Search"


def test_malformed_model_output_handling():
    """Verify that malformed model text output raises 502 Bad Gateway when fallback disabled."""
    docx_bytes = create_sample_docx()
    mock_result = MagicMock()
    mock_result.structured_output = None
    mock_result.message = "This is not JSON at all! Just random gibberish."

    original_fallback = settings.allow_dev_fallback_analysis
    settings.allow_dev_fallback_analysis = False
    try:
        with patch.object(Settings, "has_strands_credentials", return_value=True):
            with patch("strands.Agent") as MockAgent:
                mock_instance = MagicMock()
                mock_instance.return_value = mock_result
                MockAgent.return_value = mock_instance

                response = client.post(
                    "/api/syllabus/analyze",
                    files={"file": ("cs300.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
                )
                assert response.status_code == 502
                assert "malformed or invalid" in response.json()["detail"].lower()
    finally:
        settings.allow_dev_fallback_analysis = original_fallback


def test_get_and_put_syllabus_topics():
    """Verify student can retrieve and update edited topics in SQLite."""
    # 1. First upload and analyze
    docx_bytes = create_sample_docx()
    with patch.object(Settings, "has_strands_credentials", return_value=False):
        res1 = client.post(
            "/api/syllabus/analyze",
            files={"file": ("cs200.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )
    assert res1.status_code == 200
    s_id = res1.json()["syllabus_id"]

    # 2. GET /api/syllabus/{s_id}
    res_get = client.get(f"/api/syllabus/{s_id}")
    assert res_get.status_code == 200
    get_data = res_get.json()
    assert get_data["syllabus_id"] == s_id
    assert len(get_data["modules"]) > 0

    # 3. Edit topics and save via PUT /api/syllabus/{s_id}/topics
    edited_modules = [
        {
            "id": "mod_1",
            "title": "Unit 1: Custom Student Edited Module",
            "order_index": 0,
            "topics": [
                {
                    "id": "top_custom_1",
                    "title": "Student Added Topic: Dijkstra Algorithm",
                    "explanation": "Shortest path algorithm",
                    "estimated_minutes": 90,
                    "difficulty": "hard",
                    "prerequisites": ["Priority Queues"],
                    "subtopics": [],
                    "order_index": 0
                }
            ]
        }
    ]

    res_put = client.put(
        f"/api/syllabus/{s_id}/topics",
        json={
            "course_name": "CS200: Data Structures (Student Custom)",
            "modules": edited_modules,
            "ambiguous_sections": ["Exam date was unclear"]
        }
    )
    assert res_put.status_code == 200
    put_data = res_put.json()
    assert put_data["course_name"] == "CS200: Data Structures (Student Custom)"
    assert put_data["modules"][0]["title"] == "Unit 1: Custom Student Edited Module"
    assert put_data["modules"][0]["topics"][0]["title"] == "Student Added Topic: Dijkstra Algorithm"
    assert put_data["modules"][0]["topics"][0]["estimated_minutes"] == 90
    assert put_data["total_estimated_minutes"] == 90

    # 4. Verify persistence with another GET
    res_verify = client.get(f"/api/syllabus/{s_id}")
    assert res_verify.status_code == 200
    assert res_verify.json()["modules"][0]["topics"][0]["title"] == "Student Added Topic: Dijkstra Algorithm"


def test_put_empty_modules_fails():
    """Verify PUT rejects empty modules list."""
    docx_bytes = create_sample_docx()
    with patch.object(Settings, "has_strands_credentials", return_value=False):
        res1 = client.post(
            "/api/syllabus/analyze",
            files={"file": ("cs200.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )
    s_id = res1.json()["syllabus_id"]

    res_put = client.put(
        f"/api/syllabus/{s_id}/topics",
        json={"modules": []}
    )
    assert res_put.status_code == 400
    assert "must have at least one module" in res_put.json()["detail"]


def test_put_nonexistent_syllabus_returns_404():
    """Verify PUT to non-existent syllabus returns 404."""
    res = client.put(
        "/api/syllabus/fake-id-999/topics",
        json={"modules": [{"id": "m1", "title": "Test", "order_index": 0, "topics": []}]}
    )
    assert res.status_code == 404


def test_model_tool_use_error_retries_non_streaming_success():
    """
    Verify that when streaming raises modelStreamErrorException (MODEL_TOOL_USE_ERROR),
    the analyzer automatically retries using non-streaming and succeeds.
    """
    docx_bytes = create_sample_docx("Module 1: Graphs. Module 2: Trees.")

    mock_hierarchy = SyllabusHierarchy(
        course_name="CS300: Advanced Algorithms",
        course_code="CS300",
        modules=[
            ModuleItem(
                id="mod_1",
                title="Module 1: Graph Theory",
                order_index=0,
                topics=[
                    TopicItem(
                        id="top_1_1",
                        title="Breadth First Search",
                        estimated_minutes=60,
                        order_index=0,
                    )
                ]
            )
        ],
        ambiguous_sections=[]
    )
    mock_success_result = MagicMock()
    mock_success_result.structured_output = mock_hierarchy

    # First call throws modelStreamErrorException (invalid sequence in toolUse)
    # Second call (retry non-streaming) succeeds
    mock_calls = [
        Exception("An error occurred (modelStreamErrorException) when calling the ConverseStream operation: Model produced invalid sequence as part of ToolUse."),
        mock_success_result,
    ]

    with patch.object(Settings, "has_strands_credentials", return_value=True):
        with patch("strands.Agent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.side_effect = mock_calls
            MockAgent.return_value = mock_instance

            response = client.post(
                "/api/syllabus/analyze",
                files={"file": ("cs300.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["is_fallback"] is False
            assert data["ai_status"] == "completed"
            assert data["course_name"] == "CS300: Advanced Algorithms"
            assert len(data["modules"]) >= 1
            # Verify MockAgent was called twice (streaming first, then non-streaming retry)
            assert mock_instance.call_count == 2


def test_model_tool_use_error_fallback_intact_content_clean_notes():
    """
    Verify that when model tool use errors persist even after retry,
    the analyzer catches MODEL_TOOL_USE_ERROR gracefully:
    1. Returns ai_status='temporarily_unavailable'
    2. NEVER leaks '[DEVELOPMENT FALLBACK: MODEL_TOOL_USE_ERROR]' into ambiguous_sections / syllabus notes
    3. Preserves all extracted modules, topics, and metadata intact
    """
    docx_bytes = create_sample_docx("Module 1: Operating Systems. Module 2: Processes and Threads.")

    stream_error = Exception(
        "An error occurred (modelStreamErrorException) when calling the ConverseStream operation: "
        "Model 'amazon.nova-lite-v1:0' emitted an invalid tool sequence during streaming. Greedy decoding (temperature=0.0) is configured."
    )

    with patch.object(Settings, "has_strands_credentials", return_value=True):
        with patch("strands.Agent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.side_effect = stream_error
            MockAgent.return_value = mock_instance

            response = client.post(
                "/api/syllabus/analyze",
                files={"file": ("os_syllabus.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["is_fallback"] is True
            assert data["ai_status"] == "temporarily_unavailable"
            assert "temporarily unavailable" in data.get("ai_status_message", "").lower()

            # CRITICAL: Ambiguous sections must NEVER contain technical error or fallback strings
            for sec in data.get("ambiguous_sections", []):
                assert "[DEVELOPMENT FALLBACK" not in sec
                assert "MODEL_TOOL_USE_ERROR" not in sec
                assert "modelStreamErrorException" not in sec
                assert "nova-lite" not in sec

            # Structure, modules, topics must remain intact
            assert len(data["modules"]) >= 1
            assert data["total_topics_count"] >= 1
            assert data["total_estimated_minutes"] > 0


def test_model_rate_limit_error_graceful_fallback_clean_notes():
    """Verify ThrottlingException / RATE_LIMIT_OR_QUOTA falls back with clean status and no technical notes leak."""
    docx_bytes = create_sample_docx("Module 1: Introduction to Networks.")

    throttle_error = Exception("An error occurred (ThrottlingException) when calling the Converse operation: Rate limit exceeded.")

    with patch.object(Settings, "has_strands_credentials", return_value=True):
        with patch("strands.Agent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.side_effect = throttle_error
            MockAgent.return_value = mock_instance

            response = client.post(
                "/api/syllabus/analyze",
                files={"file": ("networks.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["is_fallback"] is True
            assert data["ai_status"] == "temporarily_unavailable"
            for sec in data.get("ambiguous_sections", []):
                assert "[DEVELOPMENT FALLBACK" not in sec
                assert "RATE_LIMIT" not in sec


def test_missing_credentials_returns_local_extraction_status():
    """Verify missing credentials yields ai_status='local_extraction' with zero technical leak in ambiguous_sections."""
    docx_bytes = create_sample_docx("Module 1: Database Management Systems.")

    with patch.object(Settings, "has_strands_credentials", return_value=False):
        response = client.post(
            "/api/syllabus/analyze",
            files={"file": ("dbms.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_fallback"] is True
        assert data["ai_status"] == "local_extraction"
        assert "local syllabus extraction" in data.get("ai_status_message", "").lower()
        for sec in data.get("ambiguous_sections", []):
            assert "[DEVELOPMENT FALLBACK" not in sec
            assert "CONFIG_MISSING" not in sec

