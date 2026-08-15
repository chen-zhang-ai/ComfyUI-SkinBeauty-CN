"""ComfyUI nodes and the shared full-resolution skin-beauty service."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import torch
import torch.nn.functional as F

from .semantic_mediapipe import segment_skin
from .skin_core import PRESETS, config_dict, config_summary, preset_names, process_images, resolve_config


MASK_MODES = ("自动肤色（推荐）", "外部遮罩优先", "仅外部遮罩", "全图调色")
SEMANTIC_MODES = ("自动：已有模型则使用", "纯算法：零依赖", "MediaPipe：允许首次下载")
BATCH_MODES = ("自动：逐张省显存", "逐张处理", "整批并行")
DEVICE_MODES = ("自动", "GPU", "CPU")


def _message(zh: str, en: str, locale: Optional[str] = None) -> str:
    if locale == "zh":
        return zh
    if locale == "en":
        return en
    return f"{zh} / {en}"


def _slider(default: float, minimum: float, maximum: float, step: float = 1.0) -> Tuple[str, Dict[str, Any]]:
    return ("FLOAT", {"default": default, "min": minimum, "max": maximum, "step": step, "display": "slider"})


class SkinBeautySettingsCN:
    """One shared settings node can drive any number of image processors."""

    @classmethod
    def INPUT_TYPES(cls):
        defaults = resolve_config()
        return {
            "required": {
                "预设": (preset_names(), {"default": defaults.preset}),
                "总强度": _slider(defaults.intensity, 0, 100),
                "美白": _slider(defaults.whitening, 0, 100),
                "冷暖": _slider(defaults.coolness, -100, 100),
                "红润": _slider(defaults.rosy, -50, 50),
                "匀肤": _slider(defaults.evenness, 0, 100),
                "暗部提亮": _slider(defaults.shadow_lift, 0, 100),
                "高光保护": _slider(defaults.highlight_protect, 0, 100),
                "饱和度": _slider(defaults.saturation, -50, 50),
                "平滑": _slider(defaults.smoothing, 0, 100),
                "纹理保留": _slider(defaults.texture_preserve, 0, 100),
                "肤色识别": _slider(defaults.mask_sensitivity, 0, 100),
                "蒙版羽化": _slider(defaults.mask_feather, 0, 64),
            }
        }

    RETURN_TYPES = ("SKIN_BEAUTY_CONFIG", "STRING")
    RETURN_NAMES = ("美白参数", "参数摘要")
    FUNCTION = "make_config"
    CATEGORY = "图像/人物美颜·中文"
    DESCRIPTION = "Shared skin-tone correction settings with presets and fine controls."

    def make_config(
        self,
        预设: str,
        总强度: float,
        美白: float,
        冷暖: float,
        红润: float,
        匀肤: float,
        暗部提亮: float,
        高光保护: float,
        饱和度: float,
        平滑: float,
        纹理保留: float,
        肤色识别: float,
        蒙版羽化: float,
    ):
        config = resolve_config(
            preset=预设,
            intensity=总强度,
            whitening=美白,
            coolness=冷暖,
            rosy=红润,
            evenness=匀肤,
            shadow_lift=暗部提亮,
            highlight_protect=高光保护,
            saturation=饱和度,
            smoothing=平滑,
            texture_preserve=纹理保留,
            mask_sensitivity=肤色识别,
            mask_feather=蒙版羽化,
        )
        payload = config_dict(config)
        payload["preset_values"] = PRESETS.get(预设, {})
        return payload, config_summary(config)


def _models_dir() -> str:
    try:
        import folder_paths

        return folder_paths.models_dir
    except Exception:
        return str(Path.cwd() / "models")


def _select_device(mode: str, image: torch.Tensor) -> torch.device:
    if mode == "CPU":
        return torch.device("cpu")
    if torch.cuda.is_available():
        try:
            import comfy.model_management as model_management

            device = model_management.get_torch_device()
            if mode == "GPU" or (mode == "自动" and image.shape[1] * image.shape[2] >= 512 * 512):
                return device
        except Exception:
            if mode == "GPU" or (mode == "自动" and image.shape[1] * image.shape[2] >= 512 * 512):
                return torch.device("cuda")
    return torch.device("cpu")


def _semantic_for(
    images: torch.Tensor,
    mode: str,
    locale: Optional[str] = None,
) -> Tuple[Optional[torch.Tensor], str]:
    if mode == "纯算法：零依赖":
        return None, _message(
            "纯算法 YCbCr 自适应肤色蒙版",
            "Pure-algorithm adaptive YCbCr skin mask",
            locale,
        )
    # Keep the V2.2 enum value stable.  Official nodeDefs translations expose
    # the clearer "model download only; never installs packages" label.
    allow_download = mode == "MediaPipe：允许首次下载"
    return segment_skin(
        images.detach().cpu(),
        _models_dir(),
        allow_download=allow_download,
        locale=locale,
    )


def _resize_display_preview(image: torch.Tensor, longest: int = 1600) -> torch.Tensor:
    """Build a UI-only thumbnail without changing any IMAGE output tensor."""

    image = image[:1, ..., :3].detach().float().cpu().clamp(0, 1)
    height, width = image.shape[1:3]
    if max(height, width) <= longest:
        return image
    scale = longest / float(max(height, width))
    size = (max(1, round(height * scale)), max(1, round(width * scale)))
    chw = image.permute(0, 3, 1, 2)
    return F.interpolate(chw, size=size, mode="bilinear", align_corners=False).permute(0, 2, 3, 1)


def _save_temp_preview(image: torch.Tensor, unique_id: Any = "preview") -> Dict[str, str]:
    import folder_paths
    import numpy as np
    from PIL import Image

    temp_root = Path(folder_paths.get_temp_directory())
    subfolder = "skinbeauty_cn"
    directory = temp_root / subfolder
    directory.mkdir(parents=True, exist_ok=True)
    now = time.time()
    # Remove only this plug-in's stale previews; user outputs are never touched.
    try:
        for item in directory.glob("skinbeauty_*.png"):
            if now - item.stat().st_mtime > 24 * 60 * 60:
                item.unlink()
    except OSError:
        pass

    safe_id = re.sub(r"[^0-9A-Za-z_-]+", "_", str(unique_id))[:48] or "preview"
    filename = f"skinbeauty_{safe_id}_{time.time_ns()}.png"
    target = directory / filename
    temporary = directory / f".{filename}.{time.time_ns()}.tmp"
    array = (_resize_display_preview(image)[0].numpy() * 255.0 + 0.5).astype(np.uint8)
    try:
        Image.fromarray(array).save(temporary, format="PNG", optimize=True)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return {"filename": filename, "subfolder": subfolder, "type": "temp"}


@dataclass(frozen=True)
class SkinBeautyRun:
    """One canonical result shared by normal execution and exact preview."""

    result: torch.Tensor
    mask: torch.Tensor
    preview: torch.Tensor
    report: str


def run_skin_beauty(
    images: torch.Tensor,
    settings: Dict[str, Any],
    mask_mode: str,
    semantic_mode: str,
    batch_mode: str,
    device_mode: str,
    external_mask: Optional[torch.Tensor] = None,
) -> SkinBeautyRun:
    """Run the full-resolution production path without any display resizing."""

    if mask_mode == "仅外部遮罩" and external_mask is None:
        raise ValueError(
            "蒙版模式为“仅外部遮罩”，但没有连接外部遮罩。 / "
            "Mask mode is 'external mask only', but no external mask is connected."
        )

    config = resolve_config(settings)
    if mask_mode in ("仅外部遮罩", "全图调色") or (mask_mode == "外部遮罩优先" and external_mask is not None):
        semantic, semantic_report = None, _message(
            "当前蒙版模式不需要语义模型",
            "The selected mask mode does not require a semantic model",
        )
    else:
        semantic, semantic_report = _semantic_for(images, semantic_mode)

    preferred_device = _select_device(device_mode, images)
    preferred_sequential = batch_mode != "整批并行"
    attempts = [(preferred_device, preferred_sequential, "")]
    if preferred_device.type == "cuda" and not preferred_sequential:
        attempts.append((preferred_device, True, _message(
            "整批显存不足，已自动改为逐张处理",
            "Batch GPU memory was insufficient; switched to sequential processing",
        )))
    if preferred_device.type == "cuda" and device_mode == "自动":
        attempts.append((torch.device("cpu"), True, _message(
            "GPU 显存不足，已自动回退 CPU 逐张处理",
            "GPU memory was insufficient; fell back to sequential CPU processing",
        )))

    result = mask = None
    fallback_report = ""
    device = preferred_device
    sequential = preferred_sequential
    for attempt_device, attempt_sequential, attempt_report in attempts:
        try:
            work_image = images.to(device=attempt_device, dtype=torch.float32)
            work_external = external_mask.to(device=attempt_device, dtype=torch.float32) if external_mask is not None else None
            work_semantic = semantic.to(device=attempt_device, dtype=torch.float32) if semantic is not None else None
            result, mask = process_images(
                work_image,
                config,
                mask_mode=mask_mode,
                external_mask=work_external,
                semantic_mask=work_semantic,
                sequential=attempt_sequential,
            )
            device = attempt_device
            sequential = attempt_sequential
            fallback_report = attempt_report
            break
        except RuntimeError as exc:
            if attempt_device.type != "cuda" or "out of memory" not in str(exc).lower():
                raise
            work_image = work_external = work_semantic = None
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass
    if result is None or mask is None:
        raise RuntimeError(
            "人物肤色美白显存不足；请使用逐张处理、缩小参考图或改用 CPU。 / "
            "Skin-beauty processing ran out of memory; use sequential mode, a smaller image, or CPU."
        )

    result = result.detach().cpu()
    mask = mask.detach().cpu()
    # This is an IMAGE output alias, not a screen thumbnail. Display resizing
    # happens only when a private temporary PNG is encoded below.
    preview = result
    report_zh = (
        f"{config_summary(config, 'zh')}\n"
        f"蒙版：{semantic_report}｜模式：{mask_mode}\n"
        f"批次：{result.shape[0]} 张，{result.shape[2]}×{result.shape[1]}｜"
        f"处理：{'逐张省显存' if sequential else '整批并行'}｜设备：{device}"
        f"{('｜' + fallback_report) if fallback_report else ''}"
    )
    report_en = (
        f"{config_summary(config, 'en')}\n"
        f"Mask: {semantic_report} | internal mode: {mask_mode}\n"
        f"Batch: {result.shape[0]} image(s), {result.shape[2]}×{result.shape[1]} | "
        f"processing: {'sequential' if sequential else 'parallel batch'} | device: {device}"
        f"{(' | ' + fallback_report) if fallback_report else ''}"
    )
    return SkinBeautyRun(result, mask, preview, f"{report_zh}\n{report_en}")


class SkinBeautyProcessorCN:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图像": ("IMAGE",),
                "美白参数": ("SKIN_BEAUTY_CONFIG",),
                "蒙版模式": (MASK_MODES, {"default": MASK_MODES[0]}),
                "语义蒙版": (SEMANTIC_MODES, {"default": SEMANTIC_MODES[0]}),
                "批处理": (BATCH_MODES, {"default": BATCH_MODES[0]}),
                "计算设备": (DEVICE_MODES, {"default": DEVICE_MODES[0]}),
                "生成节点预览": ("BOOLEAN", {"default": True}),
                "实时精确预览": ("BOOLEAN", {"default": True}),
            },
            "optional": {"外部遮罩": ("MASK",)},
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("IMAGE", "MASK", "IMAGE", "STRING")
    RETURN_NAMES = ("美白图像", "肤色蒙版", "预览图", "处理报告")
    FUNCTION = "process"
    CATEGORY = "图像/人物美颜·中文"
    DESCRIPTION = "Adjusts detected skin while preserving full-resolution IMAGE batches and optional masks."

    def process(
        self,
        图像: torch.Tensor,
        美白参数: Dict[str, Any],
        蒙版模式: str,
        语义蒙版: str,
        批处理: str,
        计算设备: str,
        生成节点预览: bool,
        实时精确预览: bool,
        外部遮罩: Optional[torch.Tensor] = None,
        unique_id: Any = "preview",
    ):
        run = run_skin_beauty(
            图像,
            美白参数,
            蒙版模式,
            语义蒙版,
            批处理,
            计算设备,
            外部遮罩,
        )
        result, mask, preview, report = run.result, run.mask, run.preview, run.report
        output = (result, mask, preview, report)
        if 生成节点预览:
            # Use a private UI key so ComfyUI does not append its standard image
            # gallery below our embedded before/after comparer.
            return {
                "ui": {
                    "skin_beauty_before": [_save_temp_preview(图像, f"{unique_id}_before")],
                    "skin_beauty_preview": [_save_temp_preview(result, f"{unique_id}_after")],
                },
                "result": output,
            }
        return output


class SkinBeautyPreviewSinkCN:
    """Dev-only output target injected into API prompts by the web extension."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "before": ("IMAGE",),
                "after": ("IMAGE",),
                "request_id": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "save_preview"
    CATEGORY = "_internal/skinbeauty_cn"
    DESCRIPTION = "Internal exact-preview output. Hidden unless ComfyUI developer mode is enabled."
    OUTPUT_NODE = True
    DEV_ONLY = True

    def save_preview(self, before: torch.Tensor, after: torch.Tensor, request_id: str):
        return {
            "ui": {
                "skin_beauty_before": [_save_temp_preview(before, f"{request_id}_before")],
                "skin_beauty_preview": [_save_temp_preview(after, f"{request_id}_after")],
                "skin_beauty_request": [str(request_id)],
            },
            "result": (),
        }


NODE_CLASS_MAPPINGS = {
    "SkinBeautySettingsCN": SkinBeautySettingsCN,
    "SkinBeautyProcessorCN": SkinBeautyProcessorCN,
    "SkinBeautyPreviewSinkCN": SkinBeautyPreviewSinkCN,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SkinBeautySettingsCN": "Skin Beauty | Settings",
    "SkinBeautyProcessorCN": "Skin Beauty | Process + Preview",
    "SkinBeautyPreviewSinkCN": "Skin Beauty | Internal Preview Sink",
}
