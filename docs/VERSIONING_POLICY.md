# Versioning Policy – Sentinel

## Version format

Sentinel currently uses semantic-like sprint versions:

```text
v0.9.5.<sprint>
```

Example:

```text
v0.9.5.125
```

## Release rule

Every sprint must produce a full ZIP package. Chat snippets are not a release artifact.

## Required release contents

- Full source tree.
- Updated `version.py`.
- Updated `.commit`.
- Updated `/docs/RELEASE_NOTES.md`.
- Updated `/docs/PATCH_SUMMARY.md`.
- Updated project status / roadmap when relevant.
- Commit command.
- Annotated tag command.

## Commit convention

Use a concise conventional prefix:

- `feat(...)`
- `fix(...)`
- `perf(...)`
- `docs(...)`
- `test(...)`
- `refactor(...)`

Example:

```bash
git commit -m "docs(project): consolidate handover documentation for v0.9.5.125"
```

## Tag convention

```bash
git tag -a v0.9.5.125 -m "v0.9.5.125 Documentation Consolidation and Handover"
```

## Deployment convention

The Proud Owner deploys by replacing the working project with the full ZIP release, then running the agreed validation commands locally.
