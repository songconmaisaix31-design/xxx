# Hosted Deployment Evidence

Status: Verified
Observed at: 2026-08-23 (Asia/Shanghai)

## Release identity

| Item | Value |
| --- | --- |
| Branch | `competition/prd-hackathon` |
| Runtime code commit | `48cc41604d417ddd9fd38728db432629bb1b10a8` |
| Vercel project | `dwwww/realtags-demo` |
| Production deployment | `dpl_CpwW2mRyf9b11RvF2Bvcd9fUdS9W` |
| Deployment URL | `https://realtags-demo-qou6t2ld7-dwwww.vercel.app` |
| Custom domain | `https://tags.davidwang.space` |

The build used Python 3.12, installed the locked dependencies with uv, and produced one Flask Function. The Vercel project uses the `flask` Framework Preset and the repository pins `index:app` as its WSGI entry point.

## DNS change

Only one AliDNS record was created:

| RR | Type | Value | TTL | Record ID |
| --- | --- | --- | --- | --- |
| `tags` | `CNAME` | `9ac6b2035aca735c.vercel-dns-017.com` | 600 | `2091261038183694336` |

Vercel reported the domain as `configured-correctly` and verified it for `realtags-demo`. The existing blog records were not edited:

- `www` remains a CNAME to `songconmaisaix31-design.github.io`.
- The apex remains on the four GitHub Pages addresses from `185.199.108.153` through `185.199.111.153`.

## Hosted runtime checks

The following checks were executed against the custom domain over HTTPS:

| Check | Result |
| --- | --- |
| Root HTML and hosted-state warning | `200` |
| CSRF-protected Demo login and redirect to `/profile` | `200` |
| `/profile` with “我的真实标签” | `200` |
| `/matches` | `200` |
| `/conversations` | `200` |
| `/events` | `200` |
| `/static/css/prd-contract.css` | `200`, `text/css` |
| `/static/img/brand-mark.png` | `200`, `image/png` |

The root and authenticated pages displayed the hosted Demo warning. No CSRF value, session cookie or environment-variable value was printed or recorded.

## Blog isolation proof

Before and after the DNS change, both `https://davidwang.space` and `https://www.davidwang.space` resolved to the existing blog. The post-change check returned:

| Requested URL | Final URL | Status | Title | Bytes | SHA-256 |
| --- | --- | --- | --- | --- | --- |
| `https://davidwang.space` | `https://davidwang.space/` | `200` | `David Wang` | 14,418 | `73EA2CF800B058F81997A2ED0185836102AFC21E8878BA86F9F2CB710B661904` |
| `https://www.davidwang.space` | `https://davidwang.space/` | `200` | `David Wang` | 14,418 | `73EA2CF800B058F81997A2ED0185836102AFC21E8878BA86F9F2CB710B661904` |

The fingerprint matches the pre-deployment baseline.

## Truth boundary

This is a hosted hackathon Demo, not a production persistence claim. SQLite writes use `/tmp/realtags`; state can reset on a cold start and is not guaranteed to be shared across concurrent instances. Keep, venue, SMS, merchant and POS flows remain explicitly marked Fixture or Demo capabilities. A production release still requires a managed database and the operational gates in `PRODUCTION_GAPS_AND_ROADMAP.md`.

## Rollback

1. Remove `tags.davidwang.space` from `dwwww/realtags-demo`.
2. Delete only AliDNS Record ID `2091261038183694336`.
3. Do not change the apex or `www` records.
