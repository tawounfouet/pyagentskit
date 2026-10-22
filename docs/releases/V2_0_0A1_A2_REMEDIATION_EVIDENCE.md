# PyAgentsKit 2.0.0a1 / 2.0.0a2 — Remediation Qualification Evidence

**Date:** 2026-10-22  
**Branch:** `remediation/v2-a1-a2-gap-closure`  
**Green code-bearing commit:** `144954c363de61087af3ba3dd7676e3b72d9f617`  
**GitHub Actions run:** https://github.com/tawounfouet/pyagentskit/actions/runs/39720493766

## Verified gates

The remediation pipeline completed successfully for all required jobs:

```text
quality        PASS
tests 3.11     PASS
tests 3.12     PASS
tests 3.13     PASS
package        PASS
```

The `quality` job proves:

```text
ruff check
ruff format --check
mypy
compileall
```

The test matrix includes the V2 unit/state tests, Hypothesis property tests, recursive architecture
checks, capability negotiation tests and the reusable runtime-adapter contract harness.

The `package` job proves:

```text
wheel build
sdist build
twine check
true isolated venv creation
wheel install with dependency resolution
package import
V2 OwnershipContext / MessageRecipient import
pip check
```

The qualified clean-install job does not use `--system-site-packages` and does not use
`--no-deps`.

## Remediation guarantees covered

```text
OwnershipContext is typed
MessageRecipient exists
ReconciliationStatus is explicit
Domain property tests exist
architecture checks are recursive
Application does not privilege Native by runtime name
RuntimeBinding family continuity fails closed
Native capability claims are conservative
Native side-effect control is BOUNDED
common adapter contracts run against Native + external fake
incompatible runtime versions fail negotiation before resume
CI is active
clean installation is proven
```

## Remaining release actions

The remediation code is qualified, but `IMPLEMENTED` and `RELEASED` remain distinct.

Before marking the alpha milestones released:

```text
[ ] merge remediation PR
[ ] run final CI on main
[ ] execute release_check.py to rebuild release-dist
[ ] commit regenerated SHA256SUMS if release artifacts are tracked
[ ] create/push the intended alpha tags
[ ] publish GitHub Release assets
```

No full A3 RecoveryPlanner, Effect reconciliation port, PostgreSQL V2 repository or external
runtime connector is included in this remediation.
