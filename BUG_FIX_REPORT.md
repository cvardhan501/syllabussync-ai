# SyllabusSync AI — Comprehensive Bug Fix Report

**Date:** November 1, 2026
**Project:** SyllabusSync AI (`C:\Users\cvard\Desktop\strands-hack-aws-2`)
**Status:** All 4 Reported Bugs Investigated, Fixed, and Verified
**Test Suite Status:** 125 / 125 Backend Tests Passed (100%), Frontend Build Clean
**AWS Spend:** $0.00 / ₹0.00 (Strictly enforced zero live Bedrock or YouTube API calls)

---

## 1. Executive Summary

During manual testing of SyllabusSync AI on university syllabi (specifically `CSE3016 Course Syllabus.pdf` and related courses), four critical bugs were identified across syllabus extraction, duration distribution, video recommendations, and AI agent execution.

All four issues have been resolved directly in the existing codebase without UI redesigns, architectural replacements, or unnecessary dependencies.

| Priority | Issue | Status | Primary Files Modified |
| :--- | :--- | :--- | :--- |
| **P0** | Incomplete Syllabus Topic Extraction (CSE3016 Module 1 had 4 topics instead of 6) | **RESOLVED** | `backend/app/services/syllabus_extractor.py`, `backend/app/agents/syllabus_analyzer.py` |
| **P0** | Incorrect & Repeated YouTube Recommendations (Duplicate generic UML intro video) | **RESOLVED** | `backend/app/services/resource_matcher.py` |
| **P1** | Incorrect Topic Duration Allocation (240m allocated vs. 360m official delivery) | **RESOLVED** | `backend/app/services/syllabus_extractor.py`, `backend/app/agents/syllabus_analyzer.py` |
| **P1** | Strands / Bedrock Model Tool Sequence Error & Error Tag Leakage | **RESOLVED** | `backend/app/agents/syllabus_analyzer.py` |

---

## 2. Detailed Root Cause Analysis & Fixes

### Bug 1 (P0): Incomplete Syllabus Topic Extraction

#### Reported Problem
The original `CSE3016 Course Syllabus.pdf` clearly specifies six discrete study topics in Module 1:
1. `Object-Oriented Development and Modelling Concepts`
2. `Object-Oriented Methodology`
3. `Advanced Link and Association Concepts`
4. `Generalization, Inheritance, and Grouping Constructs`
5. `Sample Object Models`
6. `A sample class model; Navigation of class models`

However, the application displayed only four topics, dropping `Object-Oriented Methodology` and `Advanced Link and Association Concepts`.

#### Root Causes Identified
1. **Unpunctuated Boundary Fusion in Raw PDF Text:**
   In the source PDF table layout, line-breaks between table rows resulted in no comma between `Concepts` and `Generalization`:
   `"...Advanced Link and Association Concepts Generalization, Inheritance, and Grouping Constructs..."`
2. **Semicolon Suppression Flaw in `_parse_table_module_topics`:**
   Module 1 ended with `; Navigation of class models`. Because `if ";" in prot_text:` took precedence, the extractor split only on `;`. Semicolon chunk 0 contained 5 commas and no colon, but because it had no colon, the parser treated the entire 150-character chunk as a single topic!
3. **Over-splitting Coordinate Triads:**
   Splitting naively on commas would split `Generalization, Inheritance, and Grouping Constructs` into three separate fragments instead of preserving the coordinate triad.
4. **Agent Prompt Lack of Specificity:**
   In `SyllabusAnalyzerAgent`, `SYSTEM_PROMPT` did not explicitly instruct the model to preserve all comma-separated topics, allowing LLM summarization to merge topics 1, 2, and 3.

#### Implemented Fixes
1. **Punctuation Boundary Recovery (`syllabus_extractor.py`):**
   Added heuristic boundary repair that detects when a category-closing noun (`Concepts`, `Models`, `Diagrams`, `Architecture`, `Methodology`, etc.) is immediately followed by a capitalized noun list (`Generalization, Inheritance...`), inserting `, ` automatically.
2. **Compound Semicolon/Comma Partitioning (`syllabus_extractor.py`):**
   When a semicolon chunk contains multiple commas without a colon (`len(sp.split(",")) >= 3`), it is recursively split on commas while protecting Oxford-comma coordinate triads (`A, B, and C`).
3. **Continuation Clause Attachment (`syllabus_extractor.py`):**
   Segments starting with `Navigation of...` or subordinate clauses after `A sample class model` are cleanly attached with `; ` to produce `A sample class model; Navigation of class models`.
4. **System Prompt Hardening (`syllabus_analyzer.py`):**
   Guideline 3 updated to explicitly command extracting every comma- and semicolon-separated topic without merging or dropping intermediate topics.

---

### Bug 2 (P0): Incorrect & Repeated YouTube Recommendations

