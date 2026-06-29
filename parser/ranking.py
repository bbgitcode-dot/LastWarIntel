import re

from parser.normalization import HeroPowerNormalizer

_HERO_POWER_NORMALIZER = HeroPowerNormalizer()


def box_center(box):
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def clean_power(text):
    match = re.search(r"[0-9OIl|][0-9OIl|,\.\s-]{6,}[0-9OIl|]", str(text or ""))
    if not match:
        return None

    normalized = _HERO_POWER_NORMALIZER.normalize(match.group(0))
    digits = normalized.value

    if len(digits) < 7:
        return None

    return int(digits)


def is_power(text):
    return clean_power(text) is not None


def is_noise(text):
    upper = text.upper()
    noise_words = [
        "ALLIANCE POWER",
        "TOTAL HERO POWER",
        "RANKING",
        "ALLIANCE NAME",
        "COMMANDER",
        "POWER",
        "NOTE:",
        "LEADERBOARD",
        "UPDATES",
        "IMPORTANT",
        "PRESIDENT",
    ]
    return any(word in upper for word in noise_words)


def is_warzone(text):
    return re.search(
        r"[WQ][a-zA-Z0-9,\.\s]*z[oa][nmg][a-zA-Z0-9,\.\s]*[#\{\}]?\s*\d{3,4}",
        text,
        re.IGNORECASE
    ) is not None or re.search(
        r"Warzone\s*[#\{\}]?\s*\d{3,4}",
        text,
        re.IGNORECASE
    ) is not None


def is_rank(text):
    text = text.strip()
    return re.fullmatch(r"\d{1,3}", text) is not None


def clean_name_part(text):
    text = text.strip()

    if not text:
        return ""

    if is_noise(text):
        return ""

    if is_warzone(text):
        return ""

    if is_rank(text):
        return ""

    if is_power(text):
        return ""

    return text


def cluster_ocr_by_rows(ocr_results, y_tolerance=28):
    items = []

    for box, text, confidence in ocr_results:
        x, y = box_center(box)

        if y < 90:
            continue

        if is_noise(text):
            continue

        items.append({
            "x": x,
            "y": y,
            "text": text,
            "confidence": confidence,
        })

    items.sort(key=lambda item: item["y"])

    rows = []

    for item in items:
        placed = False

        for row in rows:
            if abs(row["y"] - item["y"]) <= y_tolerance:
                row["items"].append(item)
                row["y"] = sum(i["y"] for i in row["items"]) / len(row["items"])
                placed = True
                break

        if not placed:
            rows.append({
                "y": item["y"],
                "items": [item]
            })

    for row in rows:
        row["items"].sort(key=lambda item: item["x"])

    return rows


def parse_ranking_rows(ocr_results):
    clustered_rows = cluster_ocr_by_rows(ocr_results)

    parsed = []

    for row in clustered_rows:
        texts = [item["text"] for item in row["items"]]

        power_items = [
            item for item in row["items"]
            if is_power(item["text"])
        ]

        if not power_items:
            continue

        power_item = max(power_items, key=lambda item: item["x"])
        power = clean_power(power_item["text"])

        rank_items = [
            item for item in row["items"]
            if item["x"] < power_item["x"] and is_rank(str(item["text"]))
        ]
        ocr_rank = None
        if rank_items:
            rank_item = min(rank_items, key=lambda item: item["x"])
            try:
                ocr_rank = int(str(rank_item["text"]).strip())
            except ValueError:
                ocr_rank = None

        name_parts = []

        for item in row["items"]:
            # Name steht links vom Powerwert
            if item["x"] >= power_item["x"]:
                continue

            # OCR rank is stored separately and must not pollute names.
            if is_rank(str(item["text"])):
                continue

            part = clean_name_part(item["text"])

            if part:
                name_parts.append(part)

        name = " ".join(name_parts).strip()

        parsed.append({
            "name": name,
            "power": power,
            "ocr_rank": ocr_rank,
            "raw_text": " | ".join(texts),
            "y": row["y"],
            "confidence": min(item["confidence"] for item in row["items"]),
        })

    parsed.sort(key=lambda row: row["power"], reverse=True)

    return parsed


def infer_ranking_type_from_values(current_type, rows):
    """Infer ranking type from parsed numeric values when OCR classification failed.

    OCR header detection remains authoritative. This fallback is used only when
    the ranking type is missing or unknown.
    """
    if current_type not in (None, "unknown"):
        return current_type

    powers = [row.get("power") for row in rows if row.get("power")]

    if not powers:
        return "unknown"

    highest_value = max(powers)

    if highest_value > 1_000_000_000:
        return "alliance_power"

    return "total_hero_power"


def merge_rows_by_power(items, limit=10, tolerance=0.003):
    merged = []

    for item in sorted(items, key=lambda row: row["power"], reverse=True):
        power = item.get("power")
        if not power:
            continue

        duplicate = None

        for existing in merged:
            existing_power = existing["power"]
            diff = abs(existing_power - power) / max(existing_power, power)

            if diff <= tolerance:
                duplicate = existing
                break

        if duplicate:
            old_name = duplicate.get("name", "")
            new_name = item.get("name", "")

            if len(new_name) > len(old_name):
                duplicate["name"] = new_name

            duplicate["power"] = max(duplicate["power"], power)
        else:
            merged.append(item)

    merged.sort(key=lambda row: row["power"], reverse=True)

    previous_ocr_rank = None
    for idx, row in enumerate(merged[:limit], start=1):
        row["computed_rank"] = idx
        ocr_rank = row.get("ocr_rank")
        warnings = []
        existing_warning = row.get("rank_warning")
        if existing_warning:
            warnings.extend(str(existing_warning).split(";"))

        if ocr_rank is not None:
            row["rank"] = int(ocr_rank)
            if int(ocr_rank) != idx:
                warnings.append(f"ocr_rank_differs_from_computed:{ocr_rank}!={idx}")
            if previous_ocr_rank is not None and int(ocr_rank) > previous_ocr_rank + 1:
                missing = ",".join(str(value) for value in range(previous_ocr_rank + 1, int(ocr_rank)))
                warnings.append(f"possible_missing_rank_before:{missing}")
            previous_ocr_rank = int(ocr_rank)
        else:
            # Missing OCR rank is common when OCR captures only names/power.
            # Do not mark every row as a ranking integrity warning.
            # True integrity warnings are reserved for observed rank gaps or
            # mismatches when OCR rank evidence exists.
            row["rank"] = idx

        row["rank_warning"] = ";".join(dict.fromkeys(warnings))

    return merged[:limit]