# Algorithm and originality / 算法与原创范围

## Processing pipeline

1. Validate a BHWC ComfyUI image and preserve alpha/extra channels separately.
2. Build a soft location mask from an external `MASK`, optional MediaPipe face/body-skin classes, or an adaptive YCbCr skin-color probability. Semantic location is multiplied by a color constraint to reject many clothing/background false positives.
3. Convert sRGB through linear RGB and D65 XYZ to CIELAB.
4. Increase L* with shadow-aware lift and highlight protection; adjust b* toward cooler/less-yellow values and a* for controlled rosy tone; apply restrained chroma scaling.
5. Use masked local averages for evenness/smoothing, with an explicit texture-preservation term.
6. Convert to sRGB, blend only through the soft mask and global intensity, restore extra channels, and return the original height and width.

The fallback mask is deliberately probabilistic, not a claim of semantic understanding. It can confuse skin-like materials. MediaPipe improves location but remains lightweight and fallible. A reviewed external skin mask is the professional accuracy path.

## Independently implemented scope

This project independently implements the PyTorch tensor pipeline, preset/config model, mask fusion, sequential/parallel batching, device and OOM fallback, fixed-model download hardening, safe preview endpoint, exact-preview protocol, bilingual integration, workflow preservation tests, and native Canvas comparer. “Independent” describes this repository's code and engineering combination; it does not claim invention of the underlying scientific concepts.

## Public and third-party foundations

- YCbCr-like chroma skin heuristics, sRGB transfer functions, D65 XYZ/CIELAB formulas, pooling/blur, smoothstep, masks, and interpolation are standard color-science or image-processing techniques.
- Semantic image segmentation and MediaPipe's face/body-skin model are Google/MediaPipe technology and are not authored or redistributed here.
- An overlaid before/after image with a movable divider is a common UI pattern. ComfyUI ImageCompare and rgthree Image Comparer were design references; their source was not copied and rgthree is not a runtime dependency of this comparer.

See `THIRD_PARTY_NOTICES.md` for links and `OPEN_SOURCE_RESEARCH.md` for the alternatives considered.
