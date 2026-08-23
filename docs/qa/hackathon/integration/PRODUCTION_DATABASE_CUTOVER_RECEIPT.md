# Production Database Cutover Receipt

Status: **BLOCKED — EXTERNAL STATE CONFLICT**  
Observed: 2026-08-23 (Asia/Shanghai)  
Project: `dwwww/realtags-real-user`  
Implementation branch: `songconmaisaix31-design/realtags-production-db-v2`

## Outcome

The production database cutover was not completed. The existing production database remains the authoritative store. A third candidate database was not created because two independently provisioned candidates were removed while the cutover tool was performing read-only verification.

## Current Safe State

- `https://app.davidwang.space` resolves to Ready production deployment `dpl_9THtmEWsaDHgB6zZkuFmXnkeXnxq` and returns HTTP `200` without the maintenance marker.
- Existing Turso resource `realtags-real-user-db` is `Available` and connected to `realtags-real-user` for production and preview.
- A fresh source inspection completed successfully with SQLite integrity `ok`, zero foreign-key violations, zero Fixture contamination, and no missing application tables.
- The latest sanitized source counts were: 15 users, 8 conversations, 16 conversation members, 45 messages, 10 external connections, and 31 tags. All other application tables contained zero rows.
- Candidate resource `realtags-production-db-v2` does not currently exist.

These checks support current source availability and consistency. They do not prove that no concurrent write occurred after the inspection.

## Attempt Evidence

### Attempt 1

- Candidate Vercel resource: `store_WG5pzzjAltSRlDbJ`
- Candidate provider resource: `01a02d6c-3201-7758-b43d-e835c3e62131`
- Maintenance deployment: `dpl_G657wyA79Sv4VRXLRZKx6Urc4eNz`
- The candidate was initialized and received one bounded transactional copy.
- Source and target aggregate counts matched at 15 users, 8 conversations, 16 conversation members, 43 messages, 10 external connections, and 31 tags.
- Integrity, foreign-key, contamination, and schema checks passed. Final logical equality was not reported because the source Hrana stream expired during cleanup.
- Vercel later restored the previous production deployment, removed the candidate connection and related environment names, and deleted the candidate resource.

### Attempt 2

- Candidate Vercel resource: `store_QssmVLDvu70J8erD`
- Candidate provider resource: `01a02d78-d401-7dca-a4d5-9530847bde4e`
- Maintenance deployment: `dpl_D2hrArn51ymMqTqAAvXVvowEqe8a`
- Public maintenance behavior was verified: safe methods returned HTTP `200` with a static maintenance page; mutating methods returned HTTP `503`.
- Source readiness at the write freeze reported 15 users, 8 conversations, 16 conversation members, 45 messages, 10 external connections, and 31 tags.
- The candidate received the transactional copy and all target tables were read during verification. Final logical equality was not reported because the source and target Hrana streams expired at different points in the long comparison.
- Before verification could be rerun with symmetrical keepalive, Vercel restored the previous production deployment, removed the candidate connection and related environment names, and deleted the candidate resource.

No local Vercel, rollback, or cutover process was running when the second restoration was observed.

## Local Hardening

The cutover tool now:

- emits table-specific snapshot failures without exposing row values;
- keeps both Hrana connections alive while the opposite database is read;
- verifies that the source write-lock transaction remains active;
- prevents an expired cleanup rollback from masking an already verified result; and
- emits an explicit logical-comparison progress stage.

The tool continues to use bound parameters, bounded payloads, a source `BEGIN IMMEDIATE` snapshot, a single conditional target transaction, exact logical tuple comparison, and sanitized aggregate output.

## Verification Boundary

- The full Python suite passed all 127 tests after the final connection-keepalive hardening.
- The current production-database and deployment focused suites passed all 22 tests after the hardening.
- Node tests passed 11 tests and the isolated harness passed all 6 stages before the final Python-only hardening.
- Python compilation and `git diff --check` passed after the hardening.
- Neither attempt produced a persistent verified candidate, so no production cutover claim is supported.

## Unblock Condition

Before another attempt, pause any Vercel account-side automation, rollback workflow, parallel deployment, or operator action that restores the deployment alias, removes integration connections or environment names, or deletes newly provisioned resources. After that pause is confirmed, recreate one candidate database and rerun the full freeze, copy, exact verification, connection swap, deployment, smoke, and rollback-readiness sequence.

No credential value is required from the user for this handoff.
