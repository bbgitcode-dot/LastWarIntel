"""Recruitment assessment domain constants.

This module contains recruitment-specific assessment vocabulary. It deliberately
contains no evaluation logic. Domain logic lives in recruitment assessment rules;
the generic Assessment Engine remains unaware of recruitment semantics.
"""

from __future__ import annotations

RECRUITMENT_WINDOW_TITLE = "Recruitment Window"
RECRUITMENT_WINDOW_TAGS = ("recruitment", "opportunity")

RECRUITABILITY_INDICATOR_TITLE = "Recruitability"
TALENT_VALUE_INDICATOR_TITLE = "Talent Value"
DECLINE_FACT_TAG = "decline"
