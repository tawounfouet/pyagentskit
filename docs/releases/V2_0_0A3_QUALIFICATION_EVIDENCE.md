# PyAgentsKit 2.0.0a3 — Qualification Evidence

**Milestone:** `2.0.0a3 — Effects & Recovery Core`  
**Date:** 2026-10-22  
**Qualification baseline commit:** `5ecf456a841204e3a75af3951cd2916e1c9acccc`  
**GitHub Actions run:** https://github.com/tawounfouet/pyagentskit/actions/runs/39727465685  
**Status:** **QUALIFIED — RELEASE PENDING**

## CI gates

The qualification baseline completed with every required job green:

```text
quality                PASS
tests / Python 3.11    PASS
tests / Python 3.12    PASS
tests / Python 3.13    PASS
package                PASS
release-qualification  PASS
```

## Release qualification

`python scripts/release_check.py` completed with:

```text
ruff check              PASS
ruff format --check     PASS
mypy                     PASS
compileall               PASS
pytest                    PASS
coverage >= 90%          PASS
benchmarks                PASS
wheel build               PASS
sdist build               PASS
twine check               PASS
reproducible build        PASS
wheel smoke install       PASS
CLI doctor                PASS
examples                  PASS
A3 effect/recovery demo   PASS
SHA-256 generation        PASS
```

Observed test evidence:

```text
346 passed
12 skipped (live/provider/PostgreSQL opt-in qualification)
coverage: 90.09%
```

The release checker produced both:

```text
pyagentskit-2.0.0a3-py3-none-any.whl
pyagentskit-2.0.0a3.tar.gz
```

and verified a second byte-identical build under the reproducible-build gate.

## A3 safety evidence

The executable suite demonstrates:

- `SUCCEEDED` Effects are not implicitly replayed;
- `UNKNOWN` is not collapsed into `FAILED`;
- a missing response is persisted as `UNKNOWN`;
- `UNKNOWN` blocks runtime progress until reconciliation/manual review;
- a checkpoint cannot override ambiguous Effect truth;
- protected Effects require valid ownership before the external-send boundary;
- Effect intent/`STARTED` is durable before the caller may perform external I/O;
- reconciliation state is durable before provider observation;
- `CONFIRMED_SUCCESS` resumes without resending the Effect;
- `STILL_UNKNOWN` can safely escalate to `MANUAL_REVIEW`;
- Recovery plans are rejected after fencing/lease generation changes;
- runtime recovery is bound to the durable `RuntimeBinding`;
- security/authority assumptions are revalidated before recovery execution;
- W1 through W5 are covered;
- the flagship timeout → crash/takeover → reconciliation → resume path executes without a
  second Effect send.

## Native runtime scope

The Native runtime is connected to the generic recovery execution gate for restart semantics.

It intentionally remains:

```text
SideEffectControlLevel.BOUNDED
```

and does not advertise:

```text
TOOL_INTERCEPTION
RESUME
NATIVE_CHECKPOINT
```

until those guarantees have dedicated V2 contract evidence.

## Deferred to 2.0.0a4 and later

Not part of the A3 qualification:

- production V2 PostgreSQL repositories;
- transactional Unit of Work implementation;
- final distributed persistence;
- external write-capable provider connectors;
- stable/production qualification.

## Release-pending actions

```text
[ ] merge PR #2
[ ] confirm CI green on main
[ ] create Git tag v2.0.0a3
[ ] publish GitHub Release assets
```

The milestone is technically qualified; `QUALIFIED` is deliberately distinct from `RELEASED`.
