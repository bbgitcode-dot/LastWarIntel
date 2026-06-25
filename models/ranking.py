from dataclasses import dataclass
from typing import Optional


@dataclass
class RankingEntry:
    id: Optional[int]
    snapshot_id: int
    ranking_type: str
    entity: str
    rank: int
    value: int
    tag: Optional[str] = None
    source_file: Optional[str] = None
    confidence: Optional[float] = None