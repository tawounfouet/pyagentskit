# release-dist

This directory stores release checksum manifests only.

Wheel and sdist binaries are generated reproducibly by `scripts/release_check.py` and retained as
GitHub Actions artifacts. They are intentionally not committed to Git because they are generated
build outputs.

For `2.0.0a4`, the qualified CI artifact contains:

```text
pyagentskit-2.0.0a4.tar.gz
pyagentskit-2.0.0a4-py3-none-any.whl
SHA256SUMS
```

Qualification baseline:

```text
GitHub Actions run: 39850666236
qualified commit: f76f8a0b717379353ad261fc5a07f2cddcbaa549
coverage: 90.49%
PostgreSQL V2 live qualification: PASS
```

The repository-root `SHA256SUMS` and this directory's `SHA256SUMS` are synchronized with the
qualified release artifact.
