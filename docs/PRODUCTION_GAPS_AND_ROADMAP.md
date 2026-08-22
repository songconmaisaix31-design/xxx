# Production Gaps and Roadmap

_Updated for `competition/prd-hackathon` on 2026-08-23_

This document separates a judge-ready hackathon loop from production readiness. A page, database field, Fixture flow, or passing unit test is not evidence that an external provider, safety operation, or public deployment is ready.

## Release decision

| Environment | Decision | Allowed data | Required controls |
| --- | --- | --- | --- |
| Local development | GO | Fixture and disposable test data | Default Demo configuration |
| Automated verification | GO | Temporary SQLite data | Locked Python environment |
| Product or judge demo | GO | Fixture data; optional public Duolingo username | Explicit Live/Fixture labels |
| Controlled internal review | GO | Non-sensitive test data | Trusted network and named operator |
| Real-user pilot | NO-GO | None yet | Close all Production P0 items below |
| Public beta or production | NO-GO | None yet | P0 closure, security/privacy review, recovery evidence |

## Truth model

| Mode | Meaning | Current examples |
| --- | --- | --- |
| `Live` | A point-in-time request reached an external service and returned a valid response | Duolingo public profile only |
| `Fixture` | Deterministic data demonstrates the product workflow | Keep, venue, SMS verification, merchant, coupon POS |
| `Derived` | A transparent projection of normalized inputs | Discipline, active time, goal consistency |
| `Self` | Data entered by the user | Profile and matching preferences |

Live evidence is not an SLA, partnership, OAuth grant, or production approval. Fixture evidence proves interaction and state transitions only.

## Closed engineering gaps on this branch

| Area | Current control | Evidence |
| --- | --- | --- |
| Session secret | Non-Demo startup fails without an explicit `FLASK_SECRET_KEY`; Demo uses a process-random key | configuration tests |
| CSRF | Every POST is protected by a session-bound token | form and rejection tests |
| External data minimization | No third-party token or raw response persistence; fixed HTTPS endpoint, input whitelist, timeout and response cap | adapter tests |
| Source truth | Live, Fixture, Derived and Self are stored and rendered separately; Derived remains unverified | adapter and profile tests |
| Tag privacy | `self_only` behavior tags are never returned to a counterpart at L0–L4 | relationship privacy test |
| Matching | Bidirectional age/gender filters precede deterministic similarity and ranking | matching tests |
| Relationship progression | Both people must speak; progression uses mutual active days; point unlock needs a two-person collaboration task | chat tests |
| Event safety logic | Phone gate, same-gender enforcement, capacity/time/store checks, table-scoped coupon and seven-day archive | event tests |
| Reproducibility | Python 3.12, `uv.lock`, CI workflow, full local Harness | lock, CI and Harness files |

These controls reduce Demo risk. They do not replace identity verification, provider contracts, operational monitoring, or an independent security assessment.

## Production P0 blockers

### P0-A: Identity, consent and account lifecycle

Current Demo phone verification is a clearly labelled Fixture. Email ownership, password recovery, device/session management, account export/deletion, consent history and retention enforcement are not implemented.

Why it matters: users cannot prove account ownership or exercise basic privacy rights, and operators cannot safely recover or remove an account.

Exit criteria:

- Approved email and SMS providers with rate limits, expiry, replay protection and delivery monitoring.
- Password reset, session revocation and suspicious-login handling.
- Versioned terms/privacy consent with auditable timestamps.
- Data export, deletion, retention and legal-hold flows tested end to end.
- Age policy and the required level of age/identity assurance agreed for each launch region.

### P0-B: Trust, abuse and offline safety operations

Reports, blocks and review records exist, but automated sanctions, appeals, emergency escalation, verified venues and incident operations do not.

Why it matters: a social product that can lead to an offline meeting needs enforceable safety operations, not only database records.

Exit criteria:

- Moderation policy, severity model, suspension/removal actions and appeal workflow.
- Rate limits and abuse controls for registration, login, messaging, reports and event creation.
- Venue/organizer verification and a clear emergency/contact process.
- Staff permissions, response targets and immutable decision audit evidence.
- Safety review covering minors, harassment, stalking, fraud and location abuse.

### P0-C: Authentication and administrator hardening

Passwords are hashed and Demo administrators are disabled outside Demo mode, but MFA, role separation, login throttling and privileged-session controls are absent.

Why it matters: one compromised administrator currently has broad moderation access.

Exit criteria:

- MFA for administrators and risk-based controls for users.
- Least-privilege roles, privileged action confirmation and session expiry.
- Login throttling, credential-stuffing detection and security event logging.
- Security headers, strict Cookie policy, CSP and trusted-proxy configuration.

