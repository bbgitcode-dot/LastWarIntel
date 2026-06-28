"""Smoke Test
OCR Normalization for structured THP parsing
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from parser.normalization import (  # noqa: E402
    AllianceTagNormalizer,
    HeroPowerNormalizer,
    PlayerNameNormalizer,
)
from parser.player_ranking import build_player_ranking_snapshot  # noqa: E402
from parser.ranking import clean_power  # noqa: E402


def main() -> None:
    tag = AllianceTagNormalizer().normalize("{[ACEv|")
    assert tag.value == "ACEv"
    assert tag.confidence < 1.0

    name = PlayerNameNormalizer().normalize("Tar0ri")
    assert name.value == "Tarori"
    assert name.confidence < 1.0

    name = PlayerNameNormalizer().normalize("Tarorl")
    assert name.value == "Tarori"

    power = HeroPowerNormalizer().normalize("29234I388")
    assert power.value == "292341388"
    assert clean_power("29234I388") == 292_341_388

    snapshot = build_player_ranking_snapshot(
        rows=[
            {
                "name": "{[ACEv| Tar0ri",
                "power": 292_341_388,
                "confidence": 0.96,
                "raw_text": "1 | {[ACEv| Tar0ri | 29234I388",
            }
        ],
        server=573,
        snapshot_id="s573-normalization-test",
        source_file="thp-noisy.png",
    )

    entry = snapshot.entries[0]
    assert entry.alliance_tag == "ACEv"
    assert entry.player_name == "Tarori"
    assert entry.hero_power == 292_341_388
    assert entry.confidence < 0.96

    legacy = entry.to_legacy_row()
    assert legacy["name"] == "[ACEv] Tarori"
    assert legacy["confidence"] == entry.confidence

    print("PASS")


if __name__ == "__main__":
    main()
