# Architecture / 架构

## Runtime data flow

```text
SkinBeautySettingsCN
  -> immutable config dictionary
IMAGE (+ optional MASK)
  -> semantic_mediapipe.py (optional local hint or safe fallback)
  -> skin_core.py (mask, Lab correction, texture/highlight controls)
  -> full-resolution IMAGE + MASK + full-resolution preview IMAGE
  -> nodes.py::run_skin_beauty (single production service and bilingual report)
  -> SkinBeautyPreviewSinkCN (dev-only, UI temporary PNG after processing)
  -> web/skin_beauty.js (partial-execution request and Canvas comparison)
```

- `skin_core.py` contains pure PyTorch color conversion, mask composition, full-resolution correction, batching, and configuration validation. It has no dependency beyond PyTorch.
- `semantic_mediapipe.py` is an optional adapter. Auto mode only reuses a valid local model. Explicit download mode performs a bounded, verified, atomic model-only download and never installs packages.
- `nodes.py` defines the stable ComfyUI contract and `run_skin_beauty`, the sole configuration, semantic/external-mask, batch, device, OOM, result, and report path used by normal execution and exact preview.
- `web/exact_preview_prompt.js` clones only the processor and its required ancestors, injects one dev-only output sink, and implements latest-only single-flight coordination.
- `web/skin_beauty.js` reads the public `Comfy.Locale` setting, submits ComfyUI's official `partialExecutionTargets`, rejects stale results, and draws the independent 1 px Canvas comparer.
- `locales/{en,zh}` localize official node definitions while leaving Python keys and saved enum values unchanged.

## Trust boundaries

Normal and preview execution both accept in-memory tensors through the ComfyUI prompt queue. The preview prompt contains only the selected processor, its IMAGE/settings/MASK ancestors, and an ephemeral `DEV_ONLY` output; unrelated downstream nodes, including node 186 and video/save outputs, are absent. The sink scales only the first batch item for display, writes a metadata-free PNG by atomic replacement, and never returns a local absolute path. Network access exists only in the explicit model-download branch and is restricted to the fixed Google Storage host. Download failures never replace a known-good model.

The processor remains a normal non-output node, so ordinary queues do not acquire extra work. `SkinBeautyPreviewSinkCN` is hidden outside ComfyUI developer mode and appears only in the transient API prompt; it is not serialized into user workflows. A 650 ms debounce plus `LatestOnlyGate` permits one in-flight preview per processor, replaces intermediate pending requests with the newest request, and applies a result only when its token is current.

## Compatibility boundary

Class IDs, Python input names, internal combo values, output indexes, and full-resolution tensor behavior are persistent workflow/API fields. Display translations are separate. V2.2 integration node IDs 272/273/274/186, reference order, links, and bypass modes are covered by tests.

## Packaging boundary

The source repository contains tests and build tools; the Release ZIP contains one `ComfyUI-SkinBeauty-CN/` root with runtime modules, `web`, `locales`, user docs, workflows, license, and optional dependency notice. It excludes CI, development tools, tests, caches, logs, raw media, and secrets.
