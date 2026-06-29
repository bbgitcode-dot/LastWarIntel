from pathlib import Path
import json
import os
import sys
import time

from parser.image import load_and_normalize_image
from parser.ocr import create_reader, read_ocr, read_metadata_ocr, ocr_to_text
from parser.server import detect_ranking_type, detect_server_consensus_from_ocr
from parser.debug import draw_debug_boxes
from parser.ranking import (
    parse_ranking_rows,
    merge_rows_by_power,
    infer_ranking_type_from_values,
)
from parser.player_ranking import build_player_ranking_snapshot
from parser.excel import export


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


def main():
    _configure_stdout()
    config = load_config()
    start_time = time.perf_counter()
    reader = create_reader()
    print(f"OCR Provider: {reader.info.engine} ({reader.info.name})")
    print(f"OCR Metadata Languages: {list(reader.info.metadata_languages)}")
    print(f"OCR Row Languages: {list(reader.info.row_languages)}")

    screenshots = sorted(
        list(SCREENSHOT_DIR.glob("*.png")) +
        list(SCREENSHOT_DIR.glob("*.jpg"))
    )

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
        server_detection = detect_server_consensus_from_ocr(metadata_ocr, min_occurrences=3)
        server = server_detection.server
        ranking_type = detect_ranking_type(metadata_text)

        # Row OCR may use multilingual readers depending on the selected profile.
        ocr = read_ocr(reader, image)
        row_text = ocr_to_text(ocr)
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
            )
            grouped[key].extend(snapshot.to_legacy_rows())
        else:
            for row in rows:
                row["source_file"] = screenshot.name
                row["server_confidence"] = server_detection.confidence
                row["server_source"] = server_detection.source
                row["server_warning"] = server_detection.warning
                grouped[key].append(row)

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

    output_file = os.getenv("SENTINEL_OUTPUT_FILE", "output/lastwar_export.xlsx")
    export(final_grouped, filename=output_file)
    duration = time.perf_counter() - start_time
    print(f"\nRuntime: {duration:.2f}s")


if __name__ == "__main__":
    main()
