# ADR-0014 — Conservative capabilities across routed model chains

Status: Accepted  
Date: 2026-09-05

## Context

A model fallback can become the model that actually serves a request. Validating only the primary
model would allow a fallback lacking tools, structured output, modalities or sufficient token
limits to be selected after the runtime preflight had already passed.

## Decision

- Catalog construction checks required capabilities on every explicit model in the route.
- The adapter exposes the intersection of booleans, modalities and known token bounds.
- An unknown bound remains unknown; it is never inferred from the other models.
- Routed models without a common input/output modality are rejected.
- Catalog data remains advisory and marked `model_verified=false`.
- Snapshot schema v2 carries a SHA-256 content check while schema v1 remains readable.

## Consequences

Fallback routing cannot silently weaken the runtime capability contract. Some permissive routes
will now be rejected earlier, which is intentional. The snapshot checksum detects modification but
does not authenticate the source; trusted distribution and deployment-specific live qualification
remain application responsibilities.
