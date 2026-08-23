# Match Gender Selection Contract

Status: implemented

Date: 2026-08-23

## Product objective

Shorten account creation by moving the desired match gender from registration
to the point where the user starts a match. The saved preference must remain a
server-owned hard filter and must be applied before a human candidate or AI
standby path is selected.

## Interaction contract

- Registration does not render or require `match_gender`.
- New accounts receive the safe, non-excluding default `any`.
- `GET /matches` renders `male`, `female`, and `any`, with the user's current
  saved value selected.
- `POST /matches/search/start` accepts an optional `match_gender`. A supplied
  value is validated and persisted before the candidate pool is ranked.
- An omitted value preserves the saved preference for compatibility with old
  clients and existing automated flows.
- An invalid value changes neither the preference nor the active match flow.

## Acceptance criteria

1. The registration page contains no desired-match-gender control.
2. Registration without `match_gender` succeeds and stores `any`.
3. The match page exposes all three values and selects the saved value.
4. Starting a match with a new valid value persists it before ranking.
5. Invalid input returns to the match page with a validation error.
6. The registration draft allowlist no longer contains `match_gender`.
7. Existing match start requests without the field retain their current
   behavior.
8. Python, Node, harness, syntax, diff, desktop, and 390x844 mobile checks pass.

## Risks and controls

- **Stale candidate count:** the ready page always presents one neutral start
  form; the server recomputes the pool only after the submitted preference is
  saved.
- **Forged values:** validate against the centralized `MATCH_GENDERS` contract
  before updating the database.
- **Existing accounts:** retain their saved value and preselect it on every
  visit instead of resetting it.
- **Interrupted match flow:** if a changed preference makes the existing
  candidate ineligible, the normal server-owned flow selects a new candidate.

## Verification commands

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_core tests.test_real_user_environment -v
node --test tests\registration_draft.test.mjs tests\match_flow.test.mjs
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.\.venv\Scripts\python.exe -m compileall -q app tests tools run_real_user_test.py
.\harness.cmd
git diff --check
```

## Verification evidence

- 114 Python tests passed.
- 11 Node tests passed.
- The isolated delivery harness passed all 6 gates.
- Desktop and 390x844 browser checks confirmed the control, saved round trip,
  registration removal, and zero horizontal overflow.
