# SeedToken v2.0

**Status:** draft protocol with reference validation

**Normative schema:** [`schemas/seed-token-v2.0.schema.json`](../../schemas/seed-token-v2.0.schema.json)

## Purpose and non-purpose

A SeedToken is a compact, human-readable continuity manifest. It names the
declared instance, identity digest, runtime observation, capability profile,
exact state references, parent token, provenance, and requested continuity
scope.

| Property | Provided? | Qualification |
|---|---|---|
| Identity declaration | **Reference only** | The token points to an IDP/identity digest; it is not the full identity. |
| Integrity | **Yes, limited** | An unkeyed digest detects change only when the expected digest or token arrives through a trusted path. |
| Authentication | **Optional** | The reference implementation supports HMAC-SHA256 when the verifier already shares a secret identified by `key_id`. |
| Authorization | **No** | Possessing or validating a token grants no right to read state or call tools. |
| Provenance | **Metadata** | Source references and issuer claims become trustworthy only through a trusted channel/authenticator. |
| Public-key signature / non-repudiation | **No** | v2.0 defines no public-key signature profile. Do not populate a generic `signature` field. |

## Canonicalization and integrity

`cpas-canonical-json-v1` is UTF-8 JSON with sorted object keys, compact
separators, Unicode preserved, and non-finite numbers rejected. It is a local
deterministic profile, not RFC 8785.

To compute `integrity.digest`:

1. remove the entire `authenticator` member, if present;
2. remove `integrity.digest`, retaining the integrity algorithm and
   canonicalization fields;
3. canonicalize and SHA-256 hash the remaining token;
4. store `sha256:<lowercase hex>`.

This detects accidental or malicious modification only when a verifier has a
trusted expected token/digest. An attacker able to replace the token can also
recompute an unkeyed digest.

## Optional HMAC authentication

The repository implements one symmetric authenticator:

1. first populate and verify `integrity.digest`;
2. set `authenticator.type` and `authenticator.key_id`, leaving out `tag`;
3. canonicalize the complete token with only `authenticator.tag` omitted;
4. compute HMAC-SHA256 and store `hmac-sha256:<lowercase hex>`.

The HMAC authenticates possession of a shared secret to another holder of that
secret. It does not identify a human by itself, grant authorization, protect
confidentiality, or provide non-repudiation. Key generation, distribution,
rotation, revocation, and storage are deployment responsibilities. Tokens must
never contain the secret.

## Validation logic

Validation returns a structured result rather than a single “continuity valid”
boolean:

1. parse JSON while rejecting duplicate object keys;
2. validate the v2 schema and date-time formats;
3. recompute and constant-time compare the integrity digest;
4. require `expires_at > created_at`, and reject a token expired at the
   verifier’s clock;
5. compare `instance_id` and `identity_digest` with the expected IDP;
6. if a parent is expected, compare both parent token ID and parent integrity
   digest; the link is evidence of ordering, not a globally unique chain;
7. if authentication is required, resolve `key_id` through a trusted key store
   and constant-time verify the HMAC;
8. separately authorize each referenced state object before retrieval;
9. report which requested continuity forms could actually be activated.

Unknown keys, missing state, clock uncertainty, capability drift, and denied
access are explicit errors/warnings. Validation never fabricates unavailable
memory.

## Threat model

| Threat | Mitigation | Residual risk |
|---|---|---|
| Accidental alteration | Canonical SHA-256 digest | No protection if expected digest is replaced too. |
| Token substitution | HMAC plus trusted `key_id` lookup | Shared-secret compromise permits forgery. |
| Replay | Expiration, parent expectations, deployment nonce/event checks | Offline tokens without verifier state remain replayable. |
| State substitution | Exact state digests and store-side verification | Ref resolution/authorization must be trusted. |
| Prompt injection in state | Rehydration labels content as untrusted data | A vulnerable host may still promote data to instruction. |
| Secret disclosure | Key IDs only; secrets external | Operational key handling is out of protocol scope. |
| Unauthorized access | External per-reference policy enforcement | Token validation alone does nothing. |
| Privacy leakage | Minimize claims/refs; secure transport and retention | Token metadata can reveal models, projects, or state names. |
| Hash collision | SHA-256 | No known practical collision, but this is not authentication. |
| Misleading identity claim | Compare with trusted IDP and optional authenticator | An authenticated issuer can still make a false semantic claim. |

## Migration from SeedToken v1

- Preserve the original token verbatim under a migration record or extension.
- Map `id` to `instance_id` only after determining whether it named an instance
  or token; create a new unique `token_id`.
- Move `model` to the runtime observation. It does not enter the identity digest.
- Map alignment prose to an IDP reference/profile summary; do not treat it as
  authorization.
- Record the old `hash` and `chain_hash` as legacy values. Recompute v2 integrity
  from canonical v2 content; never relabel an old hash as an HMAC or signature.
- Default continuity scope to `declarative` unless concrete context, DKA, or
  store references can be verified.

See [`examples/v2/seed-token-v2.example.json`](../../examples/v2/seed-token-v2.example.json)
for a non-secret documentation token. Its HMAC key is intentionally documented
for tests and therefore supplies no real authentication.
