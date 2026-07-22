# Modus Operandi — Confirmed for v0.9.5.148

- Releases are delivered only as complete ZIP packages.
- Every release includes a consistent version bump and root `.commit`.
- `RELEASE_NOTES.md`, `PATCH_SUMMARY.md`, and affected status documents are updated in the same package.
- Chat snippets are never the release artifact.
- Benchmarks are the authoritative truth for outcome claims.
- No feature receives credit for a clearance produced by another lane.
- Operational Truth, Ground Truth, snapshots, and exports are never silently corrected.

---

# Modus Operandi – Sentinel

## Roles

- **Proud Owner:** project owner, final decision maker, operational tester.
- **Mimir:** strategic copilot, implementation partner, documentation steward.

## Delivery rule

No snippets as final sprint deliverables.

Each sprint release must be a complete ZIP package that can be deployed or tested as a whole.

## Standard paths

- Documentation: `/docs`
- Release notes: `/docs/RELEASE_NOTES.md`
- Patch summary: `/docs/PATCH_SUMMARY.md`
- Next-chat handover: `/docs/NEXT_CHAT.md`
- Commit message: `/.commit`
- Version: `/version.py`

## Release package requirements

Every release should include:

1. full source tree;
2. version bump;
3. updated `.commit`;
4. release notes;
5. patch summary;
6. updated project status when behavior or strategy changes;
7. validation statement;
8. commit and tag commands.

## Commit / tag convention

Example:

```bash
git add .
git commit -m "docs(project): consolidate handover documentation for v0.9.5.125"
git tag -a v0.9.5.125 -m "v0.9.5.125 Documentation Consolidation and Handover"
```

## Engineering principles

- Evidence before inference.
- Quarantine over false truth.
- Operational Truth is protected.
- Read-only inference stays read-only.
- Current screenshot proof is preferred over historical memory.
- Matching, identity, display fidelity, and strategic intelligence are separate layers.
- Performance optimizations must not weaken DataGuard.

## Sprint rhythm

1. Proud Owner provides latest ZIP and relevant reports/screenshots.
2. Mimir reads the package and identifies the narrow sprint goal.
3. Mimir implements or documents the sprint.
4. Mimir validates with smoke tests/compile/zip integrity where possible.
5. Mimir returns a complete ZIP and commit/tag commands.
6. Proud Owner runs local validation and returns reports.
7. Next sprint is selected from evidence, not guessing.

## Language and style

Documentation should be direct, explicit, and audit-friendly. Avoid vague claims such as “improved OCR” unless the metrics prove it.
