"""
LastWarIntel
Smoke Test
Server Intelligence
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from analytics.server_intelligence.facade import (  # noqa: E402
    ServerIntelligenceFacade,
)


def main() -> None:
    result = ServerIntelligenceFacade().analyze(638)

    assert result.assessment.server == 638
    assert result.assessment.outlook is not None
    assert result.assessment.highlights

    print("PASS")


if __name__ == "__main__":
    main()