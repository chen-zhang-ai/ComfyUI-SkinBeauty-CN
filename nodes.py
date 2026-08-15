"""ComfyUI nodes and the lightweight exact-preview HTTP endpoint."""

from __future__ import annotations

import json
import os
import re
import time
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
    DESCRIPTION = "共享人物肤色美白参数。低/中/高档可一键套用，随后可继续微调。"

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


def _semantic_for(images: torch.Tensor, mode: str) -> Tuple[Optional[torch.Tensor], str]:
    if mode == "纯算法：零依赖":
        return None, "轻量 YCbCr 自适应肤色蒙版"
    allow_download = mode == "MediaPipe：允许首次下载"
    return segment_skin(images.detach().cpu(), _models_dir(), allow_download=allow_download)


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
    array = (_resize_display_preview(image)[0].numpy() * 255.0 + 0.5).astype(np.uint8)
    Image.fromarray(array, mode="RGB").save(directory / filename, format="PNG", optimize=True)
    return {"filename": filename, "subfolder": subfolder, "type": "temp"}


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
    DESCRIPTION = "只调整识别到的人物皮肤；支持 IMAGE 批次、外部遮罩和独立预览。"

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
        config = resolve_config(美白参数)
        if 蒙版模式 in ("仅外部遮罩", "全图调色") or (蒙版模式 == "外部遮罩优先" and 外部遮罩 is not None):
            semantic, semantic_report = None, "当前蒙版模式不需要语义模型"
        else:
            semantic, semantic_report = _semantic_for(图像, 语义蒙版)
        preferred_device = _select_device(计算设备, 图像)
        preferred_sequential = 批处理 != "整批并行"
        attempts = [(preferred_device, preferred_sequential, "")]
        if preferred_device.type == "cuda" and not preferred_sequential:
            attempts.append((preferred_device, True, "整批显存不足，已自动改为逐张处理"))
        if preferred_device.type == "cuda" and 计算设备 == "自动":
            attempts.append((torch.device("cpu"), True, "GPU 显存不足，已自动回退 CPU 逐张处理"))

        last_oom_text = ""
        result = mask = None
        fallback_report = ""
        device = preferred_device
        sequential = preferred_sequential
        for attempt_device, attempt_sequential, attempt_report in attempts:
            try:
                work_image = 图像.to(device=attempt_device, dtype=torch.float32)
                work_external = 外部遮罩.to(device=attempt_device, dtype=torch.float32) if 外部遮罩 is not None else None
                work_semantic = semantic.to(device=attempt_device, dtype=torch.float32) if semantic is not None else None
                result, mask = process_images(
                    work_image,
                    config,
                    mask_mode=蒙版模式,
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
                last_oom_text = str(exc)
                work_image = work_external = work_semantic = None
                try:
                    torch.cuda.empty_cache()
                except Exception:
                    pass
        if result is None or mask is None:
            raise RuntimeError(
                "人物肤色美白处理显存不足；请使用“逐张处理”、缩小参考图，或将计算设备改为 CPU。"
                f"底层信息：{last_oom_text}"
            )
        result = result.detach().cpu()
        mask = mask.detach().cpu()
        # The third IMAGE output deliberately keeps the full spatial resolution.
        # Only the temporary UI PNG is resized by _save_temp_preview().
        preview = result

        report = (
            f"{config_summary(config)}\n"
            f"蒙版：{semantic_report}｜模式：{蒙版模式}\n"
            f"批次：{result.shape[0]} 张，{result.shape[2]}×{result.shape[1]}｜"
            f"处理：{'逐张省显存' if sequential else '整批并行'}｜设备：{device}"
            f"{('｜' + fallback_report) if fallback_report else ''}"
        )
        output = (result, mask, preview, report)
        if 生成节点预览:
            # Use a private UI key so ComfyUI does not append its standard image
            # gallery below our embedded before/after comparer.
            return {"ui": {"skin_beauty_preview": [_save_temp_preview(result, unique_id)]}, "result": output}
        return output


def _resolve_input_image(source: Dict[str, Any]) -> str:
    """Resolve only a ComfyUI input image; reject traversal and output paths."""

    import folder_paths

    if source.get("type", "input") not in ("input", "upload"):
        raise ValueError("精确预览只读取 ComfyUI input 目录中的上传图")
    filename = os.path.basename(str(source.get("filename", "")))
    subfolder = str(source.get("subfolder", "")).replace("\\", "/").strip("/")
    if not filename:
        raise ValueError("没有找到上游 LoadImage 文件名")
    root = os.path.realpath(folder_paths.get_input_directory())
    candidate = os.path.realpath(os.path.join(root, subfolder, filename))
    if os.path.commonpath((root, candidate)) != root or not os.path.isfile(candidate):
        raise ValueError("预览源图不存在或路径无效")
    return candidate


def _register_preview_route() -> None:
    try:
        from aiohttp import web
        from server import PromptServer
    except Exception:
        return

    prompt_server = PromptServer.instance
    if prompt_server is None:
        return
    if getattr(prompt_server, "_skinbeauty_cn_route", False):
        return

    @prompt_server.routes.post("/skin_beauty_cn/preview")
    async def preview(request):
        try:
            from PIL import Image, ImageOps
            import numpy as np

            payload = await request.json()
            source_path = _resolve_input_image(payload.get("source") or {})
            with Image.open(source_path) as opened:
                pil_image = ImageOps.exif_transpose(opened).convert("RGB")
                # UI-only exact preview. 1600 px stays responsive while giving
                # a crisp image when the user enlarges the node.
                pil_image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                array = np.asarray(pil_image).astype("float32") / 255.0
            images = torch.from_numpy(array).unsqueeze(0)
            config = resolve_config(payload.get("config") or {})
            semantic_mode = str(payload.get("semantic_mode", SEMANTIC_MODES[0]))
            semantic, semantic_report = _semantic_for(images, semantic_mode)
            device = _select_device(str(payload.get("device", "自动")), images)
            result, _ = process_images(
                images.to(device),
                config,
                mask_mode=str(payload.get("mask_mode", MASK_MODES[0])),
                semantic_mask=semantic.to(device) if semantic is not None else None,
                sequential=True,
            )
            image_info = _save_temp_preview(result.cpu(), payload.get("node_id", "exact"))
            return web.json_response(
                {"ok": True, "image": image_info, "report": f"{config_summary(config)}｜{semantic_report}"}
            )
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)

    prompt_server._skinbeauty_cn_route = True


_register_preview_route()


NODE_CLASS_MAPPINGS = {
    "SkinBeautySettingsCN": SkinBeautySettingsCN,
    "SkinBeautyProcessorCN": SkinBeautyProcessorCN,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SkinBeautySettingsCN": "人物肤色美白｜参数面板（中文）",
    "SkinBeautyProcessorCN": "人物肤色美白｜处理＋预览（中文）",
}
