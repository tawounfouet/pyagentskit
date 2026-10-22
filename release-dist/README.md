# release-dist

This directory stores release checksum manifests only.

Wheel and sdist binaries are generated reproducibly by `scripts/release_check.py` and retained as
GitHub Actions artifacts. They are intentionally not committed to Git because they are generated
build outputs.

For `2.0.0a3`, the qualified CI artifact contains:

```text
pyagentskit-2.0.0a3.tar.gz
pyagentskit-2.0.0a3-py3-none-any.whl
SHA256SUMS
```

The repository-root `SHA256SUMS` and this directory's `SHA256SUMS` are synchronized with the
qualified release artifact.
