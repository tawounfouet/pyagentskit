# Phase 0 — Foundation

## Goal

Deliver lots 00–01: a governed, installable Python package whose public domain contracts are
defined and tested before any agent runtime or provider implementation is introduced.

## Included

- packaging, licensing, CI and contribution policy;
- architectural boundaries and ADRs;
- agent definition and model reference;
- message and multimodal content contracts;
- model request, response and capabilities contracts;
- tool definition, call, result and protocol;
- run identifiers, context, limits, status and result;
- normalized usage and errors;
- structured event contract and handler protocol;
- tests for invariants and protocol conformance.

## Excluded

- `@tool` decorator and execution;
- agent decision loop;
- model providers;
- streaming implementation;
- sessions and persistence;
- guardrails and approvals;
- durable execution;
- multi-agent collaboration;
- CLI commands.

## Exit criteria

1. The wheel and source distribution build successfully.
2. Public imports are explicit and typed.
3. Core models reject invalid identifiers, limits and timestamps.
4. A third party can implement the `Model`, `Tool` and `EventHandler` protocols.
5. Core modules do not import provider SDKs or another Py\*Kit.
6. Lint, formatting, typing and tests pass.

