# Repository Working Rules

## Scope and stack

- This repository is a Flask 3.1 application using Jinja2 server-rendered pages, Python `sqlite3`, HTML/CSS, and small native JavaScript enhancements.
- Keep the runnable structure under `app/`, with `run.py` as the development entry point and `tests/` plus `tools/harness_cli.py` as the verification surfaces.
- Repository cleanup must preserve behavior. Do not add product features, change architecture, deploy, rename the repository, or create a competition Release.

## Truth and privacy boundaries

- Describe only behavior supported by code and current tests. Label fixture, Mock, research, and local-only behavior explicitly.
- Do not claim GitHub, Steam, Duolingo, Keep, or any other provider is live without current authenticated evidence.
- Never read, copy, print, or commit credentials, tokens, cookies, private data, local connector probes, or agent logs.
- Preserve existing worktrees, branches, commits, and unexplained files; this cleanup worktree is the only writable checkout.

## Editing and verification

- Use `git mv` for tracked prototypes and documents, then repair all repository-relative links and script/test paths.
- Prefer the existing dependencies in `requirements.txt`; do not introduce new packages for cleanup.
- Before claiming completion, run all Python tests, the existing Node test, a credential-free startup smoke, link checks, `git diff --check`, secret filename/signature checks, and a check for added files at least 10 MB.
- Keep public history summaries concise and free of absolute paths, secret values, personal data, and raw agent logs.
