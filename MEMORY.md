# Project Memory

## Product identity

- Product name: 同频：真实标签.
- Canonical repository: `https://github.com/songconmaisaix31-design/tongpin-real-tags` (repository ID `1342494025`).
- The former `https://github.com/songconmaisaix31-design/xxx` URL redirects to the same repository ID; use the canonical URL for current links and clones.
- Status: `PORTFOLIO / MAINTENANCE`.
- Competition: 纯爱战神黑客松, second place.
- Core story: behavior-derived tags support anonymous matching, followed by progressive identity unlock through interaction.

## Provenance and contribution

- The project came from a four-person random team and shared ideation.
- The user brought the real-tags and personal-data-interface direction, and owned most frontend/backend work, integration, deployment, demo video, and part of the pitch.
- Team, individual, AI, open-source, fixture, and research contributions must remain distinct; do not turn ideation or generated artifacts into implementation claims.

## Implementation boundary

- Runtime stack: Flask + Jinja2 SSR, SQLite via Python `sqlite3`, and native HTML/CSS/JavaScript.
- `run.py` is the verified development startup path; `tools/harness_cli.py` and `tests/` are the existing validation paths.
- The current repository includes implemented local/fixture flows. Third-party provider research, adapters, and Mock authorization do not prove live provider integrations.
- Production readiness is not established. No unverified feature expansion is allowed during maintenance cleanup.

## Cleanup baseline

- Cleanup starts from `cb6a2ab7229ec616eb4fb0f3bb05a3e42ec176af`, matching `origin/main` and `pre-cleanup-2026-08-31` after fetch.
- Cleanup branch: `cleanup/xxx-20260831`.
- Existing worktrees and local residual files are audit-only and must not be imported or modified.

## Cleanup verification

- A task-local `.venv` was created from the existing `requirements.txt`; it is ignored and not part of delivery.
- Python 3.13.13 / Flask 3.1.3 / Node v24.16.0 passed the existing Harness (`6/6`), all 28 Python tests, and all 4 Node motion tests.
- The `run.py` Flask entry point registered its routes successfully, and an isolated temporary-SQLite application-factory smoke returned HTTP 200 for `/` without credentials or external provider calls.
