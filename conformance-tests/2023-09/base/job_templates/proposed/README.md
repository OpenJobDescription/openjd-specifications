# Proposed conformance fixtures (expected failures) — base/job_templates

Every fixture in this directory is parked because it **fails against at least
one current reference implementation**. Placement is kind-level
(`<component>/<kind>/proposed/`) so promotion is a mechanical move up one
directory once the underlying issue is resolved. The conformance runner does
not scan `proposed/` directories.

Verification environment: `openjd` CLI = openjd-rs release build from
upstream/main (post range-cap fix); cross-checks with openjd-model-for-python
0.11.x via `decode_job_template`.

## INT 64-bit boundary rejects

Spec §2.3 types these fields as `<integer>` with **no stated bound** — the
base 2023-09 document never mentions 64-bit anywhere; the int64 range exists
only in the Expression Language type table (an EXPR document). Both reference
implementations nonetheless *store* INT as a signed 64-bit integer, so
accepted values outside [-2^63, 2^63-1] cannot round-trip and silently
corrupt.

| Fixture | Construct | Observed |
|---|---|---|
| `2.3--int-default-above-int64-max.invalid.yaml` | `default: 9223372036854775808` (2^63) | accepted by **both** (openjd-rs and python) |
| `2.3--int-minvalue-above-int64-max.invalid.yaml` | `minValue: 9223372036854775808` | accepted by both |
| `2.3--int-maxvalue-above-int64-max.invalid.yaml` | `maxValue: 9223372036854775808` | accepted by both |
| `2.3--int-allowedvalues-above-int64-max.invalid.yaml` | `allowedValues: [9223372036854775808]` | accepted by both |
| `2.3--int-default-below-int64-min.invalid.yaml` | `default: -9223372036854775809` (-2^63-1) | accepted by both |

Classification: **spec question first, then implementation fix** — because the
base spec states no integer bound, a bignum implementation accepting these is
arguably conformant as the text stands. Promotion is gated on a base-spec
integer-bounds erratum (pin `<integer>` to int64 in §2.3); once that lands,
these become straightforward validation-bug pins, one branch per field. The
matching accept-twins at 2^63-1 and -2^63 are added by the base-gaps PR
(`job_templates/2.3--int-*-int64-max.yaml` etc.).

Related, different axis: the *supplied value* case lives in
`../../jobs/proposed/2.3--int-value-above-int64-max.invalid.test.yaml` — that
one is **Python-only** (openjd-rs rejects a supplied 2^63 at job creation;
openjd-model 0.11.x `create_job` accepts it).

## Type-name case sensitivity

| Fixture | Construct | Observed |
|---|---|---|
| `2--type-lowercase.invalid.yaml` | `type: string` in base (no `extensions:`) | openjd-rs: **accepted**; python: rejected ("Input tag 'string' ... does not match any of the expected tags") |

Spec §2: `type: "STRING"` is a literal, and the spec states type names become
case-insensitive only "When the `EXPR` extension is enabled" (see RFC 0007).
Base is case-sensitive.

Classification: **openjd-rs implementation bug** (unconditional
case-insensitive type parsing); python is spec-conformant. Note: the
param-types expected-failures PR previously carried an identical pin
(`2--type-lowercase-string.invalid.yaml`); it was dropped in favor of this
one — this fixture is the single copy.
