# Changelog

All notable changes are documented here. This project follows [Semantic Versioning](https://semver.org/).

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

[2.2.1]: https://github.com/likun199679-bot/ComfyUI-SkinBeauty-CN/releases/tag/v2.2.1
