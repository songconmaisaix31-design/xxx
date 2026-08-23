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

## 2026-08-23: Persistent real-user deployment

- The live branch is `songconmaisaix31-design/realtags-real-user-test`; deployed application commit `3961b91707ac7398380b6f0f61d3a484cacdeaf4` runs at `https://app.davidwang.space`.
- The isolated Vercel project is `dwwww/realtags-real-user` (`prj_wdpE2Y4LPRVZAINBbURC33Rjj57s`); production deployment `dpl_Jk89xsmbSz5T29VRDnvQcgKAeRCL` is Ready in `iad1` and is separate from both demo projects.
- The final persistent store is Turso `realtags-real-user-db`, Vercel resource `store_tywM9V3uulfX6MPt`, provider resource `01a02be8-5d01-739d-9717-aac2c46bfdc6`. It was created fresh after QA and received no QA registration or Fixture load.
- Online persistence QA passed registration, automatic login, Duolingo/GitHub/LeetCode.com Public Live sync, anonymous match, two-way chat, report, block, event verification boundary, and fresh-session reads after a second deployment. Disposable QA resource `store_ZQU6a6kbEbDIQhBL` was permanently deleted afterward.
- Keep remains unavailable in real-user mode and its sync route returns `404`. A public handle proves response provenance, not external-account ownership. Phone verification remains unavailable, so event hosting stays blocked.
- Hosted configuration uses only the encrypted Vercel variables `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`, `FLASK_SECRET_KEY`, `SESSION_COOKIE_SECURE`, `REAL_USER_ONLY`, and `DEMO_MODE`; never pull or record their values.
- AliDNS record `2091310372422056960` is the only DNS addition: `app` CNAME to `cname.vercel-dns.com`, TTL 600. It is reachable with valid HTTPS; Vercel's project-specific recommendation remains a regional-routing follow-up.
- Final smoke returned `200` for the landing page, registration, and representative assets; anonymous profile redirected to login and demo login returned `404`. The blog, blog `/tags/`, `tags.davidwang.space`, and `realtags.davidwang.space` all retained HTTP `200`.
- Registration drafts use same-tab `sessionStorage` with an explicit profile-field allowlist. Passwords are never stored, successful authentication clears the draft, clean Chrome verified refresh restoration, and automated lifecycle tests cover history Back/BFCache restoration.
- Rollback detaches only `app.davidwang.space` and deletes only AliDNS record `2091310372422056960`; retain the final database until an explicit real-user data-retention decision.

## 2026-08-23: Truthful AI standby fallback

- Implementation worktree: `C:\Users\DW\orca\workspaces\xxx\realtags-ai-standby-fallback`; candidate branch: `songconmaisaix31-design/realtags-ai-standby-fallback`.
- Human candidates always take precedence. Only an empty eligible human pool may create or reuse a single-member AI standby conversation, which is persistently labeled as AI and not a real person.
- AI conversations never create synthetic user records and expose no match score, profile reveal, contact exchange, human unlock tools, or block-person action. Forged human-only actions are rejected server-side.
- The provider receives only the fixed system instruction and at most the latest 12 bounded text turns. Profile fields, aliases, tags, source data, match weights, and credentials stay outside the request.
- Runtime activation uses only `AI_FALLBACK_ENABLED`, `AI_FALLBACK_API_KEY`, `AI_FALLBACK_BASE_URL`, and `AI_FALLBACK_MODEL`. The feature defaults to disabled, and existing AI history becomes read-only when configuration is missing or invalid.
- Provider transport is an HTTPS-only OpenAI-compatible Chat Completions boundary with an 8-second timeout, no redirects or retries, a 64 KiB response limit, a 500-character stored reply limit, and a 30-reply conversation cap.
- The credential posted in chat was treated as exposed and was not used or stored. Activation remains blocked until the user rotates it and supplies the official provider base URL and exact model identifier through encrypted Vercel configuration.
- Verification passed 105 Python tests, 8 Node tests, the 6-stage Harness pipeline, syntax and diff checks, plus 1440px desktop and true 390x844 mobile browser QA with no horizontal overflow.
- Dormant fallback code commit `fe8b8b99836fdc3eb8439f7dee92573d78ee1645` was deployed to the existing `dwwww/realtags-real-user` project as production deployment `dpl_CqJ2GisoiUauqZSsDYPM3V4fk4kj`, aliased to `https://app.davidwang.space` in Ready state. No AI environment variables were added, so public behavior remains disabled until verified activation.
- Post-deployment smoke returned `200` for the app landing and registration pages, preserved the login redirect on `/matches`, and retained `200` responses for the blog, blog `/tags/`, `tags.davidwang.space`, and `realtags.davidwang.space`. No DNS record was changed.
