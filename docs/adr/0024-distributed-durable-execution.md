# ADR-0024 — Lease-coordinated durable execution

Status: Accepted  
Date: 2026-09-09

## Context

`DurableRunner` journals checkpoints and ambiguous tool effects, while `LeaseStore` provides
tenant-scoped ownership and monotonically increasing fencing tokens. Until 1.5.0 the application
had to compose those facilities itself, leaving heartbeat, stale-worker shutdown and token
propagation open to inconsistent implementations.

## Decision

Add `DistributedDurableRunner` as a submodule-scoped wrapper around `DurableRunner` and
`LeaseStore`.

- acquisition is explicit and single-shot;
- renewal has a finite interval and maximum count;
- renewal loss cancels the active run;
- a fencing policy runs before the durable effect policy and again before effect acknowledgement;
- tools receive a typed `FencingToken` through `RunContext`;
- protected resources must compare the token and apply the write atomically;
- takeover uses the existing durable resume and reconciliation rules;
- no lease event implies a model, tool or business-effect retry.

## Consequences

A worker known to be stale cannot plan a new effect. An effect already in flight when ownership is
lost remains ambiguous and becomes `UNKNOWN_EFFECT`; another worker cannot replay it without an
explicit operator resolution. The fencing token, rather than an earlier lease check, closes the
expiry race at the protected resource.

This is worker coordination, not scheduling, multi-agent orchestration or a workflow engine.