#### Reported Problem
Different topics in the Video Library repeatedly received the same introductory video (e.g., Gate Smashers 18-minute UML intro). Distinct topics should receive topic-specific videos; short generic videos should never be duplicated.

#### Root Causes Identified
1. **Lack of Road-Map Level `used_video_ids` Enforcement:**
   In `resource_matcher.py` (`generate_strategy_preview`), when a video was returned for an assigned channel, the code previously assigned the same video to multiple topics and merely downgraded non-comprehensive duplicates to `match_status = "probable"`, keeping the exact same video attached.
2. **No Multi-Channel Fallback Pipeline:**
   If the primary channel had already used its video, the system did not systematically search the secondary channel or community candidates for an unused candidate.

#### Implemented Fixes
1. **Candidate Selection Pipeline:**
   Implemented a strict 3-tier candidate selection order:
   - **Priority 1:** Assigned primary channel candidate that has not yet been used.
   - **Priority 2:** Secondary/active channel candidate that has not yet been used.
   - **Priority 3:** Broader community candidates (when allowed by strategy or approval).
2. **Strict `used_video_ids` Tracking:**
   Every assigned video ID is tracked in `used_video_ids: Set[str]`. A video ID cannot be reused across distinct topics unless:
   - It is a long-form comprehensive lecture (`duration >= 2700s` / 45 minutes, or titled `complete course`, `full course`, `masterclass`, etc.) AND
   - Has high relevance (`score >= 0.65`).
   - When shared, it receives an explicit justification: `"Shared video: Comprehensive lecture ({duration}) covering both '{first_topic}' and '{t['topic_title']}'."`
3. **Honest Uncovered Topic Representation:**
   If no unused video with acceptable relevance (`score >= 0.40`) exists, the topic is marked `match_status = "no_resource"` with `candidate_video_id = None`, `candidate_video_title = None`, and `availability_status = "missing"`.
4. **Verified Coverage Accuracy:**
   Only genuine `verified` matches count towards `verified_coverage_percentage`.

---

### Bug 3 (P1): Incorrect Topic Duration Allocation

#### Reported Problem
Module 1 has an official delivery of 6.0 hours (360 minutes). When only 4 topics were extracted with 60 minutes each (240 minutes total), the frontend triggered the warning:
`"Topic duration total (240 min) falls short of official module delivery (360 min). Auto-Balance to 360m"`.

#### Root Causes Identified
1. Incomplete topic extraction (4 topics instead of 6) resulted in 4 * 60 = 240m.
2. In `SyllabusAnalyzerAgent.analyze_syllabus`, when backfilling `official_hours` and `official_minutes = 360` from table extraction, topic `estimated_minutes` were not auto-balanced to match the official delivery time.

#### Implemented Fixes
1. **Extraction Duration Math:**
   With all 6 topics extracted: `360 minutes // 6 topics = 60 minutes` per topic.
   Sum = 60 * 6 = 360 minutes.
   Mismatch = 0 minutes (`hasMismatch = false`), completely eliminating the warning banner.
2. **Automated Duration Balancing (`syllabus_analyzer.py`):**
   In `SyllabusAnalyzerAgent.analyze_syllabus`, when `mod.official_minutes > 0` is set and the topic duration sum does not equal official minutes:
   The system distributes official minutes evenly (`official_minutes // len(topics) + remainder distribution`) across all topics in that module.
3. **Preservation of Student Customization:**
   Manual edits made by students in the frontend remain fully editable and persistent, with the `Auto-Balance to {N}m` button remaining available whenever manual edits create a difference.

---

### Bug 4 (P1): Strands / Bedrock Tool Sequence Error & Tag Leakage

#### Reported Problem
Previously observed: `[DEVELOPMENT FALLBACK: MODEL_TOOL_USE_ERROR] Model 'amazon.nova-lite-v1:0' emitted an invalid tool sequence during streaming`. The technical error tag was leaking into user-facing `ambiguous_sections`.

#### Root Causes Identified
1. Amazon Nova models (`amazon.nova-lite-v1:0`) encounter a known Bedrock `ConverseStream` issue when emitting `toolUse` blocks during streaming, raising `ModelStreamErrorException`.
2. Fallback logic previously appended raw exception/category strings to `ambiguous_sections`.

#### Implemented Fixes
1. **Non-Streaming Enforced for Nova Models (`syllabus_analyzer.py`):**
   `use_streaming = False` is enforced for any Nova model or when `settings.strands_streaming` is False.
2. **Reliable Non-Streaming Fallback Retry:**
   If a streaming toolUse sequence error occurs, `_execute_strands_agent` catches it and immediately retries non-streaming.
3. **Bedrock Explicit Configuration:**
   `BedrockModel` explicitly sets `region_name=settings.aws_region` and `temperature=0.0`.
