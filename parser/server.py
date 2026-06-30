import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional


def normalize_server_number(value):
    value = str(value)

    if len(value) == 4 and value.startswith("8"):
        return int(value[-3:])

    return int(value)


_SERVER_PATTERNS = [
    # Pattern-first server extraction. Mobile screenshots and non-English
    # clients often repeat the server as "#552" on every ranking row while the
    # header text may be localized (for example "Kriegszone #552").  The hash
    # + 3/4 digit pattern is language-neutral and still conservative because
    # rank values and power values do not use this shape.
    r"[#＃]\s*(\d{3,4})",
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
    # Common localized labels remain useful as fallback signals, but they are
    # deliberately secondary to the language-neutral #number pattern above.
    r"Kriegszone\s*[#\{\}]?\s*(\d{3,4})",
    r"Zona(?:\s+de\s+guerra)?\s*[#\{\}]?\s*(\d{3,4})",
    r"Zone(?:\s+de\s+guerre)?\s*[#\{\}]?\s*(\d{3,4})",
]



@dataclass(frozen=True)
class ServerDetection:
    server: Optional[int]
    confidence: float
    source: str
    detections: list[int] = field(default_factory=list)
    warning: Optional[str] = None


def extract_server_candidates(text):
    candidates = []
    for pattern in _SERVER_PATTERNS:
        for match in re.finditer(pattern, text or "", re.IGNORECASE):
            try:
                candidates.append(normalize_server_number(match.group(1)))
            except (TypeError, ValueError):
                continue
    return candidates


def detect_server(text):
    candidates = extract_server_candidates(text)
    return candidates[0] if candidates else None


def detect_server_consensus_from_ocr(ocr_results, min_occurrences: int = 3) -> ServerDetection:
    """Detect server by consensus from repeated Warzone OCR hits.

    A server is accepted automatically only if the same Warzone appears at least
    ``min_occurrences`` times. Lower evidence is reported as REVIEW instead of
    silently accepting possibly wrong metadata.
    """
    candidates = []
    for _box, text, _confidence in ocr_results:
        item_candidates = extract_server_candidates(str(text))
        if item_candidates:
            # Count one vote per OCR box. Multiple regex patterns may match the
            # same text and must not inflate consensus evidence.
            candidates.append(item_candidates[0])

    if not candidates:
        return ServerDetection(
            server=None,
            confidence=0.0,
            source="ocr_consensus",
            detections=[],
            warning="server_not_detected",
        )

    counts = Counter(candidates)
    server, occurrences = counts.most_common(1)[0]
    total = sum(counts.values())
    agreement = occurrences / max(total, 1)

    if occurrences >= min_occurrences:
        # The core rule is: three matching Warzone detections are sufficient
        # for automatic assignment. Conflicting low-count candidates remain
        # visible in detections/confidence, but they should not turn every
        # row into a server warning.
        return ServerDetection(
            server=server,
            confidence=round(agreement, 4),
            source="ocr_consensus",
            detections=candidates,
            warning=None,
        )

    return ServerDetection(
        server=None,
        confidence=round(agreement, 4),
        source="ocr_consensus",
        detections=candidates,
        warning=f"server_consensus_below_threshold:{server}:{occurrences}/{min_occurrences}",
    )


def detect_ranking_type(text):
    upper = text.upper()

    if "ALLIANCE POWER" in upper:
        return "alliance_power"

    if "TOTAL HERO POWER" in upper:
        return "total_hero_power"

    return "unknown"
