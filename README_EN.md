# ComfyUI-SkinBeauty-CN

[中文](README.md) · [Changelog](CHANGELOG.md) · [Security](SECURITY.md) · [Issues](https://github.com/likun199679-bot/ComfyUI-SkinBeauty-CN/issues)

ComfyUI nodes for naturally shifting yellow or warm face and body skin toward a cooler, brighter tone while protecting backgrounds, clothing, highlights, and real skin texture.

## Features and advantages

- The core path uses only the PyTorch already provided by ComfyUI: `dependencies = []`, with no automatic package install, upgrade, or removal.
- An adaptive skin mask targets skin instead of whitening the entire frame; an external `MASK` is the highest-precision production path.
- Joint CIELAB lightness, yellow/blue, and red/green correction with shadow lift, highlight protection, evenness, smoothing, and texture preservation.
- Automatic exact preview runs the same backend algorithm without queuing the video graph. A 1 px line provides an in-node before/after comparison.
- Formal `IMAGE` outputs, including the third preview output, preserve the source resolution. Only the temporary on-screen PNG is resized.
- Same-size batches, memory-saving sequential mode, parallel mode, CPU/GPU selection, and automatic OOM fallback are supported.
- Official `locales/en` and `locales/zh` files plus bilingual custom Canvas controls.
- Optional MediaPipe face/body-skin location hints. Missing packages, models, download errors, or inference errors safely fall back.

Compared with wiring separate mask, grading, smoothing, and preview nodes, this package keeps shared parameters, masking, exact preview, and final processing consistent while reducing dependencies and graph clutter.

## Interface and effect preview

![Complete preset list](docs/assets/presets.png)

![Settings panel and in-node exact comparison](docs/assets/before-after-comparison.png)

| Divider toward the right: more source image | Divider toward the left: more processed result |
|---|---|
| ![Inspecting the source side](docs/assets/before.png) | ![Inspecting the processed side](docs/assets/after.png) |

The project owner created these assets or holds publication rights. The custom settings shown are a functional demonstration; results vary with the input, lighting, and mask. Two authorized clips were combined into a silent side-by-side preview. Their motion is not frame-locked, so it must not be read as a scientific pixel comparison: [download the comparison video](https://github.com/likun199679-bot/ComfyUI-SkinBeauty-CN/releases/download/v2.2.1/skinbeauty-video-comparison.mp4). Images and video were re-encoded and scanned with no workflow, prompt, local path, or software metadata retained; see [`docs/assets/README.md`](docs/assets/README.md).

## Nodes, presets, and controls

`Skin Beauty Settings` can drive multiple processors. Presets are Off, Low Natural Brightening, Medium Natural Cool White, High Translucent Cool White, Cool White Skin, Rosy White, and Creamy White. Presets remain editable.

Complete controls: preset, intensity, whitening, coolness, rosy tone, evenness, shadow lift, highlight protection, saturation, smoothing, texture preservation, skin detection sensitivity, and mask feathering.

`Skin Beauty Process + Preview` accepts an `IMAGE`, shared settings, and optional `MASK`; it returns the corrected image, skin mask, full-resolution preview image, and bilingual report. It exposes automatic/external/full-image mask modes, semantic modes, batch modes, and device selection.

## Installation

### ComfyUI Manager / Registry

After the Registry release is available, search for `skin-beauty-cn` or `ComfyUI-SkinBeauty-CN`. If it is not listed yet, use one of the methods below and do not install an unrelated similarly named package.

### Git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/likun199679-bot/ComfyUI-SkinBeauty-CN.git
```

### Release ZIP

Download `ComfyUI-SkinBeauty-CN_v2.2.1.zip` from [Releases](https://github.com/likun199679-bot/ComfyUI-SkinBeauty-CN/releases), extract it, and verify this layout:

```text
ComfyUI/custom_nodes/ComfyUI-SkinBeauty-CN/__init__.py
```

Restart ComfyUI and press `Ctrl+F5` in the browser. The core path requires no `pip install` command.

## Updating and uninstalling

Back up local modifications, replace the old folder as a whole, restart ComfyUI, and press `Ctrl+F5`; replacing Python only can leave stale JavaScript behind. v2.2.1 preserves node class IDs, Python input keys, internal enum values, and output order for V1/V2.2 workflows.

To uninstall, stop ComfyUI, remove `custom_nodes/ComfyUI-SkinBeauty-CN`, and restart. A model explicitly downloaded by the user remains under `ComfyUI/models/mediapipe/selfie_multiclass_256x256.tflite`; keep or remove it yourself. This project has no uninstall script and never mutates the shared Python environment.

## Workflows

```text
LoadImage --> Skin Beauty Process + Preview --> PreviewImage / downstream
Settings -------------------------------> processor(s)
```

- [`SkinBeauty_Minimal_Pure_Algorithm.json`](workflows/SkinBeauty_Minimal_Pure_Algorithm.json): immediate zero-extra-dependency check.
- [`SkinBeauty_Minimal_Auto_Semantic.json`](workflows/SkinBeauty_Minimal_Auto_Semantic.json): uses local semantic support when present and otherwise falls back without networking.
- [`MiniMax_H3_SkinBeauty_Integration.json`](workflows/MiniMax_H3_SkinBeauty_Integration.json): preserves the V2.2 dual-reference routing and bypass state; see [`DEPENDENCIES.md`](workflows/DEPENDENCIES.md) for third-party nodes.

## Starting point for yellow-to-cool-white correction

Start with Medium Natural Cool White. For strong yellow cast, try coolness 45–65. For brightness only, try whitening 35–55 and coolness 15–35. Raise highlight protection to 75–90 for already bright skin. For pore detail, keep smoothing at or below 15 and texture preservation at 88–96. Reduce skin sensitivity when beige objects are selected; for production, connect a reviewed skin `MASK`.

## Batches, performance, and memory

A ComfyUI `IMAGE` batch requires matching dimensions. Use separate processors sharing one settings node for differently sized references. Sequential processing is the safe default for 3K–5K images. Use parallel mode only for a small same-size batch with known memory headroom. In automatic device mode, a CUDA OOM retries sequentially and then on CPU; explicit GPU mode never silently changes devices.

## Optional MediaPipe: read the risk first

**Do not install MediaPipe unless you need semantic segmentation.** ComfyUI uses a shared Python environment. Manual MediaPipe installation may change NumPy/protobuf and may pull an OpenCV distribution as MediaPipe's own dependency, affecting unrelated nodes. This project never runs pip and neither imports nor directly depends on `cv2`. The optional list is isolated at `extras/requirements-mediapipe.txt`; evaluate it only in a recoverable environment:

```bash
python -m pip install -r extras/requirements-mediapipe.txt
```

The default automatic mode never downloads. Only the explicit “MediaPipe: allow model download only; never installs Python packages” option contacts the fixed HTTPS host for a fixed model version. The downloader enforces a 60-second timeout, 32 MiB limit, `.part` file, SHA256 and load validation, and atomic replacement. It downloads a model only—never Python packages. You may place a verified model manually in `ComfyUI/models/mediapipe/`. Every failure falls back to the pure algorithm and reports a sanitized reason.

## Privacy and network behavior

Core processing, automatic mode, and local-model inference stay on the machine. There is no telemetry or analytics. Only the explicit model-download mode accesses `https://storage.googleapis.com/mediapipe-models/`. The exact-preview endpoint accepts uploads from ComfyUI's `input` directory only and rejects traversal, output paths, and arbitrary file reads.

## Known limitations

- Color-based masking can select beige walls, wood, leather, or clothing; an external skin `MASK` is the most accurate path.
- Lighting, color management, and camera white balance change the appearance of the same settings. Presets are starting points, not a universal aesthetic.
- The lightweight MediaPipe model can miss occluded, extreme-pose, distant, or very small people.
- This is controlled tone and texture processing, not generative face replacement or blemish redrawing.
- Standalone exact preview currently needs an input traceable to `LoadImage`; normal queued processing still accepts any `IMAGE` source.

## Compatibility and verification

| Environment | v2.2.1 status |
|---|---|
| Windows 11 / Python 3.12.10 / Torch 2.9.1+cu130 / RTX 5090 | Local core, CPU/GPU comparison, and MediaPipe 0.10.21 exercised |
| Windows + Ubuntu / Python 3.10, 3.11, 3.12 | GitHub Actions matrix configured for static, JSON, workflow, security, and packaging checks; see public CI runs for results |
| Ubuntu / Python 3.12 / CPU Torch | GitHub Actions algorithm job configured; see public CI runs for results |
| No MediaPipe/model and download/hash/inference failures | Contract and mocked fallback coverage; not misrepresented as physical tests of every environment |

## Troubleshooting

- Node missing: verify there is no extra nested folder, inspect the startup log, and restart. This project has no root `requirements.txt` or `install.py`.
- Stale language/buttons: check the ComfyUI Locale setting and press `Ctrl+F5`.
- MediaPipe fallback: read the bilingual report. Fallback with no local model is expected and does not break the core node.
- Exact preview lacks a source: ensure the `IMAGE` can be traced to `LoadImage`; queued outputs remain functional.
- OOM: use sequential mode, reduce the simultaneous batch, or choose CPU. Do not modify the shared Torch install for this node.

## Attribution, license, and participation

The PyTorch grading pipeline, batching and fallback policies, secure exact-preview endpoint, and Canvas comparer are independently implemented or engineered in this project. YCbCr, sRGB/XYZ/CIELAB, conventional blur/masks, semantic segmentation, and slider comparisons are public techniques; the project does not claim to have invented them and neither copies nor depends on rgthree at runtime. See [`ALGORITHM_AND_ORIGINALITY.md`](docs/ALGORITHM_AND_ORIGINALITY.md), [`ARCHITECTURE.md`](docs/ARCHITECTURE.md), and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

Released under the [MIT License](LICENSE). Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md); use GitHub Issues for ordinary bugs. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SUPPORT.md](SUPPORT.md). The project follows SemVer: compatible fixes are patches, features are minors, and intentional protocol breaks require a major version.
