from services.import_repository import build_import_run_report
from services.command_center import _evidence_json
from web.routes.reviews import _enrich_review_item


def test_source_row_only_does_not_claim_visible_rank():
    grouped = {
        (554, "total_hero_power"): [
            {"rank": i, "source_file": "scrolled.png", "power": 170_000_000 - i}
            for i in range(1, 9)
        ],
        ("REVIEW", "ranking_guard_quarantine"): [
            {
                "original_server": 554,
                "original_ranking_type": "total_hero_power",
                "expected_ranking_type": "total_hero_power",
                "rank": 2,
                "source_file": "scrolled.png",
                "name": "[MBM] yochic Rfeoezome#A",
                "alliance": "MBM",
                "ranking_guard_warning": "power_sanity:power_recovery_candidates_ambiguous",
            }
        ],
    }
    report = build_import_run_report(grouped, screenshots=1, runtime_seconds=1, output_file="out.xlsx")
    review = report["reviews"][0]
    assert review["visible_rank"] is None
    assert review["source_row"] == 2
    assert review["rank_trace_source"] == "source_row_only"
    enriched = _enrich_review_item(review)
    assert enriched["rank_display_label"] == "OCR Row 2 · Operational Rank unresolved"
    assert enriched["rank_highlight_label"] == "OCR Row 2"


def test_review_ids_continue_from_existing_history():
    import_report = {
        "created_at": "2026-07-03T00:00:00+00:00",
        "status": "Review",
        "reviews": [
            {
                "server": 554,
                "ranking_type": "total_hero_power",
                "rank": None,
                "source_row": 2,
                "raw_review_rank": 2,
                "target_name": "New Target",
                "reason": "ranking_guard_quarantine",
                "description": "power_sanity:alliance_power_outlier",
                "screenshot": "new.png",
            }
        ],
    }
    existing = {"items": [{"review_id": "REV-013", "review_identity": "old"}]}
    payload = _evidence_json(import_report, existing)
    assert payload["items"][0]["id"] == "REV-014"

from services.command_center import _derive_visible_rank, _rank_context_label


def test_command_center_source_row_only_does_not_fallback_to_rank():
    item = {
        "rank": 2,
        "visible_rank": None,
        "source_row": 2,
        "raw_review_rank": 2,
        "rank_trace_source": "source_row_only",
        "screenshot_rank_window": {"start": 1, "end": 8, "count": 8},
    }
    assert _derive_visible_rank(item) == ""
    assert _rank_context_label(item) == "OCR Row 2; Operational Rank unresolved"
