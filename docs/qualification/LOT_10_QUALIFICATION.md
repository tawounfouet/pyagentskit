# Lot 10 qualification — PyAgentsKit 0.5.0

The deterministic suite qualifies:

- completed model-tool-model runs and contiguous checkpoints;
- planned/started/completed/unknown effect transitions;
- blocked recovery before operator reconciliation;
- `COMMITTED` recovery without tool replay;
- `NOT_APPLIED` controlled retry;
- analytical replay without model or tool execution;
- agent-version and tenant isolation failures;
- approval suspension/resume through the same effect ledger;
- credential-pattern redaction in durable effect state;
- synthetic checkpoint v0-to-v1 migration and future-version rejection;
- SQLite close/reopen persistence and schema migration metadata.

Provider live tests remain opt-in and are unrelated to this local durability qualification. The
release check installs the wheel offline and executes the durable example against SQLite.
