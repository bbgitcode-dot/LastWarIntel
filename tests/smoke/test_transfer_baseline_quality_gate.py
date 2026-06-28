"""Smoke tests for Sprint 10A Transfer Baseline quality gate."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from parser.player_identity_quality import parse_player_identity_quality  # noqa: E402
from parser.player_ranking import build_player_ranking_snapshot  # noqa: E402


def main() -> None:
    clean = parse_player_identity_quality("[SW3] Bierbaer", base_confidence=0.97)
    assert clean.alliance_tag == "SW3"
    assert clean.player_name == "Bierbaer"
    assert clean.status == "VALID"

    prefixed = parse_player_identity_quality("FKGzzs [Warf] GoldCradle", base_confidence=0.93)
    assert prefixed.alliance_tag == "Warf"
    assert prefixed.player_name == "GoldCradle"
    assert prefixed.status == "REVIEW"
    assert "prefix_before_alliance_tag_ignored" in prefixed.warnings

    unreadable = parse_player_identity_quality("[ABC] 张三", base_confidence=0.91)
    assert unreadable.alliance_tag == "ABC"
    assert unreadable.player_name == "UNKNOWN"
    assert unreadable.status == "REVIEW"
    assert "player_identity_requires_review" in unreadable.warnings

    missing_tag = parse_player_identity_quality("Bierbaer", base_confidence=0.96)
    assert missing_tag.alliance_tag is None
    assert missing_tag.player_name == "Bierbaer"
    assert missing_tag.status == "REVIEW"
    assert "missing_alliance_tag" in missing_tag.warnings

    snapshot = build_player_ranking_snapshot(
        rows=[
            {
                "name": "FKGzzs [Warf] GoldCradle",
                "power": 260_000_000,
                "confidence": 0.93,
                "raw_text": "1 | FKGzzs [Warf] GoldCradle | 260000000",
                "source_file": "server556_pre_transfer.png",
            },
            {
                "name": "[ABC] 张三",
                "power": 250_000_000,
                "confidence": 0.91,
                "raw_text": "2 | [ABC] 张三 | 250000000",
                "source_file": "server556_pre_transfer.png",
            },
        ],
        server=556,
        snapshot_id="s6-pre-556-thp",
        source_file="server556_pre_transfer.png",
    )

    rows = snapshot.to_legacy_rows()
    assert rows[0]["alliance_tag"] == "Warf"
    assert rows[0]["player_name"] == "GoldCradle"
    assert rows[0]["parse_status"] == "REVIEW"
    assert "prefix_before_alliance_tag_ignored" in rows[0]["parse_warnings"]

    assert rows[1]["alliance_tag"] == "ABC"
    assert rows[1]["player_name"] == "UNKNOWN"
    assert rows[1]["parse_status"] == "REVIEW"
    assert "player_identity_requires_review" in rows[1]["parse_warnings"]

    print("PASS")


if __name__ == "__main__":
    main()
