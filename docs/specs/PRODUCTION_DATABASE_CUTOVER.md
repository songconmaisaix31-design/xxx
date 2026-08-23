# Production Database Cutover Specification

## Objective

Replace the current `realtags-real-user-db` Turso resource with a separately
provisioned primary database for the public real-user deployment. Preserve all
records that exist at cutover time, keep the previous database intact as a
rollback source, and never expose database credentials or user fields during
inspection, migration, or verification.

The Vercel project remains `dwwww/realtags-real-user`, the public origin remains
`https://app.davidwang.space`, and the application release remains based on
commit `27fa51f908a55a372792f7a757d424d276aa0614` unless this operation requires
a reviewed database-operations tool change.

## User impact and truth boundary

- Existing accounts, matches, conversations, messages, reports, blocks, tags,
  and external-source state must remain available after cutover.
- A database resource in `Available` state proves provisioning only. It does
  not prove schema initialization, data completeness, application connectivity,
  or durable production use.
- The public application must not write to both databases without an explicit
  dual-write contract. This operation uses one active primary at a time.
- The current deployment is still a hackathon real-user beta. A renamed or new
  database does not establish a production SLA, disaster-recovery program,
  retention policy, abuse controls, or compliance certification.

## Resource layout

| Role | Resource | Project connection | Retention |
| --- | --- | --- | --- |
| Source primary | `realtags-real-user-db` | Existing unprefixed production and preview variables | Keep disconnected after cutover for rollback |
| Candidate primary | `realtags-production-db-v2` | Connect first with the `NEXT_` prefix | Keep as the active primary after acceptance |

Connecting the candidate with a prefix must create only
`NEXT_TURSO_DATABASE_URL` and `NEXT_TURSO_AUTH_TOKEN`. The existing
`TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` remain unchanged until data checks
pass. Secret values stay inside Vercel encrypted environment injection; do not
pull them into a file, print them, or include them in logs.

## Data contract

The migration allowlist is the application-owned table set below. The schema in
`app/db.py` remains the canonical schema source.

1. `users`
2. `external_connections`
3. `tags`
4. `events`
5. `event_members`
6. `conversations`
7. `conversation_members`
8. `messages`
9. `event_coupons`
10. `admins`
11. `reports`
12. `event_reviews`
13. `admin_audit_logs`
14. `blocks`

Operational output is restricted to table names, row counts, schema hashes,
foreign-key violation counts, integrity booleans, deployment/resource IDs, and
HTTP status metadata. It must never contain row values, user identifiers,
emails, password hashes, message text, aliases, cookies, URLs containing
credentials, or authorization tokens.

## Cutover decision

### Empty source

If every allowlisted source table has zero rows immediately before cutover:

1. Initialize the candidate using the current idempotent application schema.
2. Verify zero prohibited Demo/Fixture rows, zero foreign-key violations, and
   matching schema/table inventory.
3. Recheck the source immediately before switching. Abort if any count changed.
4. Replace only the database integration connection, redeploy the exact
   candidate SHA, and run public read-only smoke checks.

No row-copy operation is necessary in this branch.

### Non-empty source

If any allowlisted source table contains rows, do not use a best-effort copy
while public writes remain enabled. Use one of these consistency mechanisms:

1. Prefer a provider-side Turso copy from the source database at a fixed point
   in time; or
2. deploy an explicit write-maintenance boundary, obtain one source snapshot,
   acquire a source write lock, copy the allowlisted tables in one conditional
   parameterized transaction, verify row counts and exact logical equality,
   switch the primary, and then remove maintenance mode.

The client-side batch must stop before writing when its unencoded value payload
exceeds 32 MiB. A larger database requires a provider-side copy instead of an
unbounded HTTP request.

The operation must abort before cutover if the source changes after the chosen
snapshot, the candidate is not empty, schemas are incompatible, any copied
count differs, integrity fails, contamination is present, or credentials are
missing or ambiguously paired.

## Rollback

- Never delete or mutate `realtags-real-user-db` during this operation.
- Record the source and candidate Vercel resource IDs before switching.
- If the candidate deployment fails startup, health checks, authentication, or
  aggregate verification, reconnect the source resource to production and
  preview, redeploy the last known-good source SHA, and confirm public health.
- Records written only after a successful cutover belong to the candidate. Do
  not roll back blindly after accepting new writes; first make an explicit data
  reconciliation decision.
- Database rollback does not require DNS changes. Do not change the `app`
  record or any apex, `www`, `tags`, or `realtags` record.

## Acceptance criteria

1. Source inspection reports only sanitized aggregate evidence and passes
   integrity, foreign-key, and contamination checks.
2. Candidate resource is separately named, `Available`, and initially connected
   with prefixed variables only.
3. Candidate schema matches the current application table contract.
4. Every allowlisted table has the same source and candidate row count at the
   accepted snapshot, or both databases are verified empty.
5. Candidate has zero prohibited Demo users, Demo administrator, Fixture tags,
   Fixture connections, and merchant-seed events.
6. Production environment exposes exactly one unprefixed Turso URL/token pair
   after cutover; `DATABASE_PATH` remains absent.
7. The new production deployment reaches `READY`; `/`, `/register`, and a
   representative static asset return `200`; anonymous `/profile` redirects;
   `POST /demo/login` returns `404`.
8. The previous database remains `Available` but disconnected, with its exact
   resource ID recorded for rollback.
9. The branch is clean, pushed, and its remote SHA equals the deployed source
   SHA. Project `MEMORY.md` records only durable, non-secret resource facts and
   the verification boundary.

## Verification commands

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_production_database -v
vercel env run -e production --project realtags-real-user -- .\.venv\Scripts\python.exe tools/production_database.py inspect-source
vercel env run -e production --project realtags-real-user -- .\.venv\Scripts\python.exe tools/production_database.py check-readiness
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q app tests tools
.\harness.cmd
git diff --check
```

Live commands must use bounded timeouts where supported. A failed or ambiguous
check is a stop condition, not permission to delete, reconnect, or overwrite a
resource.
