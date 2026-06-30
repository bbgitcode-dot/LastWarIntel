"""Sentinel Data Quality Loop.

The Quality Loop is an automatic recovery stage between the first OCR pass and
manual review.  It does not guess or change business decisions.  It creates
additional OCR attempts from content-derived image enhancements and lets the
Sentinel Data Guard validate the recovered evidence again.

Design rules:
* no filename or timestamp based decisions
* max three total attempts including the original pass
* recovery is field/content driven
* Data Guard remains the final authority
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol

import cv2
import numpy as np

from ocr.provider import OCRResult, OcrProvider
from parser.server import ServerDetection, detect_server_consensus_from_ocr
from parser.data_guard import ServerAssignmentDecision, resolve_server_assignment


@dataclass(frozen=True)
class RecoveryAttempt:
    attempt: int
    reason: str
    strategy: str
    before_confidence: float
    after_confidence: float
    accepted: bool
    detail: str


@dataclass(frozen=True)
class QualityLoopResult:
    decision: ServerAssignmentDecision
    metadata_ocr: list[OCRResult]
    row_ocr: list[OCRResult]
    attempts: list[RecoveryAttempt] = field(default_factory=list)

    @property
    def recovered(self) -> bool:
        return any(attempt.accepted for attempt in self.attempts)

    @property
    def warning_suffix(self) -> str:
        if not self.attempts:
            return ""
        last = self.attempts[-1]
        state = "recovered" if self.recovered else "unresolved"
        return f"quality_loop:{state}:attempt={last.attempt}:strategy={last.strategy}"


class RecoveryStrategy(Protocol):
    name: str

    def supports(self, reason: str) -> bool:
        ...

    def process(self, image: np.ndarray) -> np.ndarray:
        ...


class ContrastUpscaleStrategy:
    name = "contrast_upscale"

    def supports(self, reason: str) -> bool:
        return reason in {"server_confidence_low", "server_not_detected", "server_conflict"}

    def process(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        enhanced = cv2.resize(enhanced, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)


class SharpenThresholdStrategy:
    name = "sharpen_threshold"

    def supports(self, reason: str) -> bool:
        return True

    def process(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        blur = cv2.GaussianBlur(gray, (0, 0), 1.2)
        sharp = cv2.addWeighted(gray, 1.7, blur, -0.7, 0)
        thresh = cv2.adaptiveThreshold(
            sharp,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            7,
        )
        thresh = cv2.resize(thresh, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)


class HeaderCropStrategy:
    name = "header_crop"

    def supports(self, reason: str) -> bool:
        return reason in {"server_confidence_low", "server_not_detected", "server_conflict"}

    def process(self, image: np.ndarray) -> np.ndarray:
        height, width = image.shape[:2]
        # Server and ranking metadata are usually repeated in the upper portion
        # of the Last War ranking screen.  This is content geometry, not a
        # filename/timestamp assumption.
        top = image[: max(1, int(height * 0.32)), :width]
        gray = cv2.cvtColor(top, cv2.COLOR_BGR2GRAY) if len(top.shape) == 3 else top
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        enhanced = cv2.resize(enhanced, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)


def _reason_from_decision(decision: ServerAssignmentDecision) -> str:
    warning = decision.warning or ""
    if decision.conflict or "conflict" in warning:
        return "server_conflict"
    if not decision.is_valid:
        return "server_not_detected"
    if decision.confidence < 0.85:
        return "server_confidence_low"
    return "generic_low_confidence"


def _is_better(candidate: ServerAssignmentDecision, current: ServerAssignmentDecision) -> bool:
    if candidate.is_valid and not current.is_valid:
        return True
    if not candidate.is_valid:
        return False
    if candidate.conflict and not current.conflict:
        return False
    if candidate.confidence >= max(0.85, current.confidence + 0.10):
        return True
    # Same server with more confidence is a useful recovery even below the
    # automatic import threshold; Data Guard may still send it to review later.
    if candidate.server == current.server and candidate.confidence > current.confidence:
        return True
    return False


def run_server_quality_loop(
    *,
    reader: OcrProvider,
    image: np.ndarray,
    initial_metadata_ocr: list[OCRResult],
    initial_row_ocr: list[OCRResult],
    initial_decision: ServerAssignmentDecision,
    max_attempts: int = 3,
) -> QualityLoopResult:
    """Try targeted OCR recovery for uncertain server assignments.

    The original OCR pass counts as attempt 1.  This function may perform up to
    two additional image-enhancement attempts.  The recovered OCR is only used
    when the Data Guard decision improves; otherwise the original decision is
    preserved and manual review remains the safe fallback.
    """
    if max_attempts <= 1:
        return QualityLoopResult(initial_decision, initial_metadata_ocr, initial_row_ocr, [])

    if initial_decision.is_valid and not initial_decision.conflict and initial_decision.confidence >= 0.85:
        return QualityLoopResult(initial_decision, initial_metadata_ocr, initial_row_ocr, [])

    reason = _reason_from_decision(initial_decision)
    strategies: list[RecoveryStrategy] = [HeaderCropStrategy(), ContrastUpscaleStrategy(), SharpenThresholdStrategy()]
    attempts: list[RecoveryAttempt] = []
    best_decision = initial_decision
    best_metadata = initial_metadata_ocr
    best_rows = initial_row_ocr

    attempt_no = 2
    for strategy in strategies:
        if attempt_no > max_attempts:
            break
        if not strategy.supports(reason):
            continue

        processed = strategy.process(image)
        try:
            metadata_ocr = reader.read_metadata(processed)
            row_ocr = reader.read_rows(processed)
        except Exception as exc:  # pragma: no cover - OCR provider/runtime dependent
            attempts.append(
                RecoveryAttempt(
                    attempt=attempt_no,
                    reason=reason,
                    strategy=strategy.name,
                    before_confidence=best_decision.confidence,
                    after_confidence=best_decision.confidence,
                    accepted=False,
                    detail=f"ocr_recovery_failed:{type(exc).__name__}",
                )
            )
            attempt_no += 1
            continue

        metadata_detection: ServerDetection = detect_server_consensus_from_ocr(metadata_ocr, min_occurrences=3)
        decision = resolve_server_assignment(metadata_detection, row_ocr)
        accepted = _is_better(decision, best_decision)
        attempts.append(
            RecoveryAttempt(
                attempt=attempt_no,
                reason=reason,
                strategy=strategy.name,
                before_confidence=best_decision.confidence,
                after_confidence=decision.confidence,
                accepted=accepted,
                detail=decision.warning or decision.source,
            )
        )
        if accepted:
            best_decision = decision
            best_metadata = metadata_ocr
            best_rows = row_ocr
            if best_decision.is_valid and not best_decision.conflict and best_decision.confidence >= 0.95:
                break
        attempt_no += 1

    return QualityLoopResult(best_decision, best_metadata, best_rows, attempts)
