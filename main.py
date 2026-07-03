from pathlib import Path
import argparse
import fnmatch
import json
import os
import sys
import time

from parser.image import load_and_normalize_image
from parser.ocr import create_reader, read_ocr, read_metadata_ocr, ocr_to_text
from parser.server import detect_ranking_type, detect_server_consensus_from_ocr
from parser.data_guard import resolve_server_assignment, reconcile_server_assignments_by_content
from parser.ranking_guard import apply_ranking_guard
from parser.ranking_power_sanity_guard import apply_ranking_power_sanity_guard
from parser.review_ocr import run_adaptive_review_ocr
from parser.quality_loop import run_server_quality_loop
from services.import_repository import JsonImportRunRepository, build_import_run_report
from services.command_center import generate_command_center
from parser.debug import draw_debug_boxes
from parser.ranking import (
    parse_ranking_rows,
    merge_rows_by_power,
    infer_ranking_type_from_values,
)
from parser.player_ranking import build_player_ranking_snapshot
from parser.excel import export
from application.snapshots.service import SnapshotContextError, SnapshotService


CONFIG_FILE = Path("config_pc.json")
SCREENSHOT_DIR = Path("screenshots")


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _configure_stdout() -> None:
    """Make Windows consoles safe for multilingual OCR debug output."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _safe_print(*values) -> None:
    text = " ".join(str(value) for value in values)
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("unicode_escape").decode("ascii"))



def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Sentinel screenshot import runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--rebuild-reports",
        action="store_true",
        help="Regenerate Command Center, Review Dashboard and Evidence Pack from data/latest_import_report.json without running OCR.",
    )
    parser.add_argument(
        "--screenshots",
        default="",
        help="Developer filter: comma-separated screenshot filenames or glob patterns inside screenshots/. This limits processing only; it is never used as data truth.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Developer filter: process only the first N selected screenshots. 0 means no limit.",
    )
    parser.add_argument(
        "--skip-command-center",
        action="store_true",
        help="Skip static HTML report rendering after import. Useful for OCR-only profiling.",
    )
    parser.add_argument(
        "--skip-excel",
        action="store_true",
        help="Skip Excel export mirroring during quick developer runs. The JSON import report is still written.",
    )
    parser.add_argument(
        "--finish-collection",
        action="store_true",
        help="After the import, explicitly move the active snapshot to REVIEWING/VERIFIED. By default Sentinel keeps COLLECTING so 24/7 screenshot intake is not blocked.",
    )
    return parser.parse_args(argv)


def _parse_screenshot_patterns(pattern_text: str) -> list[str]:
    return [part.strip() for part in str(pattern_text or "").split(",") if part.strip()]


def _select_screenshots(screen_dir: Path, *, patterns: list[str] | None = None, limit: int = 0) -> list[Path]:
    """Return screenshot paths for the current run.

    This is a developer/benchmark convenience only.  It filters the input set by
    explicit filename/glob and must not be interpreted as evidence about server,
    rank or upload order.  Operational truth is still derived exclusively from
    OCR, parser evidence and Data Guard validation.
    """
    screenshots = sorted(list(screen_dir.glob("*.png")) + list(screen_dir.glob("*.jpg")))
    patterns = list(patterns or [])
    if patterns:
        selected: list[Path] = []
        for screenshot in screenshots:
            name = screenshot.name
            full = str(screenshot)
            if any(fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(full, pattern) for pattern in patterns):
                selected.append(screenshot)
        screenshots = selected
    if limit and limit > 0:
        screenshots = screenshots[:limit]
    return screenshots

def main(argv=None):
    _configure_stdout()
    args = parse_args(argv)
    if args.rebuild_reports:
        command_center_files = generate_command_center()
        print("Report rebuild completed from data/latest_import_report.json")
        print(f"Command Center geschrieben nach {command_center_files['command_center']}")
        print(f"Review Dashboard geschrieben nach {command_center_files['review_dashboard']}")
        print(f"Review Evidence Pack geschrieben nach {command_center_files['review_evidence_pack']}")
        return
    config = load_config()
    snapshot_service = SnapshotService()
    try:
        active_snapshot = snapshot_service.require_active_import_snapshot()
    except SnapshotContextError as exc:
        print(f"SNAPSHOT BLOCKER | {exc}")
        return
    snapshot_service.update_status(active_snapshot.id, "collecting")
    active_snapshot = snapshot_service.require_active_import_snapshot()
    start_time = time.perf_counter()
    print(f"Active Snapshot: {active_snapshot.name} ({active_snapshot.id})")
    reader = create_reader()
    print(f"OCR Provider: {reader.info.engine} ({reader.info.name})")
    print(f"OCR Metadata Languages: {list(reader.info.metadata_languages)}")
    print(f"OCR Row Languages: {list(reader.info.row_languages)}")

    screenshot_patterns = _parse_screenshot_patterns(args.screenshots or os.getenv("SENTINEL_SCREENSHOTS", ""))
    screenshots = _select_screenshots(
        SCREENSHOT_DIR,
        patterns=screenshot_patterns,
        limit=args.limit or int(os.getenv("SENTINEL_SCREENSHOT_LIMIT", "0") or 0),
    )
    if screenshot_patterns or args.limit:
        print(f"Developer screenshot filter active: {len(screenshots)} screenshot(s) selected")
        if screenshot_patterns:
            print("Patterns:", ", ".join(screenshot_patterns))
        if args.limit:
            print("Limit:", args.limit)

    if not screenshots:
        print("Keine Screenshots gefunden.")
        return

    grouped = {}

    for screenshot in screenshots:
        print(f"\n{screenshot.name}")

        image = load_and_normalize_image(
            screenshot,
            config["target_width"],
            config["target_height"]
        )

        # Metadata OCR intentionally runs separately with the stable metadata
        # reader. This avoids multilingual noise breaking Warzone detection.
        metadata_ocr = read_metadata_ocr(reader, image)
        metadata_text = ocr_to_text(metadata_ocr)
        metadata_detection = detect_server_consensus_from_ocr(metadata_ocr, min_occurrences=3)
        ranking_type = detect_ranking_type(metadata_text)

        # Row OCR may use multilingual readers depending on the selected profile.
        ocr = read_ocr(reader, image)
        row_text = ocr_to_text(ocr)
        server_detection = resolve_server_assignment(metadata_detection, ocr)

        # Sentinel Data Quality Loop: before sending an uncertain screenshot to
        # review, try targeted content-based OCR recovery.  The loop does not
        # guess or assign servers by filename/timestamp; it only creates better
        # OCR evidence and lets the Data Guard validate again.
        quality_loop_result = run_server_quality_loop(
            reader=reader,
            image=image,
            initial_metadata_ocr=metadata_ocr,
            initial_row_ocr=ocr,
            initial_decision=server_detection,
            max_attempts=3,
        )
        if quality_loop_result.attempts:
            server_detection = quality_loop_result.decision
            metadata_ocr = quality_loop_result.metadata_ocr
            ocr = quality_loop_result.row_ocr
            metadata_text = ocr_to_text(metadata_ocr)
            row_text = ocr_to_text(ocr)
            suffix = quality_loop_result.warning_suffix
            if suffix:
                if server_detection.warning:
                    from dataclasses import replace
                    server_detection = replace(server_detection, warning=f"{server_detection.warning};{suffix}")
                else:
                    from dataclasses import replace
                    server_detection = replace(server_detection, warning=suffix)

        server = server_detection.server
        if ranking_type == "unknown":
            ranking_type = detect_ranking_type(row_text)

        print("Server :", server)
        print("Server*:", server_detection.warning or "validated")
        print("Typ    :", ranking_type)
        print("OCR    :", len(ocr), "Elemente")

        draw_debug_boxes(
            image,
            ocr,
            f"output/debug/{screenshot.stem}.png"
        )

        rows = parse_ranking_rows(ocr)
        ranking_type = infer_ranking_type_from_values(ranking_type, rows)
        print("Typ*   :", ranking_type)
        print(
            screenshot.name,
            server,
            ranking_type,
            len(rows)
        )
        print(
            f"DEBUG | {screenshot.name} | Server={server} | "
            f"ServerWarning={server_detection.warning} | "
            f"Typ={ranking_type} | Rows={len(rows)}"
        )

        if server is None:
            grouped.setdefault(("REVIEW", "server_review"), []).append({
                "source_file": screenshot.name,
                "ranking_type": ranking_type,
                "server": None,
                "server_confidence": server_detection.confidence,
                "server_source": server_detection.source,
                "server_warning": server_detection.warning,
                "server_detections": ",".join(str(value) for value in server_detection.detections),
                "data_guard_conflict": server_detection.conflict,
                "ocr_elements": len(ocr),
                "raw_text": metadata_text[:500],
            })
            print(f"SKIP | {screenshot.name} | missing validated server -> REVIEW")
            continue

        key = (server, ranking_type)
        grouped.setdefault(key, [])

        if ranking_type == "total_hero_power":
            snapshot = build_player_ranking_snapshot(
                rows=rows,
                server=server,
                ranking_type=ranking_type,
                source_file=screenshot.name,
                server_confidence=server_detection.confidence,
                server_source=server_detection.source,
                server_warning=server_detection.warning,
                data_guard_conflict=server_detection.conflict,
            )
            grouped[key].extend(snapshot.to_legacy_rows())
        else:
            for row in rows:
                row["source_file"] = screenshot.name
                row["server_confidence"] = server_detection.confidence
                row["server_source"] = server_detection.source
                row["server_warning"] = server_detection.warning
                row["data_guard_conflict"] = server_detection.conflict
                grouped[key].append(row)

    grouped = apply_ranking_guard(grouped)
    grouped = apply_ranking_power_sanity_guard(grouped)
    grouped = run_adaptive_review_ocr(
        grouped,
        reader=reader,
        screenshot_dir=SCREENSHOT_DIR,
        target_width=config["target_width"],
        target_height=config["target_height"],
        enabled=os.getenv("SENTINEL_REVIEW_OCR", "1") != "0",
    )
    grouped = reconcile_server_assignments_by_content(grouped)

    print("\n===== ZUSAMMENFASSUNG =====")

    final_grouped = {}

    for key, rows in grouped.items():
        if key[1] == "server_review":
            final_grouped[key] = rows
            print(f"\n{key[0]} - {key[1]}: {len(rows)} screenshots require review")
            continue

        tolerance = 0.003 if key[1] == "alliance_power" else 0.0003
        merged = merge_rows_by_power(rows, limit=150, tolerance=tolerance)

        final_grouped[key] = merged

        print(f"\nServer {key[0]} - {key[1]}")
        for row in merged:
            _safe_print(row["rank"], row["name"], row["power"])

    output_file = os.getenv("SENTINEL_OUTPUT_FILE") or str(snapshot_service.snapshot_output_dir(active_snapshot) / "lastwar_export.xlsx")
    if args.skip_excel:
        print("Excel export skipped by --skip-excel")
    else:
        export(final_grouped, filename=output_file)
    duration = time.perf_counter() - start_time
    import_report = build_import_run_report(final_grouped, screenshots=len(screenshots), runtime_seconds=duration, output_file=output_file)
    import_report = snapshot_service.bind_import_report(import_report, active_snapshot)
    snapshot_export_file = None
    if not args.skip_excel:
        snapshot_export_file = snapshot_service.mirror_export_to_snapshot(output_file, active_snapshot)
        if snapshot_export_file:
            import_report["snapshot_export_file"] = snapshot_export_file
    JsonImportRunRepository().save_latest_import(import_report)
    if args.finish_collection:
        snapshot_service.update_status(active_snapshot.id, "reviewing" if import_report.get("review_count") else "verified")
        print("Snapshot collection explicitly finished by --finish-collection.")
    elif str(active_snapshot.status).lower() == "open":
        snapshot_service.update_status(active_snapshot.id, "collecting")
        print("Snapshot bleibt nach Import auf COLLECTING fuer kontinuierliche Screenshot-Annahme.")
    else:
        print(f"Snapshot bleibt auf {active_snapshot.status.upper()} fuer kontinuierliche Screenshot-Annahme.")
    print("Import report geschrieben nach data/latest_import_report.json")
    if args.skip_command_center:
        print("Command Center rebuild skipped by --skip-command-center")
    else:
        command_center_files = generate_command_center()
        print(f"Command Center geschrieben nach {command_center_files['command_center']}")
        print(f"Review Dashboard geschrieben nach {command_center_files['review_dashboard']}")
        print(f"Review Evidence Pack geschrieben nach {command_center_files['review_evidence_pack']}")
    print(f"\nRuntime: {duration:.2f}s")


if __name__ == "__main__":
    main()
