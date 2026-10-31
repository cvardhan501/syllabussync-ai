"""
Syllabus Quality Validator
==========================
Inspects structured syllabus hierarchies and detects quality defects:
- Suspicious topic counts (over-fragmentation or under-extraction)
- Administrative metadata mistakenly classified as topics
- Incomplete sentence fragments
- Duplicate topics
- Empty modules
- Unreasonable study time estimates
"""

import re
from typing import List, Dict, Any, Optional

from app.schemas.syllabus import ValidationWarning, ValidationReport


METADATA_SUSPICIOUS_TERMS = [
    r"\bcredits?\b",
    r"\bl\s*t\s*p\s*c\b",
    r"\bsemester\b",
    r"\bregulation\b",
    r"\bpage\s+\d+\b",
    r"\bisbn\b",
    r"\btextbooks?\b",
    r"\breferences?\b",
    r"\bgrading\b",
    r"\bmidterm\b",
    r"\bdepartment\s+of\b",
    r"\bcia[\s\-]?\d\b",
    r"\bacademic\s+year\b",
    r"\blecture\s+hours?\b",
    r"\battendance\b",
]

FRAGMENT_TERMINAL_WORDS = {
    "and", "or", "the", "to", "for", "in", "by", "of", "with", "a", "an", "from", "into", "onto", "as"
}


