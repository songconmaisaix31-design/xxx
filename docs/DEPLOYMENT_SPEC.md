# Hackathon Deployment Specification

Status: Implemented and verified on 2026-08-23
Target branch: `competition/prd-hackathon`
Target project: `realtags-demo`
Target domain: `tags.davidwang.space`

## Goal

Publish the complete Flask Demo on an isolated subdomain without changing the existing `davidwang.space` or `www.davidwang.space` GitHub Pages blog.

## Architecture decision

Vercel is the shortest deployable path because the repository already exposes a Flask WSGI application and the authenticated Vercel account is available. GitHub Pages is rejected because it cannot execute the Flask backend. No authorized VPS deployment target is currently established.

The Vercel deployment is a hackathon Demo, not a persistent production backend:

- Flask runs as one Vercel Function.
- The SQLite database lives under `/tmp/realtags` because the function bundle is read-only.
- `/tmp` is ephemeral and is not shared reliably across function instances. Demo mutations can reset after a cold start or appear inconsistent across concurrent instances.
- A stable sensitive `FLASK_SECRET_KEY` is configured in Vercel so sessions do not reset merely because the process restarts.
- `DEMO_MODE=1` remains explicit. Keep, venue, SMS, merchant and POS capabilities remain Fixture-only.

A persistent real-user release requires a managed database and the Production P0 gates in `docs/PRODUCTION_GAPS_AND_ROADMAP.md`.

## DNS boundary

Before deployment, the authoritative DNS records are:

- Apex: four GitHub Pages A records.
- `www`: CNAME to `songconmaisaix31-design.github.io`.
- `tags`: absent.

Deployment may add only:

- `tags` CNAME required by Vercel.
- A Vercel ownership TXT record if the platform explicitly requires it.

It must not update, delete, disable or replace the apex or `www` records.

## Implementation

- Export the WSGI app from root `index.py`, a Vercel-recognized Flask entry point.
- Let `create_app` accept an explicit instance directory so Vercel can use writable `/tmp` while local and test behavior remains unchanged.
- Enable secure, HTTP-only, SameSite cookies on Vercel HTTPS deployments.
- Exclude local environments, tests and visual QA artifacts from the deployment upload.
- Keep secrets only in Vercel environment settings; never commit or print them.

## Acceptance criteria

1. Local deployment-entrypoint test passes with an isolated temporary instance directory.
2. Full Python, Node, compile and Harness gates pass.
3. Preview and production Vercel deployments build successfully.
4. Root HTML, production CSS/image assets, Demo login, profile, matching and event pages return successfully over HTTPS.
5. `https://tags.davidwang.space` serves the production deployment with a valid certificate.
6. `https://davidwang.space` and `https://www.davidwang.space` still return the pre-deployment blog title and content fingerprint.
7. The deployed UI and handoff state that hosted SQLite state is ephemeral.

## Rollback

1. Remove `tags.davidwang.space` from the Vercel project.
2. Delete only the AliDNS `tags` CNAME created by this deployment.
3. Leave all apex and `www` records untouched.
4. Keep the Vercel project deployment URL available only if a fallback Demo URL is still useful.
