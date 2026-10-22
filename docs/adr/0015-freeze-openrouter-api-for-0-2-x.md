# ADR-0015 — Freeze the OpenRouter API for the 0.2.x line

- Status: Accepted
- Date: 2026-09-05

## Context

The alpha, beta and RC milestones introduced a useful OpenRouter adapter but did not define which
parts were stable public API and which were implementation details. A stable release needs a
testable compatibility promise without freezing dynamic upstream catalog data.

## Decision

Freeze the symbols declared by `__all__` in the OpenRouter adapter, catalog and routing modules.
Freeze their existing parameters, documented defaults, serialized Pydantic fields, profile values
and schema-v1/v2 snapshot readability for all `0.2.x` patch releases.

Response/capability metadata remains additive. Private names, transport details, upstream model
catalog entries, provider availability and prices are excluded. Security fixes may tighten invalid
or unsafe input acceptance.

The contract is enforced by `tests/test_openrouter_stable_api.py` and documented in
`../compatibility/OPENROUTER_API_STABILITY.md`.

## Consequences

- applications can upgrade within `0.2.x` without changing documented OpenRouter calls;
- accidental signature or serialization changes fail the test suite;
- future features must be additive or wait for a minor-version boundary;
- the framework does not pretend to stabilize data controlled by OpenRouter or upstream providers.