class SyllabusValidatorService:
    @classmethod
    def audit_hierarchy(
        cls,
        hierarchy: Any,
        is_fallback: bool = False,
    ) -> ValidationReport:
        """
        Audits hierarchy structure and returns ValidationReport.
        Accepts SyllabusHierarchy instance, dict, or Pydantic model dump.
        """
        if hasattr(hierarchy, "model_dump"):
            h_dict = hierarchy.model_dump()
        elif isinstance(hierarchy, dict):
            h_dict = hierarchy
        else:
            h_dict = dict(hierarchy)
        return cls.validate_hierarchy(h_dict, is_fallback=is_fallback)

    @classmethod
    def validate_hierarchy(
        cls,
        hierarchy_dict: Any,
        is_fallback: bool = False,
    ) -> ValidationReport:
        """
        Validates modules and topics structure.
        Accepts dict representation, SyllabusHierarchy instance, or Pydantic model dump.
        """
        if hasattr(hierarchy_dict, "model_dump"):
            hierarchy_dict = hierarchy_dict.model_dump()

        modules = hierarchy_dict.get("modules", [])
        warnings: List[ValidationWarning] = []
        score = 100

        total_topics_count = sum(len(m.get("topics", [])) for m in modules)

        # Detect development fallback mode from argument, dict, or status
        is_fallback_mode = bool(
            is_fallback
            or hierarchy_dict.get("is_fallback")
            or hierarchy_dict.get("ai_status") in ("temporarily_unavailable", "local_extraction")
            or any("DEVELOPMENT FALLBACK" in str(a) for a in hierarchy_dict.get("ambiguous_sections", []))
        )

        if is_fallback_mode:
            status_desc = (
                "AI analysis was temporarily unavailable"
                if hierarchy_dict.get("ai_status") == "temporarily_unavailable"
                else "deterministic local extraction was used"
            )
            warnings.append(ValidationWarning(
                code="FALLBACK_ACTIVE",
                severity="medium",
                message=f"Syllabus structure was generated via rule-based extraction because {status_desc}. AI pedagogical validation was not applied.",
                suggested_action="edit",
            ))
            score -= 30  # Cap fallback score so it cannot falsely appear 100% AI-validated

        # 1. Suspicious Topic Count Checks
        if total_topics_count == 0:
            warnings.append(ValidationWarning(
                code="ZERO_TOPICS",
                severity="high",
                message="No topics were detected in this syllabus. Please add topics before proceeding.",
                suggested_action="add_topic",
            ))
            score -= 50
        elif total_topics_count > 90:
            warnings.append(ValidationWarning(
                code="SUSPICIOUS_TOPIC_COUNT",
                severity="high",
                message=f"Suspiciously high topic count ({total_topics_count} topics). Standard university syllabi typically contain 15-50 topics. Some sentences or headings may have been over-fragmented.",
                suggested_action="merge",
            ))
            score -= 25
        elif total_topics_count > 75:
            warnings.append(ValidationWarning(
                code="HIGH_TOPIC_COUNT",
                severity="low",
                message=f"Detailed syllabus breakdown with {total_topics_count} topics. Ensure granular items represent discrete study sessions.",
                suggested_action="merge",
            ))
            score -= 5
        elif total_topics_count < 3:
            warnings.append(ValidationWarning(
                code="FEW_TOPICS",
                severity="medium",
                message=f"Only {total_topics_count} topic(s) detected. Check whether major course units were omitted.",
                suggested_action="add_topic",
            ))
            score -= 15

        # 2. Module Level Checks
        seen_module_titles = set()
        all_topics_global = []

        for m_idx, mod in enumerate(modules):
            mod_id = mod.get("id") or f"mod_{m_idx+1}"
            mod_title = mod.get("title", f"Module {m_idx+1}")
            topics = mod.get("topics", [])

            # Empty Module
            if not topics:
                warnings.append(ValidationWarning(
                    code="EMPTY_MODULE",
                    severity="high",
                    message=f"Module '{mod_title}' contains no topics.",
                    module_id=mod_id,
                    module_title=mod_title,
                    suggested_action="add_topic",
                ))
                score -= 15

            # Module Title Duplicate
            norm_m_title = re.sub(r"[^\w\s]", "", mod_title.lower()).strip()
            if norm_m_title in seen_module_titles:
                warnings.append(ValidationWarning(
                    code="DUPLICATE_MODULE",
                    severity="medium",
                    message=f"Module title '{mod_title}' appears more than once.",
                    module_id=mod_id,
                    module_title=mod_title,
                    suggested_action="edit",
                ))
                score -= 10
            seen_module_titles.add(norm_m_title)

            # Topic Level Checks within Module
            seen_topic_titles_in_module = set()

            for t_idx, topic in enumerate(topics):
                t_id = topic.get("id") or f"top_{m_idx+1}_{t_idx+1}"
                t_title = topic.get("title", "").strip()
                duration = topic.get("estimated_minutes", 60)

                all_topics_global.append((mod_id, mod_title, t_id, t_title))

                # Check 2a: Short or Empty Topic Title
                if len(t_title) < 3:
                    warnings.append(ValidationWarning(
                        code="EMPTY_TOPIC_TITLE",
                        severity="high",
                        message=f"Topic has an empty or very short title: '{t_title}'.",
                        module_id=mod_id,
                        module_title=mod_title,
                        topic_id=t_id,
                        topic_title=t_title,
                        suggested_action="remove",
                    ))
                    score -= 10
                    continue

                # Check 2b: Metadata Leakage in Topic Title
                for pat in METADATA_SUSPICIOUS_TERMS:
                    if re.search(pat, t_title, re.IGNORECASE):
                        warnings.append(ValidationWarning(
                            code="METADATA_LEAKAGE",
                            severity="high",
                            message=f"Topic '{t_title[:45]}' looks like administrative metadata (e.g. credits, semester, reference) rather than a learning concept.",
                            module_id=mod_id,
                            module_title=mod_title,
                            topic_id=t_id,
                            topic_title=t_title,
                            suggested_action="remove",
                        ))
                        score -= 8
                        break

                # Check 2c: Incomplete Sentence Fragment
                words = t_title.split()
                if words and words[-1].lower() in FRAGMENT_TERMINAL_WORDS:
                    warnings.append(ValidationWarning(
                        code="SENTENCE_FRAGMENT",
                        severity="medium",
                        message=f"Topic '{t_title}' appears to end in an incomplete phrase ('{words[-1]}'). Consider merging it with the next topic.",
                        module_id=mod_id,
                        module_title=mod_title,
                        topic_id=t_id,
                        topic_title=t_title,
                        suggested_action="merge",
                    ))
                    score -= 5

                # Check 2d: Duplicate Topic within Module
                norm_t_title = re.sub(r"[^\w\s]", "", t_title.lower()).strip()
                if norm_t_title in seen_topic_titles_in_module:
                    warnings.append(ValidationWarning(
                        code="DUPLICATE_TOPIC",
                        severity="medium",
                        message=f"Topic '{t_title}' is duplicated within module '{mod_title}'.",
                        module_id=mod_id,
                        module_title=mod_title,
                        topic_id=t_id,
                        topic_title=t_title,
                        suggested_action="remove",
                    ))
                    score -= 6
                seen_topic_titles_in_module.add(norm_t_title)

                # Check 2e: Unreasonable Duration
                if duration < 10 or duration > 180:
                    warnings.append(ValidationWarning(
                        code="UNREASONABLE_DURATION",
                        severity="low",
                        message=f"Topic '{t_title}' has an unusual study duration ({duration}m). Recommended study session is 25-90 minutes.",
                        module_id=mod_id,
                        module_title=mod_title,
                        topic_id=t_id,
                        topic_title=t_title,
                        suggested_action="edit",
                    ))
                    score -= 3

        # Clamp score between 0 and 100
        score = max(0, min(100, score))
        high_severity_count = sum(1 for w in warnings if w.severity == "high")
        needs_confirm = (score < 75) or (high_severity_count > 0) or is_fallback_mode
        is_valid = (total_topics_count > 0) and (score >= 40)

        if is_fallback_mode:
            summary = f"Rule-Based Fallback (Quality Score: {score}/100). Generated via deterministic heuristics without live AI model reasoning. Review topics before proceeding."
        elif score >= 85 and not warnings:
            summary = f"Quality Score: {score}/100. Structure is clean and verified by AI."
        else:
            summary = f"Quality Score: {score}/100. {len(warnings)} potential issue(s) detected. Review flagged items before proceeding."

        return ValidationReport(
            is_valid=is_valid,
            quality_score=score,
            needs_confirmation=needs_confirm,
            total_warnings_count=len(warnings),
            warnings=warnings,
            summary=summary,
        )
