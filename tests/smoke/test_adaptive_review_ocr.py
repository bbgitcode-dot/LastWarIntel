import numpy as np

from parser.review_ocr import build_review_ocr_variants, run_adaptive_review_ocr
from services.import_repository import build_import_run_report


class StubReader:
    def __init__(self, results):
        self.results = results
        self.calls = 0

    def read_rows(self, image):
        self.calls += 1
        return self.results


def _box(x1, y1, x2, y2):
    return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]


def test_review_ocr_builds_zoom_and_enhancement_variants_from_row_y():
    image = np.zeros((400, 800, 3), dtype=np.uint8)
    row = {"visual_y": 200}

    variants = build_review_ocr_variants(image, row, max_variants=6)

    names = [variant.name for variant in variants]
    assert "row_crop" in names
    assert "row_crop_2x" in names
    assert any(name.endswith("clahe") or name.endswith("sharpen") for name in names)
    assert all(variant.image.size for variant in variants)


def test_adaptive_review_ocr_promotes_clear_second_pass_row(tmp_path):
    screenshot = tmp_path / "row.png"
    import cv2
    cv2.imwrite(str(screenshot), np.zeros((400, 800, 3), dtype=np.uint8))
    grouped = {
        ("REVIEW", "ranking_guard_quarantine"): [
            {
                "original_server": 551,
                "original_ranking_type": "total_hero_power",
                "ranking_type": "total_hero_power",
                "name": "[IVE] MEITTi",
                "power": 32_030_601,
                "source_file": "row.png",
                "visual_y": 200,
                "ranking_guard_warning": "power_recovery_candidates_ambiguous",
            }
        ]
    }
    ocr_results = [
        (_box(5, 120, 25, 140), "2", 0.91),
        (_box(70, 120, 230, 140), "[IVE] MEITTi", 0.94),
        (_box(620, 120, 760, 140), "320306014", 0.97),
    ]
    reader = StubReader(ocr_results)

    result = run_adaptive_review_ocr(
        grouped,
        reader=reader,
        screenshot_dir=tmp_path,
        target_width=800,
        target_height=400,
        enabled=True,
        max_variants_per_row=3,
    )

    assert ("REVIEW", "ranking_guard_quarantine") not in result
    promoted = result[(551, "total_hero_power")][0]
    assert promoted["power"] == 320_306_014
    assert promoted["review_ocr_status"] == "promoted"
    assert promoted["review_ocr_best_variant"]
    assert promoted["power_recovery_method"] == "total_hero_power_adaptive_review_ocr"


def test_import_report_summarizes_review_ocr():
    grouped = {
        ("REVIEW", "ranking_guard_quarantine"): [
            {
                "original_server": 551,
                "original_ranking_type": "total_hero_power",
                "rank": 2,
                "power": 32_030_601,
                "source_file": "row.png",
                "review_ocr_attempted": True,
                "review_ocr_status": "no_promotion",
                "review_ocr_score": 0.58,
                "review_ocr_decision": "kept_in_quarantine_after_review_ocr",
            }
        ],
        (551, "total_hero_power"): [
            {
                "rank": 2,
                "power": 320_306_014,
                "source_file": "row.png",
                "review_ocr_attempted": True,
                "review_ocr_status": "promoted",
                "review_ocr_score": 0.83,
            }
        ],
    }

    report = build_import_run_report(grouped, screenshots=1, runtime_seconds=1, output_file="output/x.xlsx")

    assert report["review_ocr"]["attempted"] == 2
    assert report["review_ocr"]["promoted"] == 1
    assert report["review_ocr"]["no_promotion"] == 1
    assert report["reviews"][0]["review_ocr_decision"] == "kept_in_quarantine_after_review_ocr"
