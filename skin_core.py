"""Pure PyTorch skin-tone correction used by the ComfyUI nodes.

The module intentionally has no dependencies beyond PyTorch.  Semantic masks
can be supplied by the optional MediaPipe adapter or by another ComfyUI node.
Images use ComfyUI's BHWC float convention in the public functions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Dict, Mapping, Optional, Tuple

import torch
import torch.nn.functional as F


@dataclass(frozen=True)
class BeautyConfig:
    preset: str = "中档·自然冷白"
    intensity: float = 72.0
    whitening: float = 52.0
    coolness: float = 42.0
    rosy: float = 8.0
    evenness: float = 28.0
    shadow_lift: float = 18.0
    highlight_protect: float = 72.0
    saturation: float = -8.0
    smoothing: float = 12.0
    texture_preserve: float = 88.0
    mask_sensitivity: float = 58.0
    mask_feather: float = 12.0


PRESETS: Dict[str, Dict[str, float]] = {
    "关闭": {
        "intensity": 0,
        "whitening": 0,
        "coolness": 0,
        "rosy": 0,
        "evenness": 0,
        "shadow_lift": 0,
        "highlight_protect": 80,
        "saturation": 0,
        "smoothing": 0,
        "texture_preserve": 100,
        "mask_sensitivity": 58,
        "mask_feather": 12,
    },
    "低档·自然提亮": {
        "intensity": 48,
        "whitening": 34,
        "coolness": 20,
        "rosy": 5,
        "evenness": 16,
        "shadow_lift": 10,
        "highlight_protect": 78,
        "saturation": -4,
        "smoothing": 6,
        "texture_preserve": 94,
        "mask_sensitivity": 56,
        "mask_feather": 10,
    },
    "中档·自然冷白": {
        "intensity": 72,
        "whitening": 52,
        "coolness": 42,
        "rosy": 8,
        "evenness": 28,
        "shadow_lift": 18,
        "highlight_protect": 72,
        "saturation": -8,
        "smoothing": 12,
        "texture_preserve": 88,
        "mask_sensitivity": 58,
        "mask_feather": 12,
    },
    "高档·通透冷白": {
        "intensity": 88,
        "whitening": 70,
        "coolness": 62,
        "rosy": 10,
        "evenness": 42,
        "shadow_lift": 28,
        "highlight_protect": 66,
        "saturation": -13,
        "smoothing": 20,
        "texture_preserve": 82,
        "mask_sensitivity": 60,
        "mask_feather": 14,
    },
    "冷白皮": {
        "intensity": 82,
        "whitening": 62,
        "coolness": 68,
        "rosy": 4,
        "evenness": 34,
        "shadow_lift": 20,
        "highlight_protect": 74,
        "saturation": -12,
        "smoothing": 10,
        "texture_preserve": 91,
        "mask_sensitivity": 58,
        "mask_feather": 12,
    },
    "粉润白": {
        "intensity": 76,
        "whitening": 56,
        "coolness": 30,
        "rosy": 28,
        "evenness": 34,
        "shadow_lift": 18,
        "highlight_protect": 72,
        "saturation": -4,
        "smoothing": 15,
        "texture_preserve": 86,
        "mask_sensitivity": 58,
        "mask_feather": 12,
    },
    "奶油白": {
        "intensity": 74,
        "whitening": 60,
        "coolness": 8,
        "rosy": 12,
        "evenness": 38,
        "shadow_lift": 24,
        "highlight_protect": 68,
        "saturation": -10,
        "smoothing": 18,
        "texture_preserve": 84,
        "mask_sensitivity": 57,
        "mask_feather": 13,
    },
}


def preset_names() -> Tuple[str, ...]:
    return ("自定义", *PRESETS.keys())


def resolve_config(value: Optional[Mapping[str, Any]] = None, **overrides: Any) -> BeautyConfig:
    """Create a validated immutable config.

    Preset values are used as a safe fallback.  Widget values are still kept
    authoritative so the frontend can populate a preset and then let a user
    fine-tune it without changing the backend protocol.
    """

    raw: Dict[str, Any] = asdict(BeautyConfig())
    if value:
        raw.update(dict(value))
    raw.update({key: val for key, val in overrides.items() if val is not None})

    allowed = {field.name for field in fields(BeautyConfig)}
    raw = {key: val for key, val in raw.items() if key in allowed}
    preset = str(raw.get("preset", BeautyConfig.preset))
    raw["preset"] = preset if preset in preset_names() else "自定义"

    bounds = {
        "intensity": (0, 100),
        "whitening": (0, 100),
        "coolness": (-100, 100),
        "rosy": (-50, 50),
        "evenness": (0, 100),
        "shadow_lift": (0, 100),
        "highlight_protect": (0, 100),
        "saturation": (-50, 50),
        "smoothing": (0, 100),
        "texture_preserve": (0, 100),
        "mask_sensitivity": (0, 100),
        "mask_feather": (0, 64),
    }
    for key, (low, high) in bounds.items():
        try:
            raw[key] = min(high, max(low, float(raw[key])))
        except (TypeError, ValueError, KeyError):
            raw[key] = getattr(BeautyConfig(), key)
    return BeautyConfig(**raw)


def config_dict(config: BeautyConfig) -> Dict[str, Any]:
    return asdict(config)


def _smoothstep(edge0: float, edge1: float, value: torch.Tensor) -> torch.Tensor:
    if edge1 <= edge0:
        return (value >= edge1).to(value.dtype)
    x = ((value - edge0) / (edge1 - edge0)).clamp(0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def _srgb_to_linear(rgb: torch.Tensor) -> torch.Tensor:
    return torch.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055).pow(2.4))


def _linear_to_srgb(rgb: torch.Tensor) -> torch.Tensor:
    rgb = rgb.clamp_min(0.0)
    return torch.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * rgb.pow(1.0 / 2.4) - 0.055)


def rgb_to_lab(rgb: torch.Tensor) -> torch.Tensor:
    """Convert BCHW sRGB [0,1] to CIE Lab (D65)."""

    rgb = _srgb_to_linear(rgb.clamp(0.0, 1.0))
    r, g, b = rgb[:, 0:1], rgb[:, 1:2], rgb[:, 2:3]
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b
    x, y, z = x / 0.95047, y, z / 1.08883

    delta = 6.0 / 29.0
    threshold = delta**3
    scale = 1.0 / (3.0 * delta * delta)

    def f(channel: torch.Tensor) -> torch.Tensor:
        return torch.where(channel > threshold, channel.clamp_min(0.0).pow(1.0 / 3.0), scale * channel + 4.0 / 29.0)

    fx, fy, fz = f(x), f(y), f(z)
    return torch.cat((116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz)), dim=1)


def lab_to_rgb(lab: torch.Tensor) -> torch.Tensor:
    """Convert BCHW CIE Lab (D65) to sRGB [0,1]."""

    light, a, b = lab[:, 0:1], lab[:, 1:2], lab[:, 2:3]
    fy = (light + 16.0) / 116.0
    fx = fy + a / 500.0
    fz = fy - b / 200.0
    delta = 6.0 / 29.0

    def inv_f(channel: torch.Tensor) -> torch.Tensor:
        return torch.where(channel > delta, channel.pow(3.0), 3.0 * delta * delta * (channel - 4.0 / 29.0))

    x = 0.95047 * inv_f(fx)
    y = inv_f(fy)
    z = 1.08883 * inv_f(fz)
    r = 3.2404542 * x - 1.5371385 * y - 0.4985314 * z
    g = -0.9692660 * x + 1.8760108 * y + 0.0415560 * z
    blue = 0.0556434 * x - 0.2040259 * y + 1.0572252 * z
    return _linear_to_srgb(torch.cat((r, g, blue), dim=1)).clamp(0.0, 1.0)


def _resize_limit(value: torch.Tensor, longest: int = 1024) -> Tuple[torch.Tensor, Tuple[int, int]]:
    height, width = value.shape[-2:]
    if max(height, width) <= longest:
        return value, (height, width)
    scale = longest / float(max(height, width))
    size = (max(1, round(height * scale)), max(1, round(width * scale)))
    return F.interpolate(value, size=size, mode="bilinear", align_corners=False), (height, width)


def _soft_blur(value: torch.Tensor, radius: float, longest: int = 1280) -> torch.Tensor:
    if radius <= 0.1:
        return value
    small, original_size = _resize_limit(value, longest)
    scale = small.shape[-1] / float(value.shape[-1])
    kernel = int(round(max(1.0, radius * scale))) * 2 + 1
    kernel = min(kernel, 63)
    for _ in range(3):
        small = F.avg_pool2d(small, kernel, stride=1, padding=kernel // 2)
    if small.shape[-2:] != original_size:
        small = F.interpolate(small, size=original_size, mode="bilinear", align_corners=False)
    return small


def automatic_skin_mask(rgb: torch.Tensor, sensitivity: float = 58.0) -> torch.Tensor:
    """Return a soft, adaptive skin-colour mask for BCHW RGB.

    It is a lightweight fallback, not semantic segmentation.  The YCbCr model
    is deliberately soft so an external/semantic mask can refine it without
    hard edges or holes in very pale skin.
    """

    r, g, b = rgb[:, 0:1], rgb[:, 1:2], rgb[:, 2:3]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = 0.5 - 0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 0.5 + 0.5 * r - 0.418688 * g - 0.081312 * b
    maximum = rgb.max(dim=1, keepdim=True).values
    minimum = rgb.min(dim=1, keepdim=True).values
    saturation = (maximum - minimum) / maximum.clamp_min(1e-4)

    sensitivity_scale = 0.82 + 0.55 * (float(sensitivity) / 100.0)
    cb_sigma = 0.090 * sensitivity_scale
    cr_sigma = 0.115 * sensitivity_scale
    chroma = torch.exp(-0.5 * ((cb - 0.435) / cb_sigma).pow(2) - 0.5 * ((cr - 0.595) / cr_sigma).pow(2))
    red_bias = torch.sigmoid((r - b + 0.015) * 18.0)
    green_guard = torch.sigmoid((r - g + 0.085) * 17.0)
    luma_gate = torch.sigmoid((y - 0.035) * 35.0) * torch.sigmoid((0.995 - y) * 35.0)
    saturation_gate = 0.30 + 0.70 * torch.sigmoid((saturation - 0.018) * 45.0)
    score = chroma * (0.38 + 0.62 * red_bias) * (0.45 + 0.55 * green_guard) * luma_gate * saturation_gate

    low = 0.24 - 0.10 * (float(sensitivity) / 100.0)
    high = 0.66 - 0.17 * (float(sensitivity) / 100.0)
    mask = _smoothstep(low, high, score)
    # Close small holes before feathering.  Kernel size scales gently with image resolution.
    kernel = 5 if max(rgb.shape[-2:]) < 2400 else 7
    mask = F.max_pool2d(mask, kernel, stride=1, padding=kernel // 2)
    mask = -F.max_pool2d(-mask, kernel, stride=1, padding=kernel // 2)
    return mask.clamp(0.0, 1.0)


def normalize_mask(mask: torch.Tensor, batch: int, height: int, width: int, device: torch.device) -> torch.Tensor:
    if mask.ndim == 2:
        mask = mask.unsqueeze(0).unsqueeze(0)
    elif mask.ndim == 3:
        mask = mask.unsqueeze(1)
    elif mask.ndim == 4 and mask.shape[-1] == 1:
        mask = mask.permute(0, 3, 1, 2)
    elif mask.ndim != 4:
        raise ValueError(f"不支持的遮罩形状: {tuple(mask.shape)}")
    mask = mask.to(device=device, dtype=torch.float32)
    if mask.shape[0] == 1 and batch > 1:
        mask = mask.expand(batch, -1, -1, -1)
    elif mask.shape[0] != batch:
        raise ValueError(f"遮罩批次数 {mask.shape[0]} 与图像批次数 {batch} 不一致")
    if mask.shape[-2:] != (height, width):
        mask = F.interpolate(mask, size=(height, width), mode="bilinear", align_corners=False)
    return mask[:, :1].clamp(0.0, 1.0)


def build_mask(
    rgb: torch.Tensor,
    config: BeautyConfig,
    mask_mode: str,
    external_mask: Optional[torch.Tensor] = None,
    semantic_mask: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    batch, _, height, width = rgb.shape

    ext = None
    if external_mask is not None:
        ext = normalize_mask(external_mask, batch, height, width, rgb.device)
    sem = None
    if semantic_mask is not None:
        sem = normalize_mask(semantic_mask, batch, height, width, rgb.device)

    if mask_mode == "全图调色":
        mask = torch.ones((batch, 1, height, width), device=rgb.device, dtype=rgb.dtype)
    elif mask_mode == "仅外部遮罩":
        if ext is None:
            raise ValueError("遮罩模式为“仅外部遮罩”，但没有连接外部遮罩")
        mask = ext
    else:
        auto = automatic_skin_mask(rgb, config.mask_sensitivity)
        if mask_mode == "外部遮罩优先" and ext is not None:
            mask = ext * (0.25 + 0.75 * auto)
        elif sem is not None:
            # Semantic classes provide location; colour probability rejects most false positives.
            mask = sem * (0.30 + 0.70 * auto)
        else:
            mask = auto

    return _soft_blur(mask, config.mask_feather).clamp(0.0, 1.0)


def _masked_local_average(lab: torch.Tensor, mask: torch.Tensor, amount: float) -> torch.Tensor:
    if amount <= 0.001:
        return lab
    small_lab, original_size = _resize_limit(lab, 768)
    small_mask = F.interpolate(mask, size=small_lab.shape[-2:], mode="bilinear", align_corners=False)
    radius = max(2, int(round(4 + 15 * amount)))
    kernel = radius * 2 + 1
    weighted = small_lab * small_mask
    for _ in range(2):
        weighted = F.avg_pool2d(weighted, kernel, stride=1, padding=kernel // 2)
        small_mask = F.avg_pool2d(small_mask, kernel, stride=1, padding=kernel // 2)
    average = weighted / small_mask.clamp_min(1e-3)
    if average.shape[-2:] != original_size:
        average = F.interpolate(average, size=original_size, mode="bilinear", align_corners=False)
    return average


def whiten_rgb(rgb: torch.Tensor, mask: torch.Tensor, config: BeautyConfig) -> torch.Tensor:
    """Apply a restrained cool-white correction to BCHW RGB."""

    if config.intensity <= 0.0:
        return rgb
    lab = rgb_to_lab(rgb)
    light, a, b = lab[:, 0:1], lab[:, 1:2], lab[:, 2:3]

    whitening = config.whitening / 100.0
    coolness = config.coolness / 100.0
    rosy = config.rosy / 50.0
    highlight = config.highlight_protect / 100.0
    shadow = config.shadow_lift / 100.0

    highlight_zone = _smoothstep(68.0, 96.0, light)
    lift_guard = 1.0 - 0.78 * highlight * highlight_zone
    light_target = light + whitening * 12.0 * lift_guard
    light_target = light_target + shadow * 7.0 * (1.0 - light / 100.0).clamp(0.0, 1.0).pow(2)
    a_target = a + rosy * 4.5
    b_target = b - coolness * 10.0

    chroma_scale = 1.0 + (config.saturation / 100.0) * 0.45
    a_target = a_target * chroma_scale
    b_target = b_target * chroma_scale
    target = torch.cat((light_target.clamp(0.0, 100.0), a_target, b_target), dim=1)

    evenness = config.evenness / 100.0
    smoothing = config.smoothing / 100.0
    if evenness > 0.001 or smoothing > 0.001:
        local = _masked_local_average(target, mask, max(evenness, smoothing))
        # Evenness mostly normalises colour; it only nudges luminance.
        target[:, 0:1] = torch.lerp(target[:, 0:1], local[:, 0:1], evenness * 0.14)
        target[:, 1:3] = torch.lerp(target[:, 1:3], local[:, 1:3], evenness * 0.36)
        detail_loss = smoothing * (1.0 - 0.86 * config.texture_preserve / 100.0)
        target = torch.lerp(target, local, detail_loss * 0.34)

    corrected = lab_to_rgb(target)
    blend = mask * (config.intensity / 100.0)
    return torch.lerp(rgb, corrected, blend).clamp(0.0, 1.0)


def process_images(
    images: torch.Tensor,
    config: BeautyConfig,
    mask_mode: str = "自动肤色（推荐）",
    external_mask: Optional[torch.Tensor] = None,
    semantic_mask: Optional[torch.Tensor] = None,
    sequential: bool = True,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Process a ComfyUI BHWC image batch and return BHWC image + BHW mask."""

    if images.ndim != 4 or images.shape[-1] < 3:
        raise ValueError(f"图像必须是 ComfyUI BHWC 张量，当前形状: {tuple(images.shape)}")
    original_device = images.device
    rgb = images[..., :3].to(dtype=torch.float32).permute(0, 3, 1, 2).contiguous()
    alpha_or_extra = images[..., 3:] if images.shape[-1] > 3 else None

    if not sequential or rgb.shape[0] == 1:
        mask = build_mask(rgb, config, mask_mode, external_mask, semantic_mask)
        result = whiten_rgb(rgb, mask, config)
    else:
        result_items = []
        mask_items = []
        for index in range(rgb.shape[0]):
            ext_item = external_mask[index : index + 1] if external_mask is not None and external_mask.ndim >= 3 and external_mask.shape[0] > 1 else external_mask
            sem_item = semantic_mask[index : index + 1] if semantic_mask is not None and semantic_mask.ndim >= 3 and semantic_mask.shape[0] > 1 else semantic_mask
            item_mask = build_mask(rgb[index : index + 1], config, mask_mode, ext_item, sem_item)
            result_items.append(whiten_rgb(rgb[index : index + 1], item_mask, config))
            mask_items.append(item_mask)
        result = torch.cat(result_items, dim=0)
        mask = torch.cat(mask_items, dim=0)

    result_bhwc = result.permute(0, 2, 3, 1).to(device=original_device, dtype=images.dtype)
    if alpha_or_extra is not None:
        result_bhwc = torch.cat((result_bhwc, alpha_or_extra), dim=-1)
    return result_bhwc, mask[:, 0].to(device=original_device, dtype=torch.float32)


def config_summary(config: BeautyConfig, locale: Optional[str] = None) -> str:
    zh = (
        f"{config.preset}｜总强度 {config.intensity:.0f}｜美白 {config.whitening:.0f}｜"
        f"冷暖 {config.coolness:+.0f}｜红润 {config.rosy:+.0f}｜匀肤 {config.evenness:.0f}｜"
        f"平滑 {config.smoothing:.0f}｜纹理保留 {config.texture_preserve:.0f}"
    )
    en = (
        f"{config.preset} | intensity {config.intensity:.0f} | whitening {config.whitening:.0f} | "
        f"coolness {config.coolness:+.0f} | rosy {config.rosy:+.0f} | evenness {config.evenness:.0f} | "
        f"smoothing {config.smoothing:.0f} | texture {config.texture_preserve:.0f}"
    )
    if locale == "zh":
        return zh
    if locale == "en":
        return en
    return f"{zh}\n{en}"
