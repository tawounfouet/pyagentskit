# PyAgentsKit 1.0.0 - Final qualification

The stable release runs linting, format checks, strict typing, byte compilation, the full
deterministic test suite with branch coverage, the offline benchmark, package builds, metadata
validation, archive inspection, reproducibility checks and installed-wheel smoke scenarios.

The suite protects all previously delivered domains and adds an exact V1 API freeze. The wheel
is installed away from the source tree before CLI, provider imports, state contracts, runtime,
session, approval and durability examples are exercised.

The local run uses Python 3.12. GitHub Actions defines the supported Python 3.11, 3.12 and 3.13
matrix. Provider wire contracts use HTTP mocks. Live provider checks remain opt-in and the
release gate makes no authenticated or billable request.

Exact counts, coverage, benchmark values and hashes are recorded in CHECK_RESULTS.md and
SHA256SUMS after the final run.
