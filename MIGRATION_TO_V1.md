# Migration from 0.9.x to 1.0.0

No functional migration is required from 0.9.0 to 1.0.0. Existing runtime, provider, session,
guardrail, approval, durability, evaluation and telemetry contracts remain compatible.

Before moving an application to 1.0.0:

1. replace imports from private modules with names exported by `pyagentskit`;
2. validate serialized agent definitions with `pyagentskit config validate`;
3. retain a baseline `EvalReport` and reject unexpected regression in CI;
4. verify checkpoint schema compatibility and resolve `unknown_effect` states manually;
5. pin optional provider extras and run their opt-in qualification against chosen model revisions;
6. review data policies, redaction and approval stores for every tenant;
7. run `pyagentskit doctor` and the application smoke suite from the built wheel.

The final audit introduced exact API-freeze tests but no behavior change. Future incompatible
changes require a major release and an explicit migration note.
