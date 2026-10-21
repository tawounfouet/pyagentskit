# Lot 11 qualification — 0.9.0

Qualification covers deterministic assertions, report persistence and comparison, CLI exit codes,
safe offline execution, diagnostics, metrics aggregation and OpenTelemetry lifecycle using an
in-memory tracer. The full legacy suite protects all five direct providers and OpenRouter,
governance, sessions and durable recovery.

The release gate runs Ruff, formatting, strict Mypy, byte compilation, the full offline test suite,
the runtime benchmark, distribution build, Twine metadata validation, archive inspection,
byte-for-byte rebuild comparison and wheel smoke tests. No live request is made.

Final measured counts and hashes are recorded in `CHECK_RESULTS.md`, `BENCHMARK_RESULTS.md` and
`SHA256SUMS` after the release-check.
