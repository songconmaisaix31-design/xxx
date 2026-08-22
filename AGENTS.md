# RealTags Hackathon Project Rules

## Mission

- Deliver the PRD as a credible, judge-ready hackathon product.
- Work only on isolated branches/worktrees based on `origin/main`.
- Never update, commit to, merge into, or push `main`.
- Keep the source checkout at `C:\Users\DW\orca\xxx` read-only.

## Product Truth

- The product is a Chinese anonymous social-matching experience built on verified behavioral tags.
- Treat `产品需求文档_PRD.md` as the product authority.
- Treat `docs/contracts/API_INTERFACE_CATALOG.md` as the available API evidence once imported.
- Separate live integrations, fixtures, prototypes, and roadmap claims in UI and submission materials.
- Never claim an authenticated integration, deployment, metric, or end-to-end result without current evidence.

## Stack and Layout

- Python 3 / Flask / Jinja2 / SQLite.
- Browser JavaScript and CSS are dependency-free unless the repository already declares otherwise.
- Application code: `app/`.
- Automated checks: `tests/`, `tools/`, and `harness.cmd`.
- Product and engineering docs: `docs/`.
- Fleet control files: `.agents/`, `scripts/`, and `orca.yaml`.

## Workflow

- Use Specify -> Plan -> Task -> Execute -> Verify for multi-file or product changes.
- Before implementation, keep acceptance criteria, constraints, risks, and verification commands in `docs/specs/` or an equivalent project document.
- Use the Orca Directory Fleet Kit for coordinated work. Each worker must use a new top-level worktree and an exclusive directory/file allowlist.
- A worker must not edit files outside its assigned ownership. Cross-track needs go into its handoff.
- Integration accepts only exact pushed worker SHAs and uses non-fast-forward merges. No rebases, force pushes, branch switching, `git reset --hard`, or `git clean`.
- Preserve existing user changes and avoid unrelated refactors.

## Implementation Standards

- Prefer the smallest maintainable implementation and reuse existing helpers and patterns.
- Prefer functions and declarative data over classes unless the existing abstraction requires a class.
- Keep endpoint and adapter contracts in one explicit source of truth.
- Validate all untrusted input at the boundary and use bounded network timeouts.
- Do not add speculative features or dependencies.
- Code, comments, filenames, commit messages, README content, and technical documentation are English. Chinese UI copy is expected for this Chinese product.

## Security

- Never read, print, copy, commit, or expose `.env` files, credentials, tokens, private keys, cookies, or authorization headers.
- Never hard-code secrets or store secret values in documentation or memory.
- Start API work with non-mutating, credential-free requests. Do not perform create, update, delete, payment, messaging, or other side-effecting probes.
- Redact sensitive request and response data. Do not disable TLS verification.
- Use explicit timeouts and no automatic retries for non-idempotent operations.
- Restrict event locations to the repository's restaurant POI allowlist.

## UI Delivery

- Use the checked-in brand specification, existing screenshots, and current UI as the visual source of truth.
- Build and verify representative desktop and 390x844 mobile states.
- Check text overflow, overlap, spacing, focus states, reduced motion, and the primary judge demo flow.
- Do not use preview images as implementation evidence.

## Verification

- Define completion before modifying implementation files.
- Run the focused tests for every change, then the full unit suite and HTTP workflow harness before integration.
- Run Python syntax checks and `git diff --check`.
- For UI changes, capture current screenshots or record the strongest available visual verification.
- The final candidate must have a clean worktree, a pushed branch, a verified remote SHA, and truthful evidence of every claimed gate.

## Memory

- Record durable architecture decisions, user corrections, recurring pitfalls, and non-secret operational notes in `MEMORY.md`.
- Do not duplicate facts that are obvious from source code.
- State in the final report whether `MEMORY.md` was updated.
