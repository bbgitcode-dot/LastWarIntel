import re


def normalize_server_number(value):
    value = str(value)

    if len(value) == 4 and value.startswith("8"):
        return int(value[-3:])

    return int(value)


def detect_server(text):
    patterns = [
        r"Warzone\s*[#\{\}]?\s*(\d{3,4})",
        r"Wagzone\s*[#\{\}]?\s*(\d{3,4})",
        r"Waqzone\s*[#\{\}]?\s*(\d{3,4})",
        r"Waizone\s*[#\{\}]?\s*(\d{3,4})",
        r"Wauzone\s*[#\{\}]?\s*(\d{3,4})",
        r"Watzone\s*[#\{\}]?\s*(\d{3,4})",
        r"Wagzong\s*[#\{\}]?\s*(\d{3,4})",
        r"Waqzong\s*[#\{\}]?\s*(\d{3,4})",
        r"Qagzone\s*[#\{\}]?\s*(\d{3,4})",
        r"Qagzong\s*[#\{\}]?\s*(\d{3,4})",
        r"[WQ][a-zA-Z]{2,12}\s*[#\{\}]?\s*(\d{3,4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return normalize_server_number(match.group(1))

    return None


def detect_ranking_type(text):
    upper = text.upper()

    if "ALLIANCE POWER" in upper:
        return "alliance_power"

    if "TOTAL HERO POWER" in upper:
        return "total_hero_power"

    return "unknown"