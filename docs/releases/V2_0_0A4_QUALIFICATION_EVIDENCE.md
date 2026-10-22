# PyAgentsKit 2.0.0a4 — Qualification Evidence

**Milestone:** `2.0.0a4 — Persistence V2`  
**Date:** 2026-10-22  
**Qualification baseline commit:** `66452a3624c4be8b5ac1b26d81e08da32e88949d`  
**GitHub Actions run:** https://github.com/tawounfouet/pyagentskit/actions/runs/39850160169  
**Status:** **QUALIFIED — RELEASE PENDING**

## CI gates

The qualification baseline completed with every required job green:

```text
quality                PASS
tests / Python 3.11    PASS
tests / Python 3.12    PASS
tests / Python 3.13    PASS
postgres-v2            PASS
package                PASS
release-qualification  PASS
```

## Deterministic test and coverage evidence

The release qualification executed the complete offline suite and then applied an independent
coverage threshold gate:

```text
452 passed
38 skipped (explicit live/provider/PostgreSQL opt-in paths)
coverage: 90.49%
required coverage: 90.00%
coverage report --fail-under=90: PASS
```

The explicit post-pytest coverage gate exists so a rounded terminal percentage cannot make a
sub-threshold release appear green.

## PostgreSQL V2 evidence

The dedicated PostgreSQL 16 qualification completed with:

```text
26 passed
```

It exercises the production-oriented V2 persistence behavior against a real PostgreSQL service,
including:

- the shared P0 repository contract suite;
- Run compare-and-swap conflict behavior;
- durable Effect idempotency and fingerprint conflict detection;
- Session, Conversation, Message, Worker and Artifact persistence;
- durable RuntimeBinding and RuntimeInvocation state;
- one-active-owner lease behavior;
- monotonic fencing tokens;
- transactional UnitOfWork boundaries;
- domain state + Outbox atomicity;
- Outbox claim/reclaim after publisher interruption;
- Inbox duplicate/no-op and digest-conflict behavior;
- multi-process lease contention.

## P0 repository contract evidence

The reusable persistence contract suite covers:

```text
RunRepository
SessionRepository
ConversationRepository
MessageRepository
MemoryRepository
EffectRepository
ReconciliationRepository
ApprovalRepository
LeaseRepository
WorkerRepository
RuntimeRepository
ArtifactRepository
AuditStore
OutboxStore
InboxStore
UnitOfWork
```

The same contract semantics are exercised across Memory, SQLite and PostgreSQL where applicable.

## Migration evidence

Persistence V2 uses incremental schema migrations:

```text
0001_v2_core.sql
0002_v2_catalog.sql
```

SQLite explicitly proves:

```text
schema version 1
→ initialize current adapter
→ schema version 2
→ catalog tables available
```

The PostgreSQL migration runner is exercised against the real CI service and rejects future schema
versions that the code does not understand.

## Persistence safety evidence

The executable qualification demonstrates:

- stale aggregate writes fail closed with `ConcurrencyConflictError`;
- duplicate aggregate identity is explicit;
- same Effect idempotency key + different fingerprint is rejected;
- one active lease per protected resource is enforced;
- fencing tokens increase monotonically;
- canonical domain/persistence conflicts survive adapter normalization;
- UnitOfWork rollback removes catalog state and Outbox state together;
- UnitOfWork commit persists domain state and Outbox state together;
- Inbox deduplication remains distinct from Effect idempotency;
- restore/PITR does not imply safe Effect replay.

## Packaging and release qualification

`python scripts/release_check.py` completed with:

```text
ruff check                    PASS
ruff format --check           PASS
mypy --strict                 PASS
compileall                    PASS
pytest                        PASS
coverage >= 90%               PASS
runtime benchmarks            PASS
wheel build                   PASS
sdist build                   PASS
twine check                   PASS
reproducible second build     PASS
fresh wheel installation      PASS
CLI doctor                    PASS
offline examples              PASS
A3 effect/recovery example    PASS
A4 persistence example        PASS
SHA-256 generation            PASS
```

## A4 documentation shipped with the distribution

The release distribution includes:

- `docs/guides/V2_PERSISTENCE.md`;
- `docs/releases/V2_0_0A4_RELEASE_NOTES.md`;
- `docs/releases/V2_0_0A4_QUALIFICATION_EVIDENCE.md`;
- `docs/specs/milestones/53_PYAGENTSKIT_MILESTONE_2_0_0A4_PERSISTENCE_V2_SPEC.md`;
- `examples/v2_persistence.py`.

## Deferred to later milestones

Not part of A4:

- enterprise authorization/policy governance — `2.0.0b1`;
- external general-purpose and coding-agent runtimes — `2.0.0b2`;
- write-capable external connectors and their remote reconciliation strategies — `2.0.0b2`;
- multi-region database architecture;
- V2 stable public-contract freeze — `2.0.0rc1`.

## Release-pending actions

```text
[x] include this evidence in a final qualified sdist
[ ] synchronize final SHA-256 manifests with the qualified release artifact
[ ] mark PR #3 ready for review
[ ] merge PR #3
[ ] confirm CI green on main
[ ] create Git tag v2.0.0a4
[ ] publish GitHub Release assets
```

The milestone is technically qualified. `QUALIFIED` remains deliberately distinct from
`RELEASED`.
