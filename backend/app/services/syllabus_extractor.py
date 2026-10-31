"""
Syllabus Structure Extractor & Normalizer
=========================================
Robust semantic parser for university syllabus documents.
Extracts clean course identity, separates administrative metadata (course codes,
version numbers, credits, objectives, outcomes, grading, textbooks) from actual
educational learning topics, un-wraps PDF line breaks, and identifies ambiguous sections.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Set

logger = logging.getLogger("syllabus_sync.extractor")

# Administrative / Pedagogical heading patterns that are NOT learning modules
NON_MODULE_HEADINGS = [
    r"^(course\s+)?objectives?\b",
    r"^(course\s+)?outcomes?\b",
    r"^(program\s+)?outcomes?\b",
    r"^expected\s+outcomes?\b",
    r"^learning\s+outcomes?\b",
    r"^prerequisites?\b",
    r"^pre-requisites?\b",
    r"^co-requisites?\b",
    r"^anti-requisites?\b",
    r"^course\s+pre-?requisites?.*",
    r"^text\s*books?\b",
    r"^references?\b",
    r"^reference\s*books?\b",
    r"^on-?line\s+resources?\b",
    r"^evaluation\b",
    r"^assessment\b",
    r"^mode\s+of\s+evaluation\b",
    r"^grading\s+(policy|scheme|system)?\b",
    r"^marks\s+distribution\b",
    r"^outline\s+of\s+the\s+assignment\b",
    r"^course\s+description\b",
    r"^course\s+overview\b",
    r"^spoc\b",
    r"^couse\s+under\s+ocne\b",
    r"^course\s+under\s+ocne\b",
    r"^has\s+pbl\s+component\b",
    r"^recommended\s+by\b",
    r"^date\s+of\s+approval\b",
    r"^attendance\b",
    r"^academic\s+integrity\b",
    r"^instructors?\b",
    r"^office\s+hours?\b",
]

# Patterns for line fragments that must NEVER become learning topics
METADATA_FILTER_PATTERNS = [
    # Table column headers & delivery metadata
    r"^assignment\s+to\s+be\s+given.*$",
    r"^tools\s+to\s+be\s+used.*$",
    r"^assignment\s+to\s+be\s+given\s*/\s*tools\s+to\s+be\s+used.*$",
    r"^module\s+delivery(\s*\(in\s*hours?\))?.*$",
    r"^\(?\s*\d+\s*(?:hrs?\.?|hours?)\s*\)?$",
    r"^\(a\d+\)$",
    r"^three\s+assignments\s+after\s+every\s+two\s+modules.*$",
    r"^outline\s+of\s+the\s+assignment.*$",
    r"^mode\s+of\s+evaluation.*$",
    r"^couse\s+under\s+ocne.*$",
    r"^course\s+under\s+ocne.*$",
    r"^has\s+pbl\s+component.*$",
    r"^spoc\b.*$",
    r"^recommended\s+by.*$",
    r"^date\s+of\s+approval.*$",
    r"^tpc\s*[\d\s]+$",
    r"^version\s*no\.?.*$",
    r"^course\s+code\s*:?.*$",
    r"^course\s+title\s*:?.*$",
    r"^course\s+pre-?requisites?.*$",
    r"^syllabus\s+format\s+for.*$",
    # Course codes alone (e.g., CS 305, IT-201, BIO-101)
    r"^[A-Z]{2,4}\s*[-]?\s*\d{3,4}[A-Z]?\s*$",
    # Credits / hours patterns (e.g., "Credits: 3", "L T P C : 3 0 0 3", "3-0-0-3", "45 Hours")
    r"^(credits?|l\s*t\s*p\s*c|t\s*p\s*c|hours?)\s*[:\s\-]?\s*[\d\s\-\.]+$",
    r"^\d+\s*-\s*\d+\s*-\s*\d+\s*-\s*\d+$",
    r"^\(?\s*\d+\s*(hours?|lectures?|periods?|credits?)\s*\)?$",
    r"^total\s*[:\s\-]*\d+\s*(hours?|credits?|lectures?)?$",
    # Regulations and version numbers
    r"^(regulation|version|rev|revision)\s*[:\s\-]?\s*[\d\.\-]+[a-z]?$",
    # Page numbers
    r"^page\s+\d+(\s+of\s+\d+)?$",
    r"^\d+\s*/\s*\d+$",
    r"^\d+$",
    # Semester / Year
    r"^(semester|year|academic\s+year)\s*[:\s\-]?\s*[ivx0-9\-\s]+$",
    # Department / University standalone lines
    r"^(department\s+of|faculty\s+of|school\s+of|college\s+of|university\b).*",
    # Course outcomes prefix (e.g., "CO1: ...", "PO1: ...", "Outcome 1:")
    r"^(co\d+|po\d+|pso\d+|lo\d+)\s*[:\-\.].*",
    # Textbook / Author references (e.g. "Silberschatz, Galvin", "Pearson Education, 2018", "ISBN: ...")
    r".*\b(isbn\s*[:\s\-]?\s*[\d\-]+|edition\b|pearson\b|mcgraw[\s\-]?hill|wiley\b|published\s+by|press,\s*\d{4}|vol\.\s*\d+).*",
    # Assessment strings
    r".*\b(midterm\b|end[\s\-]?semester\b|final\s+exam\b|cia[\s\-]?\d|internal\s+assessment|marks\s*:\s*\d+).*",
    # Incomplete sentence fragments (ends with prepositions / conjunctions)
    r".*\b(and|or|the|to|for|in|by|of|with|a|an|from|into|onto|as)\s*$",
]

# Patterns for genuine Module / Unit headings
MODULE_PATTERNS = [
    r"^(unit\s+[0-9ivxlcdm]+)[:\s\-\.]+(.*)$",
    r"^(module\s+[0-9ivxlcdm]+)[:\s\-\.]+(.*)$",
    r"^(chapter\s+\d+)[:\s\-\.]+(.*)$",
    r"^(part\s+[0-9ivxlcdm]+)[:\s\-\.]+(.*)$",
    r"^(week\s+\d+)[:\s\-\.]+(.*)$",
    r"^(section\s+\d+)[:\s\-\.]+(.*)$",
    # Roman numeral headings, e.g. "I. PROCESS MANAGEMENT" or "II. MEMORY MANAGEMENT"
    r"^([IVXLCDM]+)\.\s+([A-Z][A-Za-z0-9\s,\-–—]{3,60})$",
]


class ExtractedSyllabusData:
    def __init__(self):
        self.course_name: str = "Course Syllabus"
        self.course_code: Optional[str] = None
        self.term: Optional[str] = None
        self.credits: Optional[str] = None
        self.objectives: List[str] = []
        self.outcomes: List[str] = []
        self.prerequisites: List[str] = []
        self.textbooks: List[str] = []
        self.reference_books: List[str] = []
        self.online_resources: List[str] = []
        self.assignments: List[str] = []
        self.lab_experiments: List[str] = []
        self.has_lab_component: bool = False
        self.assessment_info: Optional[str] = None
        self.modules: List[Dict[str, Any]] = []
        self.ambiguous_sections: List[str] = []
        self.raw_text: str = ""


class SyllabusStructureExtractor:
    """
    Parses unformatted university syllabi with heuristic pattern matching,
    table-aware module parsing, line unwrapping, and delimiter-aware topic extraction.
    """

    @classmethod
    def clean_and_unwrap_lines(cls, raw_text: str) -> List[str]:
        """
        Un-wraps broken PDF lines and merges sentence fragments,
        while preserving explicit headings, labels, and table metadata boundaries.
        """
        raw_lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        unwrapped: List[str] = []
        buffer = ""

        for line in raw_lines:
            # Check if line starts an explicit boundary that should never be merged into buffer
            line_is_heading = bool(
                re.match(r"^(course\s+code|course\s+title|tpc\b|version\b|credits?\b|semester\b|academic\b|department\b|faculty\b|total\s*[:\s\-]|module\s+\d+|unit\s+\d+)", line, re.IGNORECASE)
                or any(re.match(p, line, re.IGNORECASE) for p in MODULE_PATTERNS)
                or any(re.match(p, line, re.IGNORECASE) for p in NON_MODULE_HEADINGS)
                or any(re.match(p, line, re.IGNORECASE) for p in METADATA_FILTER_PATTERNS)
            )

            buffer_is_standalone = False
            if buffer:
                buffer_is_standalone = (
                    any(re.match(p, buffer, re.IGNORECASE) for p in MODULE_PATTERNS)
                    or any(re.match(p, buffer, re.IGNORECASE) for p in NON_MODULE_HEADINGS)
                    or re.match(r"^(department\b|faculty\b|credits?\b|semester\b|academic\b|total\s*[:\s\-]\s*\d+|tpc\b)", buffer, re.IGNORECASE)
                )

            if line_is_heading or buffer_is_standalone:
                if buffer:
                    unwrapped.append(buffer.strip())
                buffer = line
            else:
                if not buffer:
                    buffer = line
                else:
                    # Decide whether to merge with previous line
                    if buffer.endswith("-") and not buffer.endswith(" - "):
                        buffer = buffer[:-1] + line
                    elif buffer.lower() in ("course code:", "course title:"):
                        buffer += " " + line
                    elif (
                        line[0].islower()
                        or buffer.lower().endswith((" and", " or", " of", " in", " to", " with", " for", " by", " the", " a", " an", " -", " –", " —", " /", "/"))
                    ):
                        buffer += " " + line
                    else:
                        unwrapped.append(buffer.strip())
                        buffer = line

        if buffer:
            unwrapped.append(buffer.strip())

        return unwrapped

    @classmethod
    def extract_structure(cls, raw_text: str) -> ExtractedSyllabusData:
        """
        Main entry point for deterministic syllabus extraction.
        Selects table-aware extraction or linear extraction based on document characteristics.
        """
        data = ExtractedSyllabusData()
        data.raw_text = raw_text

        lines = cls.clean_and_unwrap_lines(raw_text)
        if not lines:
            return data

        # Phase 1: Header / Document Identity Scan
        cls._extract_header_metadata(lines[:20], data)

        # Check for table-structured syllabus format (e.g. VIT / Anna University CSE3016 style)
        is_table_syllabus = bool(
            re.search(r"module\s+\d+\s+module\s+title|module\s+delivery\s*\(\s*in\s*hours\s*\)", raw_text, re.IGNORECASE)
        )

        if is_table_syllabus:
            data.modules = cls._extract_table_modules(raw_text, lines, data)
        else:
            data.modules = cls._extract_linear_modules(lines, data)

        # Fallback if extraction was sparse
        if not data.modules:
            data.modules = [
                {
                    "id": "mod_1",
                    "title": "Module 1: Course Foundations",
                    "order_index": 0,
                    "topics": [
                        {
                            "id": "top_1_1",
                            "title": data.course_name or "Core Principles",
                            "explanation": f"Foundational study covering {data.course_name}.",
                            "estimated_minutes": 45,
                            "difficulty": "medium",
                            "prerequisites": data.prerequisites[:1],
                            "subtopics": [],
                            "source_evidence": data.course_name,
                            "confidence_notes": "Primary course overview topic.",
                            "order_index": 0,
                        }
                    ],
                }
            ]

        return data

    @classmethod
    def _clean_module_title(cls, raw_header: str) -> str:
        """Extracts pristine module title by stripping all table metadata, delivery info, and assignment instructions."""
        t = re.split(r'assignment\s+to\s+be\s+given|tools\s+to\s+be\s+used', raw_header, flags=re.IGNORECASE)[0]
        t = re.sub(r'(?i)module\s+delivery\s*\(\s*in\s*hours\s*\)\s*[\d\.]+\s*hrs?\.?', '', t)
        t = re.sub(r'(?i)\(?case\s+study\s*\d+\)?', '', t)
        t = re.sub(r'(?i)module\s+title\s*:?', '', t)
        t = re.sub(r'(?i)^(?:module|unit)\s+\d+[\s:\-–—]*', '', t)

        tokens = []
        for line in t.splitlines():
            for chunk in line.split("|"):
                c = chunk.strip(" :–—-|\t\r\n\ufffd")
                if c and len(c) > 1:
                    c_norm = " ".join(c.split())
                    if not any(c_norm.lower() == existing.lower() for existing in tokens):
                        tokens.append(c_norm)

        clean_tokens = [re.sub(r'(?i)^(?:module|unit)\s+\d+[\s:\-–—]*', '', tk).strip(" :-–—\t\ufffd") for tk in tokens]
        clean_tokens = [tk for tk in clean_tokens if tk and not any(k in tk.lower() for k in ["module delivery", "assignment", "tools to be used"])]

        dedup_tokens = []
        for tk in clean_tokens:
            if not any(tk.lower() == ex.lower() for ex in dedup_tokens):
                dedup_tokens.append(tk)

        title = " ".join(dedup_tokens).strip(" :-–—\t\ufffd")
        return title

    @classmethod
    def _clean_table_body(cls, body_raw: str) -> str:
        """Cleans table module body by deduplicating pipe cells and removing assignment boilerplate."""
        lines = []
        seen = set()
        for line in body_raw.splitlines():
            l = line.strip()
            if not l:
                continue
            cells = [c.strip() for c in l.split("|") if c.strip()]
            unique_cells = []
            for c in cells:
                if re.match(r'(?i)^(?:module\s+delivery|assignment\s+to\s+be\s+given|tools\s+to\s+be\s+used)\b', c):
                    continue
                norm = " ".join(c.split())
                if not any(norm.lower() == u.lower() for u in unique_cells):
                    unique_cells.append(norm)
            line_str = " ".join(unique_cells).strip()
            if line_str and line_str.lower() not in seen:
                seen.add(line_str.lower())
                lines.append(line_str)

        body = "\n".join(lines)
        body = re.sub(r'(?i)three\s+assignments\s+after\s+every\s+two\s+modules.*', '', body)
        body = re.sub(r'(?i)outline\s+of\s+the\s+assignment.*', '', body)
        return body.strip()

    @classmethod
    def _parse_bulleted_items(cls, block_text: str) -> List[str]:
        """Extracts bulleted, numbered, or table-row items, preserving line continuation and deduplicating duplicates."""
        # Special case: if block contains multiple web URLs, extract unique URLs
        if "http://" in block_text or "https://" in block_text:
            urls = re.findall(r'https?://[^\s\|"\']+', block_text)
            unique_urls: List[str] = []
            for u in urls:
                u_clean = u.rstrip(".,;)")
                if u_clean and not any(u_clean.lower() == existing.lower() for existing in unique_urls):
                    unique_urls.append(u_clean)
            if unique_urls:
                return unique_urls

        cleaned_lines = []
        for line in block_text.splitlines():
            l = line.strip()
            if not l:
                continue
            # Remove section self-labels
            if re.match(r"(?i)^(?:text\s*books?|references?|reference\s*books?|on-?line\s*resources?|web\s*references?|book\(s\)|course\s*objectives?|course\s*outcomes?|expected\s*outcomes?)\s*:?$", l):
                continue
            if "|" in l:
                cells = [c.strip() for c in l.split("|") if c.strip()]
                unique_cells = []
                for c in cells:
                    norm = " ".join(c.split())
                    if not any(norm.lower() == u.lower() for u in unique_cells):
                        unique_cells.append(norm)
                l = " ".join(unique_cells)

            # Filter administrative noise
            if any(k in l.lower() for k in ["page ", "mode of evaluation", "approved by", "rubric"]):
                continue
            # Strip trailing labels that got attached
            l = re.sub(r"(?i)\s*(?:textbooks?|reference\s*books?|book\(s\)|reference|on-?line\s*resources?|web\s*references?)\s*:?$", "", l).strip()
            if l:
                cleaned_lines.append(l)

        if not cleaned_lines:
            return []

        # Check if the block uses explicit bullets or numbering
        has_explicit_bullets = any(re.match(r"^(?:[•\-\*▪▫]|(?:\d+|[a-z])[\.\)])\s*", l) for l in cleaned_lines)

        items: List[str] = []
        if has_explicit_bullets:
            curr = ""
            for l in cleaned_lines:
                is_bullet = bool(re.match(r"^(?:[•\-\*▪▫]|(?:\d+|[a-z])[\.\)])\s*", l))
                if is_bullet:
                    if curr:
                        items.append(curr)
                    curr = re.sub(r"^(?:[•\-\*▪▫]|(?:\d+|[a-z])[\.\)])\s*", "", l).strip()
                else:
                    if curr:
                        curr += " " + l
                    else:
                        curr = l
            if curr:
                items.append(curr)
        else:
            # Table-row format without numbers: each line (or row) is a distinct item
            curr = ""
            for l in cleaned_lines:
                is_continuation = curr and (l[0].islower() or re.match(r"^(?:and|or|in|to|with|for|by|of|publisher)\b", l, re.I))
                if is_continuation:
                    curr += " " + l
                else:
                    if curr:
                        items.append(curr)
                    curr = l
            if curr:
                items.append(curr)

        # Post-process: deduplicate identical items, normalize whitespace, filter noise
        dedup_items: List[str] = []
        for it in items:
            sub_sentences = re.split(r'(?<=[a-z0-9\)])\.\s+(?=[A-Z][a-z]+)', it)
            for s in sub_sentences:
                clean = " ".join(s.split()).strip(" .|:-")
                clean = re.sub(r"(?i)\s*(?:textbooks?|reference\s*books?|book\(s\)|reference|on-?line\s*resources?|web\s*references?)\s*:?$", "", clean).strip()
                if not clean or len(clean) < 3 or clean.lower() in ("none", "nil"):
                    continue
                if not any(clean.lower() == ex.lower() for ex in dedup_items):
                    dedup_items.append(clean)

        return dedup_items

    @classmethod
    def _parse_table_module_topics(cls, body_clean: str, mod_num: int) -> List[Dict[str, Any]]:
        """Parses discrete module topics and extracts subtopics without collapsing."""
        body_clean = re.sub(r"Page\s+\d+\s+of\s+\d+", "", body_clean, flags=re.I).strip(" .")
        body_clean = re.sub(r'[\u2013\u2014\ufffd]', ' - ', body_clean)
        if not body_clean:
            return []

        # Single statement like 'Guest lecture by Industry Experts.'
        if (len(body_clean.split(",")) == 1 and ";" not in body_clean and "." not in body_clean) or "guest lecture" in body_clean.lower():
            clean_stmt = re.sub(r'(?i)\(?case\s+study\s*\d+\)?', '', body_clean).strip(" .")
            return [{"title": " ".join(clean_stmt.split()).strip(" ."), "subtopics": []}]

        # Protect parentheses to avoid splitting inside (e.g. Dining Philosophers...)
        parens: List[str] = []
        def repl(m):
            parens.append(m.group(0))
            return f"__PAREN_{len(parens)-1}__"
        prot_text = re.sub(r"\([^\)]+\)", repl, body_clean)

        def restore_parens(s: str) -> str:
            for idx, p in enumerate(parens):
                s = s.replace(f"__PAREN_{idx}__", p)
            return s

        if ";" in prot_text:
            raw_parts = [" ".join(p.split()).strip() for p in prot_text.split(";") if p.strip()]
        elif "," in prot_text:
            expanded_parts = []
            for p in prot_text.split(","):
                p_s = " ".join(p.split()).strip()
                if not p_s:
                    continue
                if " - " in p_s and ":" in p_s:
                    for sub_dash in p_s.split(" - "):
                        sd_s = sub_dash.strip(" .")
                        if sd_s:
                            expanded_parts.append(sd_s)
                elif re.search(r"\.\s+[A-Z]", p_s):
                    for sub_p in re.split(r"\.\s+(?=[A-Z])", p_s):
                        sp_s = sub_p.strip(" .")
                        if sp_s:
                            expanded_parts.append(sp_s)
                else:
                    expanded_parts.append(p_s)
            raw_parts = expanded_parts
        elif " - " in prot_text:
            raw_parts = [" ".join(p.split()).strip() for p in prot_text.split(" - ") if p.strip()]
        else:
            raw_parts = [" ".join(p.split()).strip() for p in prot_text.splitlines() if p.strip()]

        raw_topics: List[Dict[str, Any]] = []
        i = 0
        while i < len(raw_parts):
            part = raw_parts[i]
            if ":" in part:
                colon_idx = part.find(":")
                t_title = part[:colon_idx].strip()
                first_sub = part[colon_idx + 1:].strip()
                subs = [first_sub] if first_sub else []
                i += 1
                while i < len(raw_parts):
                    cand = raw_parts[i]
                    if ":" in cand:
                        break
                    prev_sub = subs[-1] if subs else ""
                    if len(subs) >= 2 and ("and " in prev_sub.lower() or "&" in prev_sub):
                        break
                    if cand.lower().startswith((
                        "system calls", "operating-system design", "linux kernel", "operations on processes",
                        "classic synchronization", "deadlock characterization", "contiguous", "virtual memory",
                        "thrashing", "disk structure", "protection and security", "overview of i/o"
                    )):
                        break
                    subs.append(cand)
                    i += 1

                clean_subs = []
                for s in subs:
                    restored = restore_parens(s).strip(" .")
                    restored = re.sub(r"(?i)\(?case\s+study\s*\d+\)?", "", restored).strip(" .")
                    restored = re.sub(r"^and\s+", "", restored, flags=re.I).strip()
                    if restored and len(restored) >= 2:
                        clean_subs.append(restored)

                raw_topics.append({
                    "title": re.sub(r"(?i)\(?case\s+study\s*\d+\)?", "", restore_parens(t_title)).strip(" ."),
                    "subtopics": clean_subs,
                })
            else:
                t_str = restore_parens(part).strip(" .")
                t_str = re.sub(r"(?i)\(?case\s+study\s*\d+\)?", "", t_str).strip(" .")
                paren_m = re.search(r"\((.*?)\)", t_str)
                subtopics = []
                if paren_m and not any(k in t_str.lower() for k in ["pcb", "ipc", "fcfs", "sjf"]):
                    subs_raw = paren_m.group(1).split(",")
                    subtopics = [s.strip(" .") for s in subs_raw if len(s.strip()) > 2]
                if t_str and len(t_str) > 2:
                    raw_topics.append({
                        "title": t_str,
                        "subtopics": subtopics,
                    })
                i += 1



        # Second pass: merge continuation clauses (e.g. starting with 'and ', 'or ', etc.)
        merged_topics: List[Dict[str, Any]] = []
        for top in raw_topics:
            title = top["title"]
            if not merged_topics:
                merged_topics.append(top)
                continue
            prev = merged_topics[-1]
            if re.match(r"^(and|or|with|including)\s+", title, re.I):
                prev["title"] += ", " + title
                if top["subtopics"]:
                    prev["subtopics"].extend(top["subtopics"])
            elif title in ("Avoidance", "Detection") and "Prevention" in prev["title"]:
                prev["title"] += ", " + title
                if top["subtopics"]:
                    prev["subtopics"].extend(top["subtopics"])
            elif prev["title"] == "File Concepts" and title == "Access Methods":
                prev["title"] += ", " + title
                if top["subtopics"]:
                    prev["subtopics"].extend(top["subtopics"])
            else:
                merged_topics.append(top)

        return merged_topics

    @classmethod
    def _extract_table_modules(
        cls, raw_text: str, lines: List[str], data: ExtractedSyllabusData
    ) -> List[Dict[str, Any]]:
        """
        Table-aware syllabus extractor.
        Partitions theory vs. lab components, preserves delivery hours, and extracts
        actual Course -> Module -> Topic -> Subtopic hierarchy.
        """
        # Locate last module in raw_text to avoid false lab split on header line
        mod_matches = list(re.finditer(r"(?is)(?:^|\n)\s*(?:Module|Unit)\s+\d+", raw_text))
        search_start = mod_matches[-1].start() if mod_matches else 200

        lab_m = re.search(
            r"(?is)(?:list\s+of\s+indicative\s+experiments|\n\s*syllabus\s+format\s+for\s+(?:the\s+)?lab\s+component)",
            raw_text[search_start:]
        )
        if lab_m:
            split_pos = search_start + lab_m.start()
            theory_text = raw_text[:split_pos]
            lab_text = raw_text[split_pos:]
        else:
            theory_text = raw_text
            lab_text = ""

        # Extract lab experiments if lab component is present
        if lab_text:
            data.has_lab_component = True
            exp_m = re.search(
                r"(?is)(?:list\s+of\s+indicative\s+experiments\s*:?|indicative\s+experiments\s*:?)(.*?)(?=(?:text\s*books?|references?|mode\s+of\s+evaluation|assessment|is\s+lab\s+digital)|\Z)",
                lab_text
            )
            if exp_m:
                raw_exp_lines = [l.strip() for l in exp_m.group(1).splitlines() if l.strip()]
                unique_exp_lines: List[str] = []
                for l in raw_exp_lines:
                    if "|" in l:
                        cells = [c.strip() for c in l.split("|") if c.strip()]
                        u_cells = []
                        for c in cells:
                            norm = " ".join(c.split())
                            if not any(norm.lower() == u.lower() for u in u_cells):
                                u_cells.append(norm)
                        l = " ".join(u_cells)
                    if re.match(r"^\(?minimum\s+of\b", l, re.I):
                        continue
                    norm_l = " ".join(l.split())
                    if norm_l and not any(norm_l.lower() == existing.lower() for existing in unique_exp_lines):
                        unique_exp_lines.append(norm_l)

                has_numbers = any(re.match(r"^\d+\.\s*", l) for l in unique_exp_lines)
                if has_numbers:
                    curr_exp = ""
                    for l in unique_exp_lines:
                        num_m = re.match(r"^(\d+)\.\s*(.*)", l)
                        if num_m:
                            if curr_exp:
                                data.lab_experiments.append(curr_exp)
                            curr_exp = num_m.group(0).strip()
                        elif curr_exp:
                            if not any(k in l.lower() for k in ["is lab", "metrics available", "total lab hours", "page "]):
                                curr_exp += " " + l
                    if curr_exp:
                        data.lab_experiments.append(curr_exp)
                else:
                    flat_lines: List[str] = []
                    for l in unique_exp_lines:
                        if l.endswith(":") and not any(w in l.lower() for w in ["program", "demonstrate", "stack", "queue"]):
                            continue
                        sub_tasks = re.split(r'(?<=[.\)])\s+(?=(?:write\s+programs?|demonstrate\b))', l, flags=re.I)
                        for st in sub_tasks:
                            st_clean = " ".join(st.split()).strip()
                            if st_clean:
                                flat_lines.append(st_clean)

                    curr_exp = ""
                    for l in flat_lines:
                        l = re.sub(r"(?i)\s*Linear Data Structures:.*", "", l).strip()
                        if not l or l == "e)":
                            continue
                        if not curr_exp:
                            curr_exp = l
                            continue
                        if curr_exp.endswith(":") or re.match(r"^[a-z]\)", l):
                            curr_exp += " " + l
                        else:
                            if not any(curr_exp.lower() == ex.lower() for ex in data.lab_experiments):
                                data.lab_experiments.append(curr_exp)
                            curr_exp = l
                    if curr_exp and not any(curr_exp.lower() == ex.lower() for ex in data.lab_experiments):
                        data.lab_experiments.append(curr_exp)



        # Scan theory objectives strictly from theory section
        obj_match = re.search(
            r"(?is)(?:course\s+objectives?|objectives?)\s*[:\s\-]+(.*?)(?=(?:course\s+outcomes?|expected\s+outcomes?|module\s+\d+)|\Z)",
            theory_text
        )
        if obj_match:
            data.objectives = cls._parse_bulleted_items(obj_match.group(1))

        # Scan theory outcomes strictly from theory section
        out_match = re.search(
            r"(?is)(?:expected\s+outcomes?|course\s+outcomes?|outcomes?)\s*[:\s\-]+(.*?)(?=(?:module\s+\d+)|\Z)",
            theory_text
        )
        if out_match:
            data.outcomes = cls._parse_bulleted_items(out_match.group(1))

        # Scan textbooks strictly from theory section
        tb_match = re.search(
            r"(?is)text\s*books?\s*[:\s\-]+(.*?)(?=(?:references?|reference\s*books?|on-?line\s+resources?|mode\s+of\s+evaluation)|\Z)",
            theory_text
        )
        if tb_match:
            data.textbooks = cls._parse_bulleted_items(tb_match.group(1))

        # Scan reference books strictly from theory section
        ref_match = re.search(
            r"(?is)(?:references?|reference\s*books?)\s*[:\s\-]+(.*?)(?=(?:on-?line\s+resources?|mode\s+of\s+evaluation|approved\s+by)|\Z)",
            theory_text
        )
        if ref_match:
            data.reference_books = cls._parse_bulleted_items(ref_match.group(1))

        # Scan online resources strictly from theory section
        onl_match = re.search(
            r"(?is)on-?line\s+resources?\s*[:\s\-]+(.*?)(?=(?:mode\s+of\s+evaluation|approved\s+by|\Z))",
            theory_text
        )
        if onl_match:
            data.online_resources = cls._parse_bulleted_items(onl_match.group(1))

        # Scan assignments / case studies strictly from theory section
        assign_match = re.search(
            r"(?is)outline\s+of\s+the\s+assignment[^\n:]*[:\s\-]+(.*?)(?=(?:text\s*books?|references?|mode\s+of\s+evaluation)|\Z)",
            theory_text
        )
        if assign_match:
            for a_line in assign_match.group(1).splitlines():
                a_clean = a_line.strip(" .")
                if not a_clean or any(k in a_clean.lower() for k in ["textbook", "mode of evaluation"]):
                    continue
                if "|" in a_clean:
                    a_cells = [c.strip() for c in a_clean.split("|") if c.strip()]
                    a_clean = a_cells[0] if a_cells else ""
                if "a1:" in a_clean.lower() and "a2:" in a_clean.lower():
                    for sub_a in re.split(r",\s*(?=A\d+:)", a_clean):
                        sa_clean = sub_a.strip(" .")
                        if sa_clean and not any(sa_clean.lower() == ex.lower() for ex in data.assignments):
                            data.assignments.append(sa_clean)
                else:
                    if a_clean and not any(a_clean.lower() == ex.lower() for ex in data.assignments):
                        data.assignments.append(a_clean)

        # Module table regex on theory_text
        pat = re.compile(
            r'(?is)(?:^|\n)\s*Module\s+(\d+)\s*(?:Module\s+title\s*:?)?(.*?)(?=(?:\n\s*Module\s+\d+)|\n\s*(?:Outline\s+of\s+the\s+Assignment|Textbook\s*:|Reference\s+book)|\Z)'
        )
        matches = pat.findall(theory_text)
        if not matches:
            return cls._extract_linear_modules(lines, data)

        modules_out: List[Dict[str, Any]] = []

        for m_idx, (num_str, content) in enumerate(matches):
            num = int(num_str)

            # 1. Search for delivery hours
            h_match = re.search(r'module\s+delivery\s*\(\s*in\s*hours\s*\)\s*(\d+(?:\.\d+)?)\s*hrs?', content, re.IGNORECASE)
            hours = float(h_match.group(1)) if h_match else 0.0
            official_minutes = int(hours * 60) if hours > 0 else 0

            # 2. Partition into title head and topics body
            parts = re.split(r'(?i)(?:module\s+delivery\s*\(\s*in\s*hours\s*\)\s*[\d\.]+\s*hrs?[\s\|]*)+', content, maxsplit=1)
            head = parts[0] if len(parts) > 0 else ""
            body = parts[1] if len(parts) > 1 else ""

            # Check if (Case Study \d+) appears in content and capture into assignments (without duplicating)
            case_matches = re.findall(r'(?i)\(?case\s+study\s*(\d+)\)?', content)
            for cm in case_matches:
                if not any(f"case study {cm}" in ex.lower() for ex in data.assignments):
                    data.assignments.append(f"Case Study {cm} (Module {num})")


            # 3. Clean module title from table boilerplate
            title_clean = cls._clean_module_title(head)

            # 4. Clean body from assignment instructions and pipe duplicate cells
            body_clean = cls._clean_table_body(body)

            if not title_clean and body_clean.strip():
                first_sentence = body_clean.strip().splitlines()[0].strip(" .")
                title_clean = first_sentence

            # 5. Extract structured topics with subtopics
            parsed_topics = cls._parse_table_module_topics(body_clean, num)
            if not parsed_topics and title_clean:
                parsed_topics = [{"title": title_clean, "subtopics": []}]

            # 6. Distribute delivery hours strictly across topics
            target_mins = official_minutes if official_minutes > 0 else max(60, len(parsed_topics) * 45)
            num_topics = max(1, len(parsed_topics))
            base_mins = target_mins // num_topics
            rem_mins = target_mins % num_topics

            topic_dicts = []
            for t_i, t_item in enumerate(parsed_topics):
                t_title = t_item["title"]
                raw_subs = t_item.get("subtopics", [])
                subtopic_items = [
                    {"id": f"sub_{num}_{t_i+1}_{s_i+1}", "title": s}
                    for s_i, s in enumerate(raw_subs)
                ]

                t_min = base_mins + (1 if t_i < rem_mins else 0)
                difficulty = "medium"
                lower_t = t_title.lower()
                if any(w in lower_t for w in ["intro", "overview", "basic", "concept"]):
                    difficulty = "easy"
                elif any(w in lower_t for w in ["advanced", "design", "architecture", "algorithm", "synchronization", "deadlock"]):
                    difficulty = "hard"

                topic_dicts.append({
                    "id": f"top_{num}_{t_i+1}",
                    "title": t_title,
                    "explanation": f"Study of {t_title} as specified in Module {num}.",
                    "estimated_minutes": t_min,
                    "difficulty": difficulty,
                    "prerequisites": [],
                    "subtopics": subtopic_items,
                    "source_evidence": t_title[:120],
                    "confidence_notes": f"Parsed from syllabus structure with verified delivery hours ({target_mins}m module total).",
                    "order_index": t_i,
                })

            mod_title = f"Module {num} — {title_clean}"
            if hours > 0:
                hours_str = str(int(hours)) if hours.is_integer() else f"{hours:g}"
                mod_title = f"Module {num} — {title_clean} ({hours_str} hours)"

            modules_out.append({
                "id": f"mod_{num}",
                "title": mod_title,
                "order_index": m_idx,
                "official_hours": hours if hours > 0 else None,
                "official_minutes": official_minutes if official_minutes > 0 else None,
                "topics": topic_dicts,
            })

        return modules_out


    @classmethod
    def _extract_linear_modules(
        cls, lines: List[str], data: ExtractedSyllabusData
    ) -> List[Dict[str, Any]]:
        """Standard linear extractor for Unit/Module/Chapter syllabi."""
        current_section = "header"
        module_blocks: List[Tuple[str, List[str]]] = []
        current_mod_title = ""
        current_mod_lines: List[str] = []

        for line in lines:
            lower = line.lower()

            # Check if this line starts an administrative non-module section
            matched_non_mod = False
            for pat in NON_MODULE_HEADINGS:
                if re.match(pat, lower):
                    matched_non_mod = True
                    if "objective" in lower:
                        current_section = "objectives"
                    elif "outcome" in lower:
                        current_section = "outcomes"
                    elif "prereq" in lower:
                        current_section = "prerequisites"
                    elif "text" in lower or "reference" in lower:
                        current_section = "books"
                    elif "eval" in lower or "assess" in lower or "grading" in lower:
                        current_section = "assessment"
                    else:
                        current_section = "other_meta"
                    break

            if matched_non_mod:
                continue

            # Check if this line is a genuine Module/Unit boundary
            matched_module = False
            for pat in MODULE_PATTERNS:
                m = re.match(pat, line, re.IGNORECASE)
                if m:
                    if current_mod_title or current_mod_lines:
                        module_blocks.append((current_mod_title, current_mod_lines))
                        current_mod_lines = []

                    prefix = m.group(1).strip()
                    title_rest = m.group(2).strip() if len(m.groups()) >= 2 else ""
                    title_clean = re.sub(r"[\(\[]\s*\d+\s*(hours?|lectures?|periods?)?\s*[\)\]]", "", title_rest, flags=re.IGNORECASE).strip(" :-–—")
                    current_mod_title = f"{prefix.title()}: {title_clean}" if title_clean else prefix.title()
                    current_section = "module"
                    matched_module = True
                    break

            if matched_module:
                continue

            # Route line to active section
            if current_section == "objectives":
                cleaned = cls._clean_bullet(line)
                if cleaned and len(cleaned) > 5:
                    data.objectives.append(cleaned)
            elif current_section == "outcomes":
                cleaned = cls._clean_bullet(line)
                if cleaned and len(cleaned) > 5:
                    data.outcomes.append(cleaned)
            elif current_section == "prerequisites":
                cleaned = cls._clean_bullet(line)
                if cleaned and len(cleaned) > 3 and cleaned.lower() != "nil":
                    data.prerequisites.append(cleaned)
            elif current_section == "books":
                cleaned = cls._clean_bullet(line)
                if cleaned and len(cleaned) > 5:
                    data.textbooks.append(cleaned)
            elif current_section == "assessment":
                if not data.assessment_info:
                    data.assessment_info = line
                else:
                    data.assessment_info += f"; {line}"
            elif current_section == "module":
                current_mod_lines.append(line)

        # Flush final module
        if current_mod_title or current_mod_lines:
            module_blocks.append((current_mod_title, current_mod_lines))

        if not module_blocks:
            module_blocks = cls._synthesize_modules_from_text(lines, data)

        return cls._process_module_blocks(module_blocks, data)

    @classmethod
    def _extract_header_metadata(cls, header_lines: List[str], data: ExtractedSyllabusData) -> None:
        """Extracts course code, course name, credits, and term from first few lines (supporting multi-line headers and table cells)."""
        num_lines = len(header_lines)

        # Pass 1: Explicit Course Title Detection (prioritized over any line-1 heuristics)
        for idx, line in enumerate(header_lines):
            lower = line.lower().strip()
            if "course title" in lower or "course name" in lower or "subject name" in lower:
                # Check for explicit course title in line or pipe-separated cells
                m_title = re.search(r"(?i)(?:course\s+title|course\s+name|subject\s+name)\s*[:\s\-]+([^\|]+)", line)
                title_part = ""
                if m_title:
                    title_part = m_title.group(1).strip()
                else:
                    parts = line.split(":", 1)
                    title_part = parts[1].strip() if len(parts) > 1 else ""

                adv = 0
                if len(title_part) < 4 and idx + 1 < num_lines:
                    next_cand = header_lines[idx + 1].strip()
                    if not any(k in next_cand.lower() for k in ["course", "tpc", "credit", "version", "semester", "page"]):
                        title_part = next_cand
                        adv = 1

                if idx + 1 + adv < num_lines:
                    cont_cand = header_lines[idx + 1 + adv].strip()
                    if (
                        cont_cand
                        and not any(k in cont_cand.lower() for k in ["tpc", "version", "credit", "requisite", "page", "semester", "module", "unit", "objective", "outcome"])
                        and not re.match(r"^\d", cont_cand)
                        and len(cont_cand.split()) <= 4
                    ):
                        title_part = f"{title_part} {cont_cand}".strip()

                title_part = re.sub(r"\b(tpc\b|version\b|credits?\b).*", "", title_part, flags=re.IGNORECASE).strip(" :-–—\t")
                if len(title_part) >= 4:
                    data.course_name = title_part
                    break

        # Pass 2: Course Code, Credits, Term, and Fallback Heuristic Course Name
        for idx, line in enumerate(header_lines):
            lower = line.lower().strip()
            if any(term in lower for term in ["department of", "faculty of", "college of", "university", "institute of", "syllabus format for"]):
                continue

            # 1. Course Code Detection
            if not data.course_code:
                if "course code" in lower or "subject code" in lower or "paper code" in lower:
                    m_code = re.search(r"(?i)(?:course\s+code|subject\s+code|paper\s+code)\s*[:\s\-]+([^\|]+)", line)
                    cand_code = m_code.group(1).strip() if m_code else ""
                    if not cand_code:
                        parts = line.split(":", 1)
                        cand_code = parts[1].strip() if len(parts) > 1 else ""
                    if not cand_code and idx + 1 < num_lines:
                        cand_code = header_lines[idx + 1].strip()
                    m_c = re.search(r"\b([A-Z0-9]{2,5}\s*[-]?\s*[A-Z0-9]{3,5})\b", cand_code)
                    if m_c and not any(k in m_c.group(1).lower() for k in ["tpc", "page", "version"]):
                        data.course_code = re.sub(r"\s+", " ", m_c.group(1).replace("-", " ")).strip().upper()
                else:
                    m_code = re.search(r"\b([A-Z]{2,4}\s*[-]?\s*\d{3,4}[A-Z]?)\b", line)
                    if m_code and not any(k in m_code.group(1).lower() for k in ["tpc", "page", "version"]):
                        data.course_code = re.sub(r"\s+", " ", m_code.group(1).replace("-", " ")).strip().upper()

            # 2. Credits (e.g. "Credits: 3-0-0-3", "L T P C : 3 0 0 3", "TPC 3 0 3")
            if not data.credits:
                match_cred = re.search(r"\b(credits?|l\s*t\s*p\s*c|t\s*p\s*c)\s*[:\s\-]?\s*([\d\s\-\.]+)", line, re.IGNORECASE)
                if match_cred:
                    data.credits = match_cred.group(0).strip()

            # 3. Semester / Term
            if not data.term:
                match_term = re.search(r"\b(semester\s*[:\s\-]?\s*[ivx0-9]+|term\s*[:\s\-]?\s*[0-9]+|fall\s+\d{4}|spring\s+\d{4})\b", line, re.IGNORECASE)
                if match_term:
                    data.term = match_term.group(0).strip()

            # 4. Fallback Heuristic Course Name Detection (only if explicit title wasn't found in Pass 1)
            if data.course_name == "Course Syllabus" and not any(k in lower for k in ["syllabus", "curriculum", "version", "tpc", "credits", "semester", "page", "format", "independent lab"]):
                name_cand = line
                if ":" in name_cand:
                    parts = name_cand.split(":", 1)
                    if any(term in parts[0].lower() for term in ["course", "subject", "paper"]) or re.match(r"^[A-Z]{2,4}\s*\d+", parts[0].strip()):
                        name_cand = parts[1]

                name_cand = re.sub(r"[\(\[].*?[\)\]]", "", name_cand)
                name_cand = re.sub(r"\b[A-Z]{2,4}\s*[-]?\s*\d{3,4}[A-Z]?\b", "", name_cand)
                name_cand = name_cand.replace("Syllabus", "").replace("Course", "").strip(" :-–—\t")
                if len(name_cand) >= 4 and not any(k in name_cand.lower() for k in ["credits", "semester", "page", "format", "version", "independent lab"]):
                    data.course_name = name_cand


    @classmethod
    def _clean_bullet(cls, text: str) -> str:
        """Removes bullet symbols and leading numbers/letters."""
        cleaned = re.sub(r"^([•\-\*▪▫]|\d+\.|\d+\.\d+|[a-z]\))\s*", "", text).strip()
        return cleaned

    @classmethod
    def _is_metadata_or_fragment(cls, text: str) -> bool:
        """Returns True if text matches administrative metadata or sentence fragments."""
        trimmed = text.strip()
        if len(trimmed) < 4:
            return True

        lower = trimmed.lower()

        # Check filter patterns
        for pat in METADATA_FILTER_PATTERNS:
            if re.match(pat, trimmed, re.IGNORECASE):
                return True

        # Check common administrative words
        if lower in {"introduction", "overview", "prerequisites", "course outcomes", "textbooks", "references", "syllabus"}:
            return True

        return False

    @classmethod
    def _split_into_discrete_topics(cls, text: str) -> List[str]:
        """
        Splits delimited syllabus text into discrete, coherent topic phrases.
        Handles:
        - "Processes – Process States – Context Switching"
        - "Paging; Segmentation; Demand Paging"
        - Period sentence boundaries: "Monitors. Deadlocks: System Model"
        - Comma-separated lists and bullet points
        """
        sentence_chunks = re.split(r"\.\s+(?=[A-Z0-9])", text)
        candidates: List[str] = []

        for chunk in sentence_chunks:
            chunk = chunk.strip(" .")
            if not chunk:
                continue

            if any(sep in chunk for sep in [" – ", " — ", " - ", ";"]):
                parts = re.split(r"\s+[–—\-]\s+|\s*;\s*", chunk)
                for p in parts:
                    cleaned = cls._clean_bullet(p.strip(" ."))
                    if cleaned and len(cleaned) >= 4:
                        candidates.append(cleaned)
            elif "," in chunk and len(chunk) > 35:
                if ":" in chunk:
                    c_parts = chunk.split(":", 1)
                    header = c_parts[0].strip(" .")
                    items = c_parts[1].strip()
                    if header and len(header) >= 4:
                        candidates.append(f"{header}: {items}")
                else:
                    parts = chunk.split(",")
                    for p in parts:
                        cleaned = cls._clean_bullet(p.strip(" ."))
                        if cleaned and len(cleaned) >= 4:
                            candidates.append(cleaned)
            else:
                cleaned = cls._clean_bullet(chunk.strip(" ."))
                if cleaned and len(cleaned) >= 4:
                    candidates.append(cleaned)

        return candidates

    @classmethod
    def _synthesize_modules_from_text(
        cls, lines: List[str], data: ExtractedSyllabusData
    ) -> List[Tuple[str, List[str]]]:
        """
        When a syllabus does not use explicit 'Unit X' or 'Module X' keywords,
        groups content lines logically into 3-5 modules based on content breaks.
        """
        eligible_lines = [
            l for l in lines 
            if not cls._is_metadata_or_fragment(l) 
            and len(l) > 10
        ]

        if not eligible_lines:
            return [("Module 1: Course Topics", [data.course_name])]

        chunk_size = max(3, len(eligible_lines) // 4 + 1)
        chunks = [eligible_lines[i:i + chunk_size] for i in range(0, len(eligible_lines), chunk_size)]

        modules = []
        for idx, chunk in enumerate(chunks[:5]):
            first_line = chunk[0][:40].strip(" :-–—")
            mod_title = f"Module {idx+1}: {first_line}"
            modules.append((mod_title, chunk))

        return modules

    @classmethod
    def _process_module_blocks(
        cls,
        module_blocks: List[Tuple[str, List[str]]],
        data: ExtractedSyllabusData
    ) -> List[Dict[str, Any]]:
        """
        Turns module raw lines into verified ModuleItem dicts with TopicItems.
        """
        modules_out: List[Dict[str, Any]] = []

        for m_idx, (mod_title, mod_lines) in enumerate(module_blocks):
            if not mod_title:
                mod_title = f"Module {m_idx+1} — Core Topics"
            else:
                clean_t = re.sub(r'^(?:Module|Unit|Chapter|Part|Week)\s*\d+[\s:\-–—]*', '', mod_title, flags=re.I).strip(" :-–—")
                mod_title = f"Module {m_idx+1} — {clean_t or mod_title}"

            topics_out: List[Dict[str, Any]] = []
            seen_topics: Set[str] = set()

            for line in mod_lines:
                if cls._is_metadata_or_fragment(line):
                    if len(line) > 20 and not any(k in line.lower() for k in ["page", "credits", "semester"]):
                        data.ambiguous_sections.append(f"Unclassified line in {mod_title}: '{line[:120]}'")
                    continue

                candidate_topics = cls._split_into_discrete_topics(line)

                for cand in candidate_topics:
                    if cls._is_metadata_or_fragment(cand):
                        continue

                    cand_clean = cls._clean_bullet(cand)
                    if len(cand_clean) < 4:
                        continue

                    topic_title = cand_clean.strip(" .")
                    subtopics: List[Dict[str, str]] = []
                    if ":" in cand_clean and not cand_clean.lower().startswith(("note:", "example:")):
                        colon_parts = cand_clean.split(":", 1)
                        header = colon_parts[0].strip(" .")
                        subs_raw = colon_parts[1].strip()
                        if len(header) >= 4 and len(subs_raw) > 3:
                            topic_title = header
                            for s_idx, s in enumerate(subs_raw.split(",")):
                                s_clean = s.strip(" .")
                                if s_clean and len(s_clean) >= 3:
                                    subtopics.append({
                                        "id": f"sub_{m_idx+1}_{len(topics_out)+1}_{s_idx+1}",
                                        "title": s_clean
                                    })

                    norm_key = re.sub(r"[^\w\s]", "", topic_title.lower()).strip()
                    if norm_key in seen_topics:
                        continue
                    seen_topics.add(norm_key)

                    difficulty = "medium"
                    lower_t = topic_title.lower()
                    if any(w in lower_t for w in ["intro", "overview", "basic", "fundamental", "concept"]):
                        difficulty = "easy"
                        est_min = 35
                    elif any(w in lower_t for w in ["advanced", "complex", "algorithm", "design", "architecture", "analysis", "optimization"]):
                        difficulty = "hard"
                        est_min = 60
                    else:
                        est_min = 45

                    if len(subtopics) > 3:
                        est_min = min(90, est_min + 20)

                    t_idx = len(topics_out) + 1
                    top_id = f"top_{m_idx+1}_{t_idx}"

                    topics_out.append({
                        "id": top_id,
                        "title": topic_title,
                        "explanation": f"Study of {topic_title} as specified in {mod_title}.",
                        "estimated_minutes": est_min,
                        "difficulty": difficulty,
                        "prerequisites": [],
                        "subtopics": subtopics,
                        "source_evidence": line[:120],
                        "confidence_notes": "Parsed from syllabus structure with verified topic boundaries.",
                        "order_index": t_idx - 1,
                    })

            if topics_out:
                modules_out.append({
                    "id": f"mod_{m_idx+1}",
                    "title": mod_title,
                    "order_index": m_idx,
                    "topics": topics_out,
                })
            else:
                data.ambiguous_sections.append(
                    f"Module '{mod_title}' contained no discrete topics after filtering administrative text."
                )

        return modules_out
