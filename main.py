from pathlib import Path
import json

from parser.image import load_and_normalize_image
from parser.ocr import create_reader, read_ocr, ocr_to_text
from parser.server import detect_server, detect_ranking_type
from parser.debug import draw_debug_boxes
from parser.ranking import parse_ranking_rows, merge_rows_by_power
from parser.excel import export


CONFIG_FILE = Path("config_pc.json")
SCREENSHOT_DIR = Path("screenshots")


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    config = load_config()
    reader = create_reader()

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

        ocr = read_ocr(reader, image)
        text = ocr_to_text(ocr)

        server = detect_server(text)
        ranking_type = detect_ranking_type(text)

        print("Server :", server)
        print("Typ    :", ranking_type)
        print("OCR    :", len(ocr), "Elemente")

        draw_debug_boxes(
            image,
            ocr,
            f"output/debug/{screenshot.stem}.png"
        )

        rows = parse_ranking_rows(ocr)

        key = (server, ranking_type)
        grouped.setdefault(key, [])

        for row in rows:
            row["source_file"] = screenshot.name
            grouped[key].append(row)

    print("\n===== ZUSAMMENFASSUNG =====")

    final_grouped = {}

    for key, rows in grouped.items():
        tolerance = 0.003 if key[1] == "alliance_power" else 0.0003
        merged = merge_rows_by_power(rows, limit=10, tolerance=tolerance)

        final_grouped[key] = merged

        print(f"\nServer {key[0]} - {key[1]}")
        for row in merged:
            print(row["rank"], row["name"], row["power"])

    export(final_grouped)


if __name__ == "__main__":
    main()