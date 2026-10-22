# Deprecation policy

PyAgentsKit 1.0.0 is the first stable public API. The 0.9.x candidate was promoted without a
functional break.

From 1.0.0 onward:

- public names in `pyagentskit.__all__` follow semantic versioning;
- incompatible removals require a major version;
- deprecated APIs remain for at least one minor release when practical;
- urgent security fixes may shorten that period and must explain the reason;
- event and checkpoint `schema_version` values evolve independently from package versions;
- optional provider capabilities can change only when upstream reality changes and are documented.

Modules prefixed with `_`, test helpers not exported publicly and serialized provider metadata not
declared in a public contract are internal.
