# Final audit - PyAgentsKit 1.0.0

## Verdict

The 0.9.0 API candidate is suitable for promotion to 1.0.0 without a functional change.
The provider-neutral boundary is intact, all effects remain governed, stateful features are
opt-in, and the release can be qualified without network access or credentials.

## Evidence

- exact freeze of 155 root exports;
- field-order freeze for ten central serialized contracts;
- provider constructor and lifecycle compatibility tests;
- full regression coverage of tools, runtime, providers, OpenRouter, sessions, guardrails,
  approvals, durability, evaluations, CLI and telemetry;
- Python 3.11-3.13 CI matrix and strict static typing;
- reproducible wheel and sdist with installed-wheel smoke tests;
- final security and compatibility reviews.

## Accepted residual risks

Provider models, pricing, quotas and privacy eligibility change independently from the package.
SQLite is not a distributed coordination service. External telemetry, secrets, tenant identity,
storage encryption and live model qualification remain deployment responsibilities. These
boundaries are documented and do not block the V1 release.

## Scope after V1

Patch releases fix defects and security issues. Minor releases may add compatible capabilities.
Universal multi-agent orchestration and workflow scheduling remain outside the V1 contract.
