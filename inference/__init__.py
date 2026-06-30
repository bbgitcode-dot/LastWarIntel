"""Sentinel Inference Layer.

Inference operates above Operational Truth. It never changes parser output or
runtime exports; it produces explicit, explainable conclusions for validation
and future intelligence workflows.
"""

from .context_engine import apply_contextual_inference, ContextInference

__all__ = ["apply_contextual_inference", "ContextInference"]