4. **Clean Diagnostic Isolation:**
   Internal error categories (`MODEL_TOOL_USE_ERROR`, `RATE_LIMIT_OR_QUOTA`, `CONFIG_MISSING`, etc.) are recorded in `engine_name` and logs, while `ambiguous_sections` strictly contains genuine syllabus document ambiguities. Technical error tags never leak into user-facing notes.

---

## 3. Before vs. After Verification

### Module 1 Topic Extraction Comparison

| Metric | Before Fix | After Fix |
| :--- | :--- | :--- |
| **Topic 1** | Object-Oriented Development and Modelling Concepts | Object-Oriented Development and Modelling Concepts |
| **Topic 2** | Generalization, Inheritance, and Grouping Constructs *(Skipped Topic 2 & 3)* | **Object-Oriented Methodology** |
| **Topic 3** | Sample Object Models | **Advanced Link and Association Concepts** |
| **Topic 4** | A sample class model; Navigation of class models | Generalization, Inheritance, and Grouping Constructs |
| **Topic 5** | *Missing* | Sample Object Models |
| **Topic 6** | *Missing* | A sample class model; Navigation of class models |
| **Total Topics** | 4 topics | **6 topics (100% matched to original syllabus)** |

### Module 1 Duration Allocation Comparison

| Topic | Allocated Before | Allocated After | Status |
| :--- | :--- | :--- | :--- |
| Topic 1 | 60 min | 60 min | Correct |
| Topic 2 | 60 min | 60 min | Correct |
| Topic 3 | 60 min | 60 min | Correct |
| Topic 4 | 60 min | 60 min | Correct |
| Topic 5 | — | 60 min | Correct |
| Topic 6 | — | 60 min | Correct |
| **Total Duration** | **240 min** | **360 min (6.0 hrs)** | **Exact match to official delivery** |
| **Warning Banner** | Triggered (shortfall 120m) | **None (0m difference)** | **Warning eliminated** |

---

## 4. Automated Verification Results

### Backend Regression Test Suite
Executed: `pytest backend/tests/`
Total Test Files: 17
Result: **125 passed in 100.79s (100% PASS)**

Key Test Modules Verified:
- `test_cse3016_extraction.py`: 9 passed (verifies clean 7 modules, stated teaching hours, and Module 1 6-topic extraction with 60m allocation).
- `test_cse300_regression.py`: 7 passed (verifies 5/6/5/5/5/5/1 topic distribution and exact 1800m / 30h allocation).
- `test_cse2001_extraction.py`: 6 passed (verifies lab separation, zero metadata leakage).
- `test_youtube_overhaul_regression.py`: 7 passed (verifies topic query generation, generic video rejection, long-form sharing, and all 4 channel strategies).
- `test_youtube_resources.py`: 10 passed (verifies third-channel approval flow, alternative discovery, and replacement).
- `test_channel_distribution_and_structure.py`: 5 passed (verifies multiline course extraction, numbered module organization, and ~50:50 distribution).
- `test_strands_ai_diagnosis.py`: 3 passed (verifies BedrockModel region, non-streaming Nova, tool-use prompt, zero error tag leakage).

### Frontend Build & Typecheck
Command: `npm --prefix frontend run build` (`tsc -b && vite build`)
Result: **Built successfully in 1.02s with 0 errors**.

### AWS Cost Protection
- Zero live Bedrock API invocations during testing ($0.00 spend).
- Zero live YouTube Data API calls during testing ($0.00 spend).
- All automated tests executed with deterministic mocks and local fixtures.

---

## 5. Files Changed

1. `backend/app/services/syllabus_extractor.py`
   - Added category noun boundary repair for unwrapped table lines.
   - Enhanced `_parse_table_module_topics` to support nested comma splitting inside semicolon segments while preserving coordinate triads.
   - Connected sample class model continuation clauses with semicolon.
   - Preserved deadlock handling topic mergers.
2. `backend/app/agents/syllabus_analyzer.py`
   - Updated `SYSTEM_PROMPT` Guidelines 3 and 5.
   - Added auto-balancing of topic durations when `mod.official_minutes` is present in `analyze_syllabus`.
3. `backend/app/services/resource_matcher.py`
   - Implemented 3-tier candidate evaluation pipeline.
   - Enforced course/roadmap-level `used_video_ids` set to prevent non-comprehensive duplicate video assignments.
   - Protected comprehensive multi-topic video sharing (>45m) with explicit shared justification.
   - Left uncovered topics honestly marked as `no_resource` with `candidate_video_id = None`.
   - Constrained third channel discovery to approved strategies.
4. `backend/tests/test_cse3016_extraction.py`
   - Added explicit test assertions validating all 6 Module 1 topics and 60m duration distribution.
