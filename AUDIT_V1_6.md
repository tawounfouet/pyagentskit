# Audit — PyAgentsKit 1.6.0 Distributed Operations

Audit date: 2026-09-11

## Conclusion

The release adds operational control without weakening the 1.5 fencing and durability guarantees.
Admission is finite, drain is non-destructive, readiness fails closed, operational telemetry is
payload-free and real process failure paths preserve lease expiry plus monotonic takeover tokens.

## Controls reviewed

- worker incarnation ID retained across health, audit and trace attributes;
- duplicate run and capacity admissions rejected before lease acquisition;
- state changes serialized by an async lock;
- drain blocks new work immediately and never cancels on grace timeout;
- coordination probe cannot mutate controller state and exposes only exception type;
- audit vocabulary contains no prompt, tool name, arguments, results, DSN or exception message;
- JSON Lines sink validates timestamps and serialized contracts on read;
- OpenTelemetry spans close on release or lease loss;
- observer failures are isolated from effect semantics;
- process death leaves the stored lease until TTL expiration;
- process suspension allows a higher-token takeover while the old worker is paused;
- live PostgreSQL test uses two owner identities and the unchanged durable resume path;
- root API, core events, provider signatures and stable schemas remain frozen.

## Residual deployment risks

- best-effort observer isolation may create audit gaps; monitor exporters independently;
- JSON Lines is single-process local evidence, not a centralized compliance journal;
- health probing needs a host-owned timeout to avoid hanging readiness handlers;
- forced termination can still interrupt third-party code after an external commit;
- Kubernetes `preStop` depends on the embedding application exposing the documented endpoint;
- database failover latency and event-loop starvation must fit the measured heartbeat margin;
- PostgreSQL CI does not certify managed-service networking, TLS, IAM, backups or regional failover;
- queue redelivery, poison messages, fairness and backpressure remain outside this release.
