# Local residual audit (2026-09-01)

This is a public-safe, read-only classification of repository worktrees and refs observed before cleanup. No existing checkout, connector probe, credential file, agent log, or local-only commit was changed or imported.

## Start contract

- `origin/main`: `cb6a2ab7229ec616eb4fb0f3bb05a3e42ec176af`
- `pre-cleanup-2026-08-31`: `cb6a2ab7229ec616eb4fb0f3bb05a3e42ec176af`
- Cleanup branch began at the same SHA.

## Existing worktrees

Twenty pre-existing worktrees were inspected read-only. All had zero tracked-file modifications.

| Lane | HEAD | Classification |
| --- | --- | --- |
| Original main checkout | `42cdcbf4` | Stale clean tracked tree; 27 untracked API probe/adapter/report files retained locally |
| Prize/fleet lane | `3a17590b` | Clean and remote-backed; `.agents` metadata retained |
| GitHub lane | `42cdcbf4` | Clean historical pointer; HEAD reachable from remote refs |
| Governance/data base | `01363335` | Clean and remote-backed |
| Main fork | `42cdcbf4` | Clean historical pointer; HEAD reachable from remote refs |
| Old Fleet Kit evidence lane | `42cdcbf4` | Clean tracked tree; 31 untracked Fleet Kit/evidence files retained locally |
| AI permission lane | `2f1aea79` | Clean and remote-backed |
| AI runtime verification lane | `ac3e6d01` | Clean; HEAD reachable from remote refs |
| AI runtime verification v2 | `cdefff81` | Clean tracked tree; contains three local-only commits |
| AI standby lane | `5eb9d913` | Clean; HEAD reachable from remote refs |
| AI reliability lane | `0f4334f4` | Clean and remote-backed |
| Deployment lane | `4ed6a420` | Clean and remote-backed |
| Real-user test lane | `4dc6a176` | Clean; HEAD reachable from remote refs |
| Architecture lane | `eddb9dd3` | Clean and remote-backed |
| Core matching lane | `06012b59` | Clean and remote-backed |
| Data-source lane | `324b847d` | Clean and remote-backed |
| Experience lane 1 | `4c298caa` | Clean and remote-backed |
| Experience lane 2 | `ac9c0d60` | Clean and remote-backed |
| Integration lane | `a6535493` | Clean and remote-backed |
| QA lane | `6f4ba724` | Clean; HEAD reachable from remote refs |

## Local-only commits

Exactly three commits were not reachable from any fetched remote ref. They form the old AI runtime verification v2 chain and were not cherry-picked or otherwise imported:

- `6d1bc332e02bfad0c39a2e266a48cd8829db9d0f`
- `6f15e8a89e6e393c26cbfc7ece9f459a0938f156`
- `cdefff815e50a1ee95de9f84ac300711cd7d2407`

## Residual classification

- Original checkout: 27 untracked files covering API contracts, adapters, probe scripts, sanitized reports, tests, and example credential schema. These belong to a separate local interface-audit effort; none are part of this cleanup snapshot.
- Old Fleet Kit evidence lane: 31 untracked files covering `.agents` plans/prompts/run evidence plus Fleet Kit scripts, tests, hooks, and documentation. Raw agent evidence was not read into this public record.
- Other pre-existing worktrees: no tracked changes and no untracked residuals observed.
- Local `main` in the original checkout remained behind fetched `origin/main`; it was not updated because existing worktrees are out of scope.

These residuals require an owner decision in their original worktrees. Cleanup, deletion, archival, or publication was not authorized here.
