from dataclasses import dataclass
from typing import Optional


@dataclass
class Snapshot:
    id: Optional[int]
    uuid: str
    collection_id: int
    server: int
    status: str = "pending"
    parser_version: Optional[str] = None
    ocr_engine: Optional[str] = None
    ocr_version: Optional[str] = None