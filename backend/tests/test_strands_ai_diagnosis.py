"""
Tests diagnosing and verifying the Strands AI / Amazon Nova tool-use fix.
Confirms:
1. BedrockModel is created with explicit region_name=settings.aws_region.
2. Streaming is disabled (streaming=False) for Amazon Nova models to prevent ConverseStream MODEL_TOOL_USE_ERROR.
3. System prompt aligns with Strands structured tool use rather than conflicting with raw JSON text instructions.
4. Error handling does not leak internal technical tags ([DEVELOPMENT FALLBACK: ...]) to user-facing notes.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.core.config import settings
from app.agents.syllabus_analyzer import (
    SyllabusAnalyzerAgent,
    SYSTEM_PROMPT,
)


def test_system_prompt_instructs_tool_use_not_raw_json():
    """
    Ensure the system prompt does not contain conflicting raw JSON instructions
    like 'Return ONLY valid JSON' that cause tool forcing failures on ConverseStream.
    """
    assert "Return ONLY valid JSON" not in SYSTEM_PROMPT
    assert "SyllabusHierarchy" in SYSTEM_PROMPT


@pytest.mark.anyio
async def test_bedrock_model_configuration_and_non_streaming():
    """
    Verify BedrockModel is initialized with:
    1. Explicit region_name matching settings.aws_region.
    2. streaming=False for Nova models (e.g. amazon.nova-lite-v1:0).
    """
    with patch("strands.models.BedrockModel") as mock_bedrock:
        with patch("strands.Agent") as mock_agent:
            mock_inst = MagicMock()
            mock_agent.return_value = mock_inst
            mock_inst.structured_output.return_value = MagicMock(
                course_name="Test Course",
                course_code="CSE1001",
                total_hours=30.0,
                topics_count=5,
                credits=3,
                modules=[],
                segregated_specifications={},
                ambiguous_sections=[],
            )

            try:
                await SyllabusAnalyzerAgent._execute_strands_agent(
                    "Module 1: Test Topic",
                    non_streaming=False,
                )
            except Exception:
                pass

            assert mock_bedrock.called
            call_kwargs = mock_bedrock.call_args.kwargs
            assert call_kwargs.get("region_name") == settings.aws_region
            assert call_kwargs.get("streaming") is False


def test_no_technical_error_tags_in_user_facing_ambiguities_notes():
    """
    Verify that when model or extraction falls back, internal exception strings
    and tags like '[DEVELOPMENT FALLBACK: MODEL_TOOL_USE_ERROR]' are never leaked.
    """
    # Deterministic fallback call
    fallback_res = SyllabusAnalyzerAgent._generate_deterministic_dev_fallback(
        "Module 1: Foundations\nTopic 1: Intro",
        fallback_category="MODEL_TOOL_USE_ERROR",
        fallback_reason="Model emitted an invalid tool sequence",
        ai_status="temporarily_unavailable",
        ai_status_message="AI analysis temporarily unavailable",
    )

    # Check ambiguous_sections and notes
    notes = fallback_res.ambiguous_sections or []
    for note in notes:
        assert "[DEVELOPMENT FALLBACK" not in note
        assert "MODEL_TOOL_USE_ERROR" not in note
        assert "Model emitted an invalid" not in note

    assert fallback_res.ai_status == "temporarily_unavailable"
    assert fallback_res.ai_status_message == "AI analysis temporarily unavailable"
