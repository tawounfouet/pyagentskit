# PyAgentsKit 1.0.0 — Final security audit

## Result

The V1 security gates pass for the local, provider-neutral runtime. Untrusted model output is
validated before tool execution; guardrails fail closed; provider egress is policy-controlled;
approvals are tenant-scoped and fingerprint-bound; durable effects cannot be silently replayed.
Secrets are excluded from serializable definitions, logs, release archives and committed env
files. Telemetry exports correlation metadata rather than prompts or tool arguments.

## Supply chain

- the core has one direct runtime dependency: Pydantic 2;
- HTTPX and OpenTelemetry remain bounded optional extras;
- pip check, distribution metadata checks and isolated wheel smoke tests are release gates;
- builds must be byte-identical under the fixed SOURCE_DATE_EPOCH;
- PyPI publication is tag-gated and uses trusted publishing instead of a repository token;
- release artifacts carry SHA-256 checksums.

Installed dependency metadata was checked locally: Pydantic 2.13.5 is MIT and HTTPX 0.28.1 is
BSD-3-Clause. A current external vulnerability database was not available in this offline
qualification and is therefore not claimed as evidence.

## Residual deployment responsibilities

Applications own credential storage, network allowlists, tenant authentication, database and
artifact encryption, backups, OpenTelemetry exporters, reviewer authorization and live provider
qualification. SQLite stores are reference backends, not distributed locks. OpenRouter ZDR
applies only to eligible inference endpoints and does not extend to third-party tools.
