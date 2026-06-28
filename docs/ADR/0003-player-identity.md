# ADR-0003 – Player Identity

Status: Accepted

## Context
Player names, alliance tags and OCR output are not stable identifiers.

## Decision
Sentinel identifies players using a persistent identity assembled from multiple signals (server, normalized name, alliance history, hero power continuity and future unique evidence).

## Consequences
- Historical tracking survives OCR errors.
- Alliance changes do not create new identities.
- Identity confidence is explicit.
