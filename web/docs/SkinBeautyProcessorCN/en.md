# Skin Beauty Process + Preview

Accepts one image or a same-size `IMAGE` batch and returns the corrected image, skin mask, full-resolution preview image, and bilingual report.

## Masks

- **Automatic skin**: adaptive color mask, optionally fused with existing MediaPipe face/body-skin classes.
- **External mask preferred**: uses the external location while constraining it with skin probability.
- **External mask only**: strictly changes the supplied area and is the most accurate production path.
- **Full-image grading**: intentionally grades the entire frame.

Default automatic semantic mode reuses a valid local model but never downloads. The explicit “MediaPipe: allow model download only; never installs Python packages” mode downloads only the fixed verified model when missing. The plugin never installs packages.

## Preview and batching

Automatic exact preview debounces settings changes for about 0.5 seconds; the manual exact-preview button forces a refresh without submitting the video queue. The approximate browser whitening path has been removed. Move across the large Canvas to control the 1 px before/after divider. UI scaling never resizes any `IMAGE` output.

Sequential mode is the safe default for 3K–5K images. Automatic device mode retries CUDA OOM as sequential processing and then CPU; explicit GPU mode never silently changes devices.
