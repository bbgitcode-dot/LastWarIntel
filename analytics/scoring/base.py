from dataclasses import dataclass
from typing import Optional


@dataclass
class ScoreResult:
    name: str
    server: int
    score: float
    raw_value: Optional[float] = None
    explanation: str = ""


class BaseScore:
    name = "base"
    weight = 1.0

    def calculate(self, server: int) -> ScoreResult:
        raise NotImplementedError