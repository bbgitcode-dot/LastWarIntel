"""
Sentinel OCR Configuration

OCR is an observation sensor. The default profile prioritizes data quality for
transfer-baseline imports over speed.
"""

DEFAULT_OCR_LANGUAGES = [
    "en",
    "ch_sim",
    "ch_tra",
    "ja",
    "ko",
]

OCR_GPU = False
