from dataclasses import dataclass
from typing import Optional


@dataclass
class Entity:
    id: Optional[int]
    uuid: str
    entity_type: str
    name: str
    tag: Optional[str] = None