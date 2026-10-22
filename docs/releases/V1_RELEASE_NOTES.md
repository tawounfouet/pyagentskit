# PyAgentsKit 1.0.0 — Production Stable

PyAgentsKit 1.0.0 closes the V1 roadmap. It promotes the complete 0.9.0 API candidate without a
functional break and introduces no new provider or orchestration scope.

## Stable surface

- provider-neutral agent, model, message, tool, run and event contracts;
- bounded async mono-agent runtime and deterministic `FakeModel`;
- OpenAI, Anthropic, Google Gemini, xAI, Ollama and OpenRouter adapters;
- sessions, context policies, memory and integrity-checked artifacts;
- guardrails, privacy policy and human approval suspension/resume;
- durable checkpoints, effect journal and explicit ambiguous-effect reconciliation;
- deterministic evaluations, CLI diagnostics, metrics and optional OpenTelemetry;
- wheel, sdist, `py.typed`, Python 3.11–3.13 CI and reproducible builds.

## Compatibility

There is no application migration from 0.9.0. The package root now has an exact 155-symbol freeze,
and the central serialized contracts plus provider constructor parameters are protected by V1
tests. Future incompatible changes require a major version.

## Deliberate exclusions

V1 does not include universal multi-agent orchestration, workflow scheduling, distributed leases,
arbitrary code execution, a proprietary RAG system or automatic provider credential discovery.
PyWorkflowKit integration remains outside this release.
