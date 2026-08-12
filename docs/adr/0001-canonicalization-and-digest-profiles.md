# ADR-0001: canonicalization and digest profiles

- **Status:** Accepted for the CPAS v2 draft when this change is merged
- **Decision scope:** IDP identity, DKA-E snapshots, runtime capability
  profiles, SeedToken integrity, and SeedToken HMAC authentication
- **Issue:** [#97](https://github.com/SpartanM34/Reflective-AI-and-CPAS-Core/issues/97)
- **Date:** 2026-08-12

## Context

The original v2 draft used `cpas-canonical-json-v1`: Python `json.dumps` with
sorted keys, compact separators, preserved Unicode, and non-finite values
rejected. That encoding is deterministic for the accepted Python data model,
but it is not a portable protocol definition. Python and ECMAScript can differ
in number rendering and object-key ordering. A digest computed by one runtime
therefore was not safely reproducible by another.

This is a protocol concern, not an identity claim. Changing the digest encoding
must not imply that the declared Clarence-9 identity changed. It changes the
content-address representation of the stable identity projection.

[RFC 8785](https://www.rfc-editor.org/rfc/rfc8785) defines the JSON
Canonicalization Scheme (JCS) using ECMAScript primitive serialization, the
I-JSON data model, and deterministic UTF-16 property sorting. It is an
Informational RFC rather than an Internet Standards Track specification, but it
provides a documented cross-language target and public test material.
[RFC 7493](https://www.rfc-editor.org/rfc/rfc7493) defines I-JSON constraints.

## Comparison

| Concern | `cpas-canonical-json-v1` | RFC 8785/JCS consequence |
|---|---|---|
| Object ordering | Python string ordering | UTF-16 code-unit ordering; supplementary-plane keys can move |
| Numbers | Python number rendering | ECMAScript number rendering, including exponent thresholds and `-0` |
| Unicode | UTF-8 output, no normalization | UTF-8 output, no normalization, invalid surrogate code points rejected |
| Duplicate members | Rejected by the CPAS strict loader | Must be rejected before canonicalization |
| Non-finite numbers | Rejected | Rejected |
| Large integers | Python can represent arbitrary integers | Producers must remain in the interoperable I-JSON/IEEE-754 domain; the Python reference rejects integers outside its safe domain |
| Cross-runtime claim | None | Reproducible only for implementations that pass the normative vectors |

## Decision

### 1. Freeze the legacy profile

`cpas-canonical-json-v1` remains unchanged. Its digest profile is
`cpas-sha256-direct-v1`, defined as:

```text
SHA-256(cpas-canonical-json-v1(value))
```

Existing records may omit `digest_profile`; when and only when their
canonicalization is `cpas-canonical-json-v1`, omission resolves to
`cpas-sha256-direct-v1`. This is a compatibility inference, not a rewrite.

### 2. Use RFC 8785 for new semantic digests

The new canonicalization profile is `rfc8785-jcs-v1`. The version suffix names
the CPAS adoption profile; the canonical bytes are RFC 8785 JCS bytes. CPAS
does not normalize Unicode before canonicalization. Producers must reject
duplicate members, non-finite values, invalid Unicode scalar values, and values
outside the supported I-JSON number domain.

The Python reference pins
[`rfc8785` 0.1.4](https://pypi.org/project/rfc8785/). The dependency is an
implementation, not the protocol authority; the RFC, this ADR, and the
normative vectors define repository behavior.

### 3. Domain-separate every semantic digest

New SHA-256 semantic digests use this exact byte preimage:

```text
ASCII("CPAS-DIGEST-V2") || 00 ||
ASCII(digest_profile) || 00 ||
ASCII("rfc8785-jcs-v1") || 00 ||
JCS(value)
```

`00` is one NUL byte. Profile identifiers are ASCII and cannot contain NUL.
Digest text is `sha256:` followed by 64 lowercase hexadecimal characters.

| Artifact | Digest profile | Canonical value |
|---|---|---|
| IDP stable identity | `cpas-digest-v2:idp-identity` | `idp_version`, `instance_id`, `instance_name`, `identity_profile`, `epistemic_policy`, and `safety` |
| DKA-E snapshot | `cpas-digest-v2:dka-snapshot` | Complete record with only `integrity.digest` omitted |
| Capability profile | `cpas-digest-v2:capability-profile` | Capability `name`/`status` pairs, sorted by name |
| SeedToken integrity | `cpas-digest-v2:seed-token-integrity` | Complete token with `authenticator` and `integrity.digest` omitted |

The profile identifier is part of the preimage. Identical JSON content in two
artifact domains therefore produces different digests.

### 4. Keep raw-file hashes distinct

`raw-sha256` means SHA-256 over the exact stored bytes. It is used for repository
source and artifact references. It is not JCS, does not use the CPAS digest
frame, and must not be substituted for an identity or DKA digest.

### 5. Domain-separate the v2 SeedToken HMAC

`cpas-hmac-v2:seed-token-authentication` uses:

```text
ASCII("CPAS-HMAC-V2") || 00 ||
ASCII("cpas-hmac-v2:seed-token-authentication") || 00 ||
ASCII("rfc8785-jcs-v1") || 00 ||
JCS(token with authenticator.tag omitted)
```

Existing HMAC tokens with legacy canonicalization and no authentication profile
remain verifiable as `cpas-hmac-direct-v1`. Neither HMAC profile grants
authorization or confidentiality. The unkeyed digest remains integrity
metadata, not authentication.

### 6. Negotiate by explicit markers

A verifier must inspect both `canonicalization` and the applicable digest or
authentication profile. Unknown or incompatible combinations fail closed. A
JCS value without a domain profile is invalid. A legacy value without a profile
may be read only through the compatibility rule above.

Schema compatibility remains intentionally asymmetric:

- existing legacy v2 draft records continue to parse and verify;
- newly emitted records include explicit profiles;
- migrating a value recomputes it and records the former value; it never
  relabels old digest text;
- semantic identity comparison projects declared identity fields rather than
  comparing profile-dependent digest strings.

## Normative verification

[`cpas-canonicalization-v1.json`](../../compliance-tests/canonicalization/cpas-canonicalization-v1.json)
contains positive, legacy, Unicode/key-order, number-boundary, and negative
vectors. The Python reference and an independent Node.js implementation must
both reproduce every positive byte string and domain digest. Both also reject
the negative parser/data-model vectors.

Passing the vectors demonstrates conformance for those cases. It does not prove
cryptographic authenticity, implementation security, or correctness for every
possible input.

## Threat analysis

| Threat | Treatment | Residual risk |
|---|---|---|
| Artifact substitution across domains | Profile identifier is hashed in the preimage | A caller that ignores the profile can still misuse a digest |
| Ambiguous concatenation | NUL-delimited fixed frame and NUL-free ASCII identifiers | Implementations must reproduce the byte layout exactly |
| Duplicate object members | Strict parse before canonicalization | Alternate parsers must implement the same boundary |
| Unicode key-order drift | JCS UTF-16 ordering plus supplementary-plane vectors | Unicode normalization remains intentionally out of scope |
| Number-format drift | ECMAScript/JCS serialization plus boundary vectors | Application values outside interoperable I-JSON remain invalid/ambiguous |
| Legacy/new confusion | Separate canonicalization and digest-profile names | Unlabeled values outside the documented legacy rule cannot be recovered safely |
| Digest replacement | Optional authenticated channel/HMAC and trusted expected digest | Unkeyed SHA-256 alone does not authenticate an issuer |
| Dependency drift | Exact test dependency and independent vectors | A compromised dependency/toolchain remains an operational risk |

## Alternatives considered

- **Silently change `cpas-canonical-json-v1`: rejected.** Existing values would
  be reinterpreted and could no longer be verified reliably.
- **Keep the Python profile for new records: rejected.** It cannot support the
  requested cross-runtime portability claim.
- **Deterministic CBOR: deferred.** It can be compact and well specified, but
  would add a second data model and migration burden while current protocols
  are JSON-native.
- **Hash JCS bytes without a domain frame: rejected.** It permits semantically
  different artifact types with equal JSON to share a digest.
- **Use HMAC or signatures for every digest: rejected.** Content addressing,
  authentication, authorization, and provenance are distinct mechanisms.

## Consequences

This is an explicitly breaking change for newly emitted v2 draft digest values,
while retaining read/verify compatibility for old values. Current examples and
cross-references receive new digests. Consumers must treat a digest as a tuple
of algorithm, canonicalization, and digest profile. Stable CPAS 2.0 should not
rename or alter these profiles without a new protocol version and vectors.

The decision resolves the canonicalization choice for the current v2 draft. It
does not resolve public-key signatures, key governance, or production storage
trust.
