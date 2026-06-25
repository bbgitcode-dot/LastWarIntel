from dataclasses import dataclass
from typing import Optional


@dataclass
class Collection:
    id: Optional[int]
    uuid: str
    name: str
    description: str = ""
    type: str = "custom"
    status: str = "active"
    expected_servers: Optional[int] = None