# Architecture / 架构

## Runtime data flow

```text
SkinBeautySettingsCN
  -> immutable config dictionary
IMAGE (+ optional MASK)
  -> semantic_mediapipe.py (optional local hint or safe fallback)
  -> skin_core.py (mask, Lab correction, texture/highlight controls)
  -> full-resolution IMAGE + MASK + full-resolution preview IMAGE
  -> nodes.py (bilingual report and UI-only temporary PNG)
  -> web/skin_beauty.js (exact-preview request and Canvas comparison)
```

- `skin_core.py` contains pure PyTorch color conversion, mask composition, full-resolution correction, batching, and configuration validation. It has no dependency beyond PyTorch.
- `semantic_mediapipe.py` is an optional adapter. Auto mode only reuses a valid local model. Explicit download mode performs a bounded, verified, atomic model-only download and never installs packages.
- `nodes.py` defines the stable ComfyUI contract, device/OOM policy, sanitized input-image resolution, and exact-preview route.
- `web/skin_beauty.js` reads the public `Comfy.Locale` setting, localizes custom controls, debounces exact preview, and draws the independent 1 px Canvas comparer.
- `locales/{en,zh}` localize official node definitions while leaving Python keys and saved enum values unchanged.

## Trust boundaries

The normal queue accepts in-memory tensors. The standalone preview endpoint treats browser payloads as untrusted: it accepts only a basename plus a safe relative subfolder under ComfyUI `input`, rejects other source types and traversal, and never returns a local absolute path. Network access exists only in the explicit model-download branch and is restricted to the fixed Google Storage host. Download failures never replace a known-good model.

## Compatibility boundary

Class IDs, Python input names, internal combo values, output indexes, and full-resolution tensor behavior are persistent workflow/API fields. Display translations are separate. V2.2 integration node IDs 272/273/274/186, reference order, links, and bypass modes are covered by tests.

## Packaging boundary

The source repository contains tests and build tools; the Release ZIP contains one `ComfyUI-SkinBeauty-CN/` root with runtime modules, `web`, `locales`, user docs, workflows, license, and optional dependency notice. It excludes CI, development tools, tests, caches, logs, raw media, and secrets.
