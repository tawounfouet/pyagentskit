# Dependency governance

## Runtime dependency

| Package | Range | Purpose | Required | License review |
|---|---|---|---:|---|
| Pydantic | `>=2.10,<3` | Validation, immutable contracts and JSON Schema | Yes | Approved for Phase 0 |

## Build dependency

| Package | Range | Purpose | Rationale |
|---|---|---|---|
| Hatchling | `>=1.27,<1.30` | PEP 517 wheel and sdist build | Metadata 2.4 remains compatible with the current release-check toolchain |

## Optional runtime dependencies

| Extra | Package range | Purpose | Boundary | License review |
|---|---|---|---|---|
| `postgres` | `asyncpg>=0.31,<1` | PostgreSQL connection pooling and protocol | Imported only by explicit pool creation; application owns DSN and lifecycle | Apache-2.0 reviewed |
| `s3` | `boto3>=1.35,<2` | S3 object operations | Imported only by explicit client creation; SDK credential chain remains external | Apache-2.0 reviewed |
| `azure` | `azure-storage-blob>=12.20,<13` | Azure Blob object operations | Imported only by explicit client creation; credential lifecycle remains external | MIT reviewed |
| `production-stores` | Combined optional store SDKs | Deployment convenience | No import-time connection or credential lookup | Component licenses reviewed |
| `providers` | `httpx>=0.27,<1` | Provider HTTP transports | No provider call during import or release qualification | BSD-3-Clause reviewed |
| `opentelemetry` | `opentelemetry-api>=1.30,<2` | Optional telemetry bridge | Payload-safe application-owned exporter | Apache-2.0 reviewed |

## Development dependencies

| Package | Purpose |
|---|---|
| Ruff | Linting and deterministic formatting |
| mypy | Strict static type checking |
| pytest | Test discovery and execution |
| pytest-cov | Branch-aware coverage reporting |
| build | Isolated PEP 517 build |
| Twine | Distribution metadata verification |

## Policy

Every new dependency requires a documented responsibility, supported version range, license
review, security impact and reason it cannot be reasonably provided by an existing dependency or
the standard library.

Provider SDKs and Py\*Kit integrations must remain optional extras.