### P0-D: Approved external integrations

Duolingo uses a public profile endpoint without credentials. Keep, maps/POI, SMS, merchant and POS are Fixture-only. No provider has supplied an uptime commitment or production authorization to this project.

Why it matters: an undocumented or public endpoint can change without notice, while a Fixture cannot establish the core “verified behavior” claim.

Exit criteria:

- Provider terms and data-processing purpose reviewed and approved.
- Supported API/auth flow with minimal scopes, revocation and failure handling.
- Credentials stored in a managed secret system; no secrets or raw provider payloads in logs or application tables.
- Sandbox tests for rejection, expiry, rate limit, schema drift and provider outage.
- User-facing provenance, last-sync time, disconnect and deletion controls.

### P0-E: Production platform and observability

The repository has a development server and CI checks, but no production WSGI/container configuration, TLS edge, health probes, centralized logs, metrics, alerts or incident runbooks.

Why it matters: a passing local flow cannot prove availability, detect abuse, or support recovery during an incident.

Exit criteria:

- Reproducible build artifact and hardened WSGI deployment behind HTTPS.
- Separate environments, managed secret injection and least-privilege service identity.
- Health/readiness checks, structured redacted logs, metrics, tracing and actionable alerts.
- Deployment rollback, incident response and on-call ownership exercised in a staging drill.
- Dependency, SAST and container/image scanning added to release gates.

### P0-F: Durable data, migrations and recovery

SQLite and additive startup migrations are appropriate for the Demo. They are not a multi-instance migration, concurrency, backup or disaster-recovery strategy.

Why it matters: concurrent writers, failed schema changes or host loss can corrupt or permanently lose user and moderation data.

Exit criteria:

- Managed production database with versioned forward/backward migration procedures.
- Transaction and concurrency tests for matching, signup approval, coupons and schedulers.
- Encrypted backups with defined RPO/RTO and a successful isolated restore drill.
- Idempotent scheduled jobs with locking, retries, dead-letter handling and monitoring.

### P0-G: Privacy, location and contact exchange

Precise coordinates are not persisted, but the nearby flow currently places them in a GET query where browser history, proxies or access logs may retain them. L4 signals that contact exchange is available but has no two-party consent workflow.

Why it matters: location and contact details can create direct physical safety risks.

Exit criteria:

- Move precise coordinates out of URLs and define coarse-location retention/logging rules.
- Explicit two-party consent, expiry, revocation and audit for contact exchange.
- Privacy threat model covering matching inference, screenshots, blocking and re-identification.
- Independent privacy and security review before processing real personal data.

## Product and scale backlog

| Priority | Capability | Current boundary |
| --- | --- | --- |
| P1 | Real-time chat, delivery state, pagination and notifications | SSR refresh only |
| P1 | Real maps, route guidance and dynamic venue inventory | Three Fixture POIs |
| P1 | Merchant onboarding, payment, POS and settlement | Fixture coupon workflow |
| P1 | Production scheduler and asynchronous jobs | Manual/CLI scheduling |
| P1 | Browser, device, accessibility and network-condition matrix | Desktop runtime QA plus static responsive tests |
| P1 | Data lifecycle UI and provider disconnect | Service-level primitives only |
| P2 | Reputation, attendance, post-event review and appeals | Not implemented |
| P2 | Experimentation and privacy-preserving product analytics | No official metrics |
| P2 | Localization, time zones and regional policy variants | Chinese-first, limited time assumptions |

## Delivery sequence

1. **Hackathon candidate — current:** stable Fixture-first story, optional Duolingo Live request, deterministic reset, claims ledger and local evidence.
2. **Controlled alpha:** complete Production P0 architecture in staging, use only team accounts and approved sandbox providers, run browser/accessibility and recovery drills.
3. **Real-user pilot:** require security/privacy/safety approvals, provider production access, monitored deployment and explicit pilot limits.
4. **Public beta:** close critical P1 reliability gaps, publish support and incident processes, and collect only metrics that have a defined privacy purpose.

No phase advances because a screenshot looks complete. Advancement requires the listed runtime, operational and review evidence.

## Evidence authority

- Product requirements: `产品需求文档_PRD.md`
- Current implementation acceptance: `docs/PRD_ACCEPTANCE_MATRIX.md`
- External data contract: `docs/API_CONTRACT.md`
- Allowed and disallowed claims: `docs/CLAIMS_LEDGER.md`
- Repeatable local verification: `docs/HARNESS_CLI.md`
