# CLI and diagnostics

The `pyagentskit` command is a thin standard-library facade over public contracts. It introduces no
mandatory CLI dependency and never discovers or imports application code dynamically.

```bash
pyagentskit --version
pyagentskit doctor
pyagentskit config validate agent.json
pyagentskit run agent.json --input hello --response "offline response"
pyagentskit eval validate evals/reference_dataset.json
pyagentskit eval compare baseline.json candidate.json
pyagentskit checkpoint inspect runs.sqlite RUN_UUID --tenant TENANT
```

`run` is deliberately an offline smoke command. It uses `FakeModel`, rejects agent definitions with
tools, and cannot trigger provider costs. Production applications construct `Runner`, tools,
policies and secret providers in Python.

`doctor` checks the supported Python range, the core dependency, provider transport availability
and optional OpenTelemetry API. Missing optional packages are warnings; a broken core is a failure.
Output is JSON and success uses exit code 0. Invalid input and regressions use exit code 2.
