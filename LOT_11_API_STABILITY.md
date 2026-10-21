# Lot 11 API stability — 0.9.0

The complete root export set is the V1 API candidate. Existing 0.5.0 contracts are retained.
0.9.0 adds evaluation contracts, diagnostics, local metrics, an optional OpenTelemetry sink and the
previously implemented `Runner` as an explicit root export.

Stable candidate domains are agent definitions, normalized messages/models, tools, runner and run
results, events, sessions/context/memory/artifacts, guardrails/privacy/approvals, durability,
providers, evaluations and telemetry. Provider catalogs remain time-sensitive observations, not
permanent model guarantees.

CLI JSON output follows the underlying Pydantic contracts. CLI wording and presentation are not a
Python compatibility surface. Private modules and model-specific upstream payloads remain internal.
