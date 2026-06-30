"""Sentinel Data Guard checks for import-time data integrity.

Phase 1 protects server assignment.  The guard treats Warzone evidence found
inside OCR output as the strongest signal and prevents session/sheet context
from silently moving rows to the wrong server.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Optional

from parser.server import ServerDetection, extract_server_candidates


@dataclass(frozen=True)
class DataGuardEvidence:
    source: str
    server: int | None
    votes: int
    confidence: float
    detail: str


@dataclass(frozen=True)
class ServerAssignmentDecision:
    server: Optional[int]
    confidence: float
    source: str
    warning: Optional[str] = None
    detections: list[int] = field(default_factory=list)
    evidence: list[DataGuardEvidence] = field(default_factory=list)
    conflict: bool = False

    @property
    def is_valid(self) -> bool:
        return self.server is not None


def _collect_candidates(ocr_results: Iterable[tuple]) -> list[int]:
    candidates: list[int] = []
    for _box, text, _confidence in ocr_results:
        found = extract_server_candidates(str(text))
        if found:
            # One vote per OCR element. Multiple patterns in one text must not
            # inflate a single visible Warzone line.
            candidates.append(found[0])
    return candidates


def _majority_evidence(source: str, candidates: list[int]) -> DataGuardEvidence | None:
    if not candidates:
        return None
    counts = Counter(candidates)
    server, votes = counts.most_common(1)[0]
    total = sum(counts.values())
    confidence = votes / max(total, 1)
    return DataGuardEvidence(
        source=source,
        server=server,
        votes=votes,
        confidence=round(confidence, 4),
        detail=f"{votes}/{total} Warzone votes for server {server}",
    )


def resolve_server_assignment(
    metadata_detection: ServerDetection,
    row_ocr_results: Iterable[tuple],
    *,
    min_row_votes: int = 3,
) -> ServerAssignmentDecision:
    """Resolve final server assignment using Sentinel Data Guard evidence.

    Rule: repeated row-level Warzone evidence wins over metadata/session/sheet
    context.  This fixes the class of bugs where a screenshot showing Warzone
    #551 was later exported as #552 by downstream grouping.
    """
    row_candidates = _collect_candidates(row_ocr_results)
    row_evidence = _majority_evidence("row_warzone_majority", row_candidates)

    evidence: list[DataGuardEvidence] = []
    if metadata_detection.detections:
        meta_counts = Counter(metadata_detection.detections)
        meta_server, meta_votes = meta_counts.most_common(1)[0]
        meta_total = sum(meta_counts.values())
        evidence.append(
            DataGuardEvidence(
                source="metadata_ocr_consensus",
                server=meta_server,
                votes=meta_votes,
                confidence=round(meta_votes / max(meta_total, 1), 4),
                detail=f"{meta_votes}/{meta_total} metadata votes for server {meta_server}",
            )
        )
    if row_evidence:
        evidence.append(row_evidence)

    # Strong row evidence is authoritative.
    if row_evidence and row_evidence.votes >= min_row_votes:
        conflict = metadata_detection.server is not None and metadata_detection.server != row_evidence.server
        warning = None
        source = "data_guard:row_warzone_majority"
        if conflict:
            warning = f"server_assignment_conflict:metadata={metadata_detection.server}:row={row_evidence.server}"
            source = "data_guard:row_warzone_override"
        elif metadata_detection.warning:
            warning = f"metadata_{metadata_detection.warning}:row_warzone_validated"

        return ServerAssignmentDecision(
            server=row_evidence.server,
            confidence=row_evidence.confidence,
            source=source,
            warning=warning,
            detections=row_candidates or metadata_detection.detections,
            evidence=evidence,
            conflict=conflict,
        )

    # Otherwise keep the existing metadata consensus decision.
    return ServerAssignmentDecision(
        server=metadata_detection.server,
        confidence=metadata_detection.confidence,
        source=metadata_detection.source,
        warning=metadata_detection.warning,
        detections=metadata_detection.detections,
        evidence=evidence,
        conflict=False,
    )


# ---- Content-level operational guard --------------------------------------


def _row_server_confidence(rows: list[dict]) -> float:
    values: list[float] = []
    for row in rows:
        try:
            if row.get("server_confidence") is not None:
                values.append(float(row.get("server_confidence")))
        except (TypeError, ValueError):
            continue
    return sum(values) / len(values) if values else 0.0


def _row_power(row: dict) -> int | None:
    try:
        value = row.get("power")
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _powers(rows: list[dict]) -> list[int]:
    return [value for value in (_row_power(row) for row in rows) if value is not None]


def _alliance_tag(row: dict) -> str | None:
    value = str(row.get("alliance_tag") or "").strip()
    if value:
        return value.upper().strip("[] ")
    text = str(row.get("name") or row.get("raw_text") or "")
    # This extracts bracketed alliance tags from parsed row content only. It is
    # intrinsic OCR content and not based on filename or upload metadata.
    import re

    match = re.search(r"\[([^\]\[]{1,8})\]", text)
    if not match:
        return None
    return match.group(1).upper().strip()


def _alliance_tags(rows: list[dict]) -> set[str]:
    return {tag for tag in (_alliance_tag(row) for row in rows) if tag}


def _power_enclosure_score(suspect_rows: list[dict], target_rows: list[dict]) -> float:
    suspect_powers = _powers(suspect_rows)
    target_powers = _powers(target_rows)
    if not suspect_powers or not target_powers:
        return 0.0
    suspect_min, suspect_max = min(suspect_powers), max(suspect_powers)
    target_min, target_max = min(target_powers), max(target_powers)

    # Strong signal: the suspicious block's whole power range fits inside a
    # larger group of the same ranking type. This catches a misassigned scroll
    # segment without using filename timestamps or upload order.
    if target_min <= suspect_min and suspect_max <= target_max:
        return 1.0

    overlap_min = max(suspect_min, target_min)
    overlap_max = min(suspect_max, target_max)
    if overlap_max <= overlap_min:
        return 0.0
    suspect_span = max(suspect_max - suspect_min, 1)
    return max(0.0, min(1.0, (overlap_max - overlap_min) / suspect_span))


def _tag_overlap_score(suspect_rows: list[dict], target_rows: list[dict]) -> float:
    suspect_tags = _alliance_tags(suspect_rows)
    target_tags = _alliance_tags(target_rows)
    if not suspect_tags or not target_tags:
        return 0.0
    return len(suspect_tags & target_tags) / max(len(suspect_tags), 1)


def _mark_content_quarantined(rows: list[dict], *, original_server: int, target_server: int, score: float) -> None:
    warning = (
        "server_assignment_conflict:"
        f"quarantine_candidate_target={target_server}:detected={original_server}:score={score:.2f}"
    )
    for row in rows:
        previous = str(row.get("server_warning") or "")
        row["server_warning"] = warning if not previous else f"{previous};{warning}"
        row["server_source"] = "data_guard:quarantine"
        row["data_guard_conflict"] = True
        row["quarantine_reason"] = "server_assignment_conflict"
        row["quarantine_candidate_server"] = target_server


def reconcile_server_assignments_by_content(
    grouped: dict[tuple[object, str], list[dict]],
    *,
    max_suspect_rows: int = 20,
    min_target_rows: int = 25,
    min_score: float = 0.72,
) -> dict[tuple[object, str], list[dict]]:
    """Quarantine isolated server blocks using only screenshot content evidence.

    The Data Guard validates, blocks and explains. It must not silently repair
    server assignments by merging suspicious rows into another server. When a
    small, low-confidence block is better explained as part of another larger
    same-ranking group, the block is moved to a review/quarantine sheet. This
    avoids both wrong standalone sheets and wrong auto-merges.

    This guard intentionally avoids filename timestamps and filename patterns.
    Evidence is based on parsed row content: power continuity, alliance-tag
    overlap, row counts, and server confidence.
    """
    numeric_keys = [key for key in grouped if isinstance(key[0], int) and key[1] != "server_review"]
    if not numeric_keys:
        return grouped

    quarantines: dict[tuple[int, str], tuple[int, float]] = {}

    for suspect_key in numeric_keys:
        suspect_server, ranking_type = suspect_key
        suspect_rows = list(grouped.get(suspect_key) or [])
        if not suspect_rows or len(suspect_rows) > max_suspect_rows:
            continue

        suspect_confidence = _row_server_confidence(suspect_rows)
        # High-confidence small groups are allowed to stand unless content
        # evidence overwhelmingly proves they belong elsewhere.
        low_confidence_bonus = 1.0 if suspect_confidence < 0.8 else 0.0

        best_target: int | None = None
        best_score = 0.0

        for target_key in numeric_keys:
            target_server, target_ranking = target_key
            if target_key == suspect_key or target_ranking != ranking_type:
                continue
            target_rows = list(grouped.get(target_key) or [])
            if len(target_rows) < min_target_rows or len(target_rows) <= len(suspect_rows):
                continue

            power_score = _power_enclosure_score(suspect_rows, target_rows)
            tag_score = _tag_overlap_score(suspect_rows, target_rows)
            size_score = min(1.0, len(target_rows) / max(len(suspect_rows) * 3, 1))

            # Content-first scoring. Tags and power continuity carry the
            # decision. Confidence only helps to avoid overcorrecting real small
            # server groups.
            score = (0.45 * power_score) + (0.35 * tag_score) + (0.10 * size_score) + (0.10 * low_confidence_bonus)

            if score > best_score:
                best_score = score
                best_target = int(target_server)

        if best_target is not None and best_score >= min_score:
            quarantines[(int(suspect_server), ranking_type)] = (best_target, best_score)
            _mark_content_quarantined(
                suspect_rows,
                original_server=int(suspect_server),
                target_server=best_target,
                score=best_score,
            )

    if not quarantines:
        return grouped

    new_grouped: dict[tuple[object, str], list[dict]] = {}
    for key, rows in grouped.items():
        server, ranking_type = key
        if not isinstance(server, int):
            new_grouped.setdefault(key, []).extend(rows)
            continue
        quarantine = quarantines.get((server, ranking_type))
        if quarantine is not None:
            target, _score = quarantine
            quarantine_key = ("REVIEW", "data_guard_quarantine")
            for row in rows:
                row["original_server"] = server
                row["ranking_type"] = ranking_type
                row["candidate_server"] = target
            new_grouped.setdefault(quarantine_key, []).extend(rows)
        else:
            new_grouped.setdefault(key, []).extend(rows)
    return new_grouped
