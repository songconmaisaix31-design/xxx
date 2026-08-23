# Avatar Matching Demo Contract

Status: implementation-ready

Date: 2026-08-23

## Product objective

Add one truthful, demo-ready photo signal without pretending that a placeholder
face check proves identity. A profile with a photo can require photo-bearing
candidates or accept profiles without a photo only as fallback candidates.

## Data contract

The `users` record owns three additive fields:

| Field | Values | Meaning |
| --- | --- | --- |
| `avatar_data_url` | nullable bounded image data URL | User-supplied JPEG, PNG, or WebP avatar. |
| `avatar_face_check` | `not_submitted`, `mock_placeholder` | `mock_placeholder` is not identity verification. |
| `photo_match_preference` | `photo_or_standby`, `photo_only` | Whether a user with a photo accepts no-photo standby candidates. |

For the hackathon demo, avatar bytes are stored in the existing database so a
serverless deployment does not lose files. Before sustained production traffic,
move this field to private object storage and retain only an opaque object key.

## Upload boundary

- Registration accepts `multipart/form-data`.
- The server ignores the client filename and detects JPEG, PNG, or WebP from
  magic bytes.
- The decoded file body is limited to 400 KiB. SVG and all other formats are
  rejected.
- Passwords and file inputs are never stored in browser draft storage.
- The UI must label face recognition as `Mock placeholder / not verified`.

## Matching semantics

1. Gender and age hard filters still apply in both directions.
2. `photo_only` applies in both directions and is valid only for a user who
   uploaded a photo.
3. Candidates with photos form the primary pool.
4. Candidates without photos are returned only when the primary pool is empty,
   are labeled standby, and receive a 15% raw-score reduction before display
   smoothing.
5. The result page may expose only the selected avatar, its truthful placeholder
   face-check state, display score, hidden-common-point count, and opaque attempt
   reference. Email and other profile fields remain sealed.

## Acceptance criteria

- Valid JPEG, PNG, and WebP uploads persist across requests.
- Oversized, empty, and unsupported uploads fail without creating an account.
- Existing clients that omit avatar fields continue to register.
- Photo-only preference rejects no-photo candidates in both directions.
- Photo candidates win over higher-scoring no-photo candidates.
- No-photo candidates appear only as a lowered-score standby pool.
- Registration, profile, desktop result, and mobile result views do not overflow.
- The full Python, Node, and harness suites remain green.

## Known limit

The face-check state is deliberately a non-security placeholder. It must be
replaced by a consented liveness and face-comparison provider before making any
claim that an avatar belongs to the account holder.
