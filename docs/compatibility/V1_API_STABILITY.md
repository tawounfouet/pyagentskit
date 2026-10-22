# PyAgentsKit 1.0.0 — Public API stability contract

The exact 155 names in `pyagentskit.__all__` form the root V1 API. Their canonical sorted-list
SHA-256 is `bfd66c240b638dca67178db2159c49b1df0181a78a405d72f6abb889252b08d9`.

`tests/test_v1_api_freeze.py` verifies this manifest and freezes field order for the central agent,
model, tool, run, event, checkpoint and evaluation contracts. It also freezes provider constructor
parameter names, run statuses and the event vocabulary size.

Compatible additions use a minor release. Bug and security fixes use a patch release. Removing,
renaming or changing required behavior requires a major release. New optional
fields require safe defaults and tolerant readers. Event and checkpoint schema versions remain
independent from package SemVer.

Names prefixed with `_`, upstream payloads and metadata not declared by a public contract remain
internal. Time-sensitive provider capability catalogs are observations, not permanent guarantees.
