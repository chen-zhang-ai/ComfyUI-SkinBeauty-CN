# Changelog

All notable changes are documented here. This project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Documentation

- Added a MediaPipe environment and version compatibility table that separates verified, CI/mocked, candidate-only, and unverified evidence.
- Documented optional dependency risks, read-only environment checks, and manual model placement with the official URL, size, and SHA256.
- Expanded practical placement examples for reference-video preprocessing, final image grading, masks, multiple references, and decoded video-frame batches.
- Removed the personal MiniMax integration workflow link from the project homepage while keeping the workflow file and its dependency documentation unchanged.

## [2.2.2] - 2026-08-15

### Fixed

- Replaced the standalone `LoadImage` HTTP preview with ComfyUI's official partial-execution protocol and a dev-only ephemeral output target.
- Exact preview now executes the production processor at source resolution with the same IMAGE, settings, external MASK, semantic mode, batch mode, device selection, and OOM fallback.
- Display PNG encoding happens only after the full-resolution tensor result and uses atomic replacement; downstream IMAGE outputs remain unchanged.

### Security and release engineering

- Migrated the public repository to the `chen-zhang-ai` organization without rewriting the v2.2.1 history.
- Added latest-only single-flight preview scheduling, ancestor-only prompt construction, and stale-result rejection so video/save nodes are excluded.
- Pinned GitHub Actions to audited full commit SHAs and made GitHub Release and Registry publishing depend on the complete reusable Quality Gate.
- Expanded resolution, external-mask, partial-graph, concurrency, privacy, packaging, and CI contract tests.

### Compatibility

- Public node class IDs, Python input keys, stored enum values, output order, V1/V2.2 workflow routing, and full-resolution IMAGE behavior remain compatible.

## [2.2.1] - 2026-08-15

### Added

- Official English and Chinese node localization plus bilingual custom preview controls and reports.
- Two dependency-free minimal workflows and a sanitized MiniMax H3 integration workflow.
- Verified, model-only MediaPipe downloader with fixed URL, SHA256, size/timeout limits, load validation, `.part` handling, and atomic replacement.
- Windows/Ubuntu CI, security and package-contract tests, reproducible Release ZIP tooling, and standard open-source governance files.

### Changed

- Removed the approximate browser whitening preview; automatic and manual previews now use the exact backend algorithm.
- Moved the optional MediaPipe list to `extras/requirements-mediapipe.txt` so Manager and Registry cannot auto-run it.
- Hardened OOM fallback, error sanitization, preview path restrictions, documentation, and third-party attribution.

### Compatibility

- Node class IDs, Python input keys, internal enum values, output order, V2.2 workflow routing, and full-resolution `IMAGE` outputs remain compatible.

## [2.2.0] - 2026-08-14

- Initial V2.2 baseline with shared settings, skin processing, exact preview, Canvas comparison, optional MediaPipe integration, and MiniMax workflow wiring.

[2.2.2]: https://github.com/chen-zhang-ai/ComfyUI-SkinBeauty-CN/releases/tag/v2.2.2
[2.2.1]: https://github.com/chen-zhang-ai/ComfyUI-SkinBeauty-CN/releases/tag/v2.2.1
