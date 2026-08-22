# Project Memory

## 2026-08-23: Hackathon takeover baseline

- Repository: `https://github.com/songconmaisaix31-design/xxx`.
- Protected source checkout: `C:\Users\DW\orca\xxx`; keep it read-only and do not update its `main` checkout.
- Fleet control worktree: `C:\Users\DW\orca\workspaces\xxx\fleet-control-hackathon-prize`.
- Baseline: `origin/main@648caa40ccd880f331b050bb27cfe80c361b0328`.
- The baseline already contains a substantial Flask/Jinja2/SQLite MVP. Improve verified gaps instead of rebuilding it.
- Product authority: `产品需求文档_PRD.md`.
- The sanitized API catalog supplied by the user is `C:\Users\DW\orca\xxx\API_INTERFACE_CATALOG.md`; import a copy into `docs/contracts/` without reading any credential files.
- Credential-free evidence supports public Duolingo profile, GitHub public REST, and LeetCode GraphQL transport. Keep, NetEase, and WeRead must remain fixture-only or unavailable unless separately verified with safe authorization.
- Use the installed Orca Directory Fleet Kit for isolated ownership, exact-SHA handoffs, integration, and audit evidence.
- Do not install repository hooks through shared `core.hooksPath`; run the Kit gates explicitly.
- User priority for the hackathon demo: use safe public interfaces first whenever they return useful behavior data; use mocks only as clearly labeled placeholders for unavailable integrations.
- The shortest truthful live set is Duolingo public profile plus GitHub public REST. LeetCode may be labeled live only after its site-specific profile mapping, not merely GraphQL transport, is verified.

## 2026-08-23: Frozen P0 implementation decisions

- Preserve the server-rendered Flask/Jinja2/SQLite architecture for the hackathon candidate; the reliable path is a focused vertical slice, not a framework rewrite.
- Public Live P0 sources are limited to bounded credential-free reads: Duolingo public profile, GitHub public REST user/repos/events, and the exact LeetCode.com public-profile GraphQL query. A public handle proves response provenance, not account ownership.
- Keep is a deterministic demo-only Fixture. Steam, NetEase Cloud Music, WeRead, GitHub GraphQL, and LeetCode.cn product mapping remain Unavailable until their prerequisites and mappings are safely verified.
- Public Live, Fixture, Unavailable, and Roadmap are mutually exclusive evidence classes. A Public Live failure preserves the last successful snapshot and must never silently load Fixture data.
- Normalized external tags are self-only and are the only datasource input to matching. Raw upstream bodies, credentials, repository names, profile identity fields, raw match scores, and weight details must not enter storage or L0 output.
- The offline judge path must remain resettable and credential-free. Demo accelerators and merchant benefits are Fixture behavior, never production, partner, payment, or deployment evidence.
- Final publication must use a new candidate branch with exact remote SHA verification. Local and remote `main`, plus the protected source checkout at `C:\Users\DW\orca\xxx`, must not be modified.

## 2026-08-23: Isolated public demo deployment

- Deployment branch: `deploy/realtags-davidwang-space`; do not merge or push it to `main` without an explicit future request.
- Public demo: `https://realtags.davidwang.space`, served by the new Vercel project `dwwww/realtags-prize-demo` (`prj_n3AqlfIYQICxn9nOSIsNbLVdp7Ov`).
- AliDNS record `2091285074485882880` is the only deployment DNS mutation: `realtags` CNAME to `9df316820fdcbb4c.vercel-dns-017.com`, TTL 600.
- Preserve the GitHub Pages apex A records, `www` CNAME, `/tags/` route, and the existing `tags` CNAME to `9ac6b2035aca735c.vercel-dns-017.com`. Never reuse or reconfigure the existing Vercel project `realtags-demo` for this deployment.
- Vercel requires `framework: flask`, the top-level `index.py` app, runtime assets under generated `public/static`, and a writable `DATABASE_PATH` such as `/tmp/realtags.sqlite3`.
- Vercel function-local SQLite is ephemeral and may reset between instances or deployments. This URL is hackathon Demo evidence only, not production durability or availability evidence.
- Deployment secrets live only in Vercel environment settings. Record variable names, never values; do not pull them into `.env` files.
- Rollback removes only AliDNS record `2091285074485882880` and detaches only `realtags.davidwang.space` from `realtags-prize-demo`.

## 2026-08-23: Isolated real-user test environment

- The real-user test worktree is `C:\Users\DW\orca\workspaces\xxx\realtags-real-user-test`; its branch must remain separate from `main` and the public demo branch.
- `run_real_user_test.py` forces `DEMO_MODE=0`, binds to `127.0.0.1:5001`, and uses the ignored persistent database `instance/real-user-test.sqlite3`.
- Startup rejects databases containing demo users, the demo administrator, Fixture tags/connections, or Fixture merchant events. Automated user-flow tests use temporary databases only.
- Registration persists all submitted profile fields, establishes the session, and redirects to `/profile/connections`; production copy does not invite Fixture loading.
- Real phone verification remains unavailable. Never set `phone_verified` automatically or claim event-host eligibility without a real verification provider and consent flow.
- The Vercel demo remains ephemeral and separate. A public persistent real-user environment requires an explicitly selected managed database and a verified migration before any deployment or DNS change.

## 2026-08-23: Persistent real-user deployment preparation

- The isolated Vercel project is `dwwww/realtags-real-user` (`prj_wdpE2Y4LPRVZAINBbURC33Rjj57s`). It is separate from `realtags-prize-demo` and `realtags-demo`.
- The target managed store is a dedicated Turso database in `iad1`, accessed through the pinned `turso-serverless==0.1.0` DB-API driver while local development continues to use `sqlite3`.
- Hosted startup requires paired `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN`, `DEMO_MODE=0`, `REAL_USER_ONLY=1`, a non-default `FLASK_SECRET_KEY`, and `SESSION_COOKIE_SECURE=1`. Record only these names, never their values.
- The Vercel project already has the four non-database runtime variables configured for Production and Preview. A generated local `.env.local` was removed without being read; never run `vercel env pull` in this worktree.
- Turso provisioning is pending the account owner's human acceptance of Vercel Marketplace and Turso legal terms. No database resource, deployment, custom domain, or DNS record has been created or changed yet.
- The intended custom hostname is `app.davidwang.space`, leaving `realtags.davidwang.space`, the GitHub Pages blog and `/tags/`, and `tags.davidwang.space` unchanged.
