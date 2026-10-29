from typing import Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SyllabusRecord:
    id: str
    filename: str
    file_type: str
    file_size_bytes: int
    char_count: int
    word_count: int
    raw_text: str
    created_at: Optional[datetime] = None
