# Roadmap

| Version | Scope |
|---|---|
| 0.1.0a1 | Phase 0 foundation and contracts |
| 0.1.0a2 | Typed tool decorator and executor |
| 0.1.0b1 | Mono-agent runner, limits, events and FakeModel |
| 0.1.0rc1 | Delivered: beta consolidation + OpenAI reference provider |
| 0.1.0rc2 | Delivered: Anthropic, Google Gemini, xAI and Ollama adapters |
| 0.1.0 | **Delivered:** stable mono-agent core and five explicit provider adapters |
| 0.2.0a1 | **Delivered:** minimal deterministic OpenRouter adapter |
| 0.2.0b1 | **Delivered:** OpenRouter routing, catalog and capability negotiation |
| 0.2.0rc1 | **Delivered:** OpenRouter resilience, privacy policy and trace qualification |
| 0.2.0 | **Delivered:** stable optional OpenRouter provider and frozen `0.2.x` API |
| 0.3.0 | **Delivered:** sessions, context policies, memory and artifacts |
| 0.4.0 | **Delivered:** guardrails, privacy policy and human approvals |
| 0.5.0 | **Delivered:** durable checkpoints and recovery, without PyWorkflowKit |
| 0.9.0 | **Delivered:** evals, CLI, observability and production hardening |
| 1.0.0 | **Delivered:** stable public API and final V1 qualification |
| 1.1.0 | **Delivered:** integrated Runner streaming and bounded safe parallel tool calls |
| 1.2.0 | **Delivered:** explicit model retry/backoff and safe stream observability |
| 1.3.0 | **Delivered:** PostgreSQL durable runs and fenced distributed lease ports |
| 1.4.0 | **Delivered:** PostgreSQL state stores, blob artifacts, migrations and RLS assets |
| 1.5.0 | **Delivered:** lease-coordinated distributed durable execution and fenced takeover |
| 1.6.0 | **Delivered:** worker operations, crash qualification, health, drain and telemetry |

Universal multi-agent orchestration is explicitly outside the V1 scope.

Next milestone candidates require a new explicit decision. Any new feature must preserve SemVer and
the V1 contracts; multi-agent orchestration remains out of scope.
