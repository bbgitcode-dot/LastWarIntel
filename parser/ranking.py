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
    """Legacy helper kept for compatibility.

    New ranking parsing uses build_aligned_ranking_rows() below. This helper is
    still used by older smoke tests and callers that expect broad Y clustering.
    """
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
    """Parse ranking rows using bounding-box based row alignment.

    The parser no longer trusts OCR result order or broad text clustering. It
    reconstructs every visible card row from layout anchors, primarily the THP
    value and optional rank token, before extracting name text.
    """
    from parser.alignment import build_aligned_ranking_rows

    aligned_rows = build_aligned_ranking_rows(
        ocr_results,
        is_power=is_power,
        clean_power=clean_power,
        is_rank=is_rank,
        is_noise=is_noise,
        is_warzone=is_warzone,
    )

    parsed = []

    for row in aligned_rows:
        power_item = row.power_token
        if power_item is None:
            continue

        power = clean_power(power_item.text)
        if power is None:
            continue

        ocr_rank = None
        if row.rank_token is not None:
            try:
                ocr_rank = int(str(row.rank_token.text).strip())
            except ValueError:
                ocr_rank = None

        from parser.columns import reconstruct_columns

        columns = reconstruct_columns(
            row.tokens,
            rank_token=row.rank_token,
            power_token=power_item,
            is_rank=is_rank,
            is_power=is_power,
        )

        name = columns.raw_name

        warnings = list(row.warnings)
        warnings.extend(columns.warnings)
        if not name:
            warnings.append("missing_name_after_alignment")

        corrections = list(columns.corrections)

        parsed.append({
            "name": name,
            "power": power,
            "ocr_rank": ocr_rank,
            "raw_text": " | ".join(row.texts),
            "y": row.y,
            "confidence": row.confidence,
            "alignment_warning": ";".join(dict.fromkeys(warnings)),
            "column_corrections": ";".join(dict.fromkeys(corrections)),
        })

    # Preserve visual order here. The merge step is responsible for final power
    # sorting and duplicate handling across screenshots. Keeping visual order in
    # raw parse output makes debugging row shifts much easier.
    parsed.sort(key=lambda item: item.get("y", 0))
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


def _explicit_visible_rank(row):
    for key in ("visible_rank", "ocr_rank", "rank"):
        value = row.get(key)
        try:
            if value is not None and value != "":
                return int(float(value))
        except (TypeError, ValueError):
            continue
    return None


def _raw_identity_lock(row):
    """Keep raw OCR identity alongside normalized/canonical identity fields.

    v0.9.5.90 makes raw identity a protected Operational Truth surface.
    Normalized names can still exist for matching, but they must never replace
    the observed screenshot display in exports or review placeholders.
    """
    row.setdefault("raw_player_name", row.get("player_name") or row.get("name"))
    row.setdefault("raw_alliance_tag", row.get("alliance_tag"))
    row.setdefault("raw_alliance_name", row.get("name"))
    row.setdefault("observed_name", row.get("player_name") or row.get("name"))
    row.setdefault("observed_alliance", row.get("alliance_tag"))
    return row


def merge_rows_by_power(items, limit=10, tolerance=0.003):
    """Merge ranking rows while preserving visible rank slots when available.

    The historical implementation sorted every row by power and then rewrote
    ranks. That is unsafe for OCR pipelines: one recovered/truncated power can
    move a screenshot row to a different slot. Since v0.9.5.90, an explicit
    visible rank is a lock. Power is still used for duplicate handling and for
    rows without rank evidence, but it cannot rewrite a visible slot.
    """
    prepared = [_raw_identity_lock(dict(item)) for item in items if item.get("power") not in (None, "")]
    has_visible_slots = any(_explicit_visible_rank(row) is not None for row in prepared)

    if not has_visible_slots:
        merged = []
        for item in sorted(prepared, key=lambda row: row["power"], reverse=True):
            power = item.get("power")
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
                    duplicate["raw_alliance_name"] = item.get("raw_alliance_name") or new_name
                    duplicate["raw_player_name"] = item.get("raw_player_name") or item.get("player_name")
                duplicate["power"] = max(duplicate["power"], power)
            else:
                merged.append(item)
        merged.sort(key=lambda row: row["power"], reverse=True)
        for idx, row in enumerate(merged[:limit], start=1):
            row["computed_rank"] = idx
            row["rank"] = idx
            row["operational_rank"] = idx
            row["rank_slot_preserved"] = False
            row["rank_warning"] = row.get("rank_warning") or ""
        return merged[:limit]

    by_slot = {}
    unranked = []
    for item in prepared:
        slot = _explicit_visible_rank(item)
        if slot is None:
            unranked.append(item)
            continue
        item["visible_rank"] = slot
        item.setdefault("ocr_rank", slot)
        existing = by_slot.get(slot)
        if existing is None:
            by_slot[slot] = item
            continue
        existing_power = existing.get("power") or 0
        item_power = item.get("power") or 0
        if item_power > existing_power or len(str(item.get("name") or "")) > len(str(existing.get("name") or "")):
            warnings = [str(existing.get("rank_warning") or "").strip(), "duplicate_visible_rank_slot"]
            item["rank_warning"] = ";".join(part for part in dict.fromkeys(warnings) if part)
            by_slot[slot] = item
        else:
            warnings = [str(existing.get("rank_warning") or "").strip(), "duplicate_visible_rank_slot"]
            existing["rank_warning"] = ";".join(part for part in dict.fromkeys(warnings) if part)

    merged = [by_slot[slot] for slot in sorted(by_slot)]
    merged.extend(sorted(unranked, key=lambda row: row.get("power") or 0, reverse=True))

    previous_visible_rank = None
    power_order = {id(row): idx for idx, row in enumerate(sorted(merged, key=lambda row: row.get("power") or 0, reverse=True), start=1)}
    for idx, row in enumerate(merged[:limit], start=1):
        visible_rank = _explicit_visible_rank(row)
        warnings = []
        for key in ("rank_warning", "alignment_warning"):
            if row.get(key):
                warnings.extend(str(row.get(key)).split(";"))

        row["computed_rank"] = idx
        if visible_rank is not None:
            row["visible_rank"] = visible_rank
            row["rank"] = visible_rank
            row["operational_rank"] = visible_rank
            row["rank_slot_preserved"] = True
            if power_order.get(id(row)) != idx:
                warnings.append(f"power_order_differs_from_visible_slot:{power_order.get(id(row))}!={idx}")
            if previous_visible_rank is not None and visible_rank > previous_visible_rank + 1:
                missing = ",".join(str(value) for value in range(previous_visible_rank + 1, visible_rank))
                warnings.append(f"possible_missing_rank_before:{missing}")
            previous_visible_rank = visible_rank
        else:
            row["rank"] = idx
            row["operational_rank"] = idx
            row["rank_slot_preserved"] = False

        row["rank_warning"] = ";".join(dict.fromkeys(part for part in warnings if part))

    return merged[:limit]
