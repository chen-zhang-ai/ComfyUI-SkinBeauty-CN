"""Optional MediaPipe face/body skin segmentation.

Nothing in this module is imported until the user selects a semantic mode, so
the node pack remains usable with only ComfyUI's existing dependencies.
"""

from __future__ import annotations

import os
import threading
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

import torch
import torch.nn.functional as F


MODEL_NAME = "selfie_multiclass_256x256.tflite"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/image_segmenter/"
    "selfie_multiclass_256x256/float32/latest/"
    + MODEL_NAME
)
_LOCK = threading.Lock()
_SEGMENTER = None
_SEGMENTER_PATH: Optional[str] = None


def default_model_path(models_dir: str) -> str:
    return str(Path(models_dir) / "mediapipe" / MODEL_NAME)


def status(models_dir: str) -> Tuple[bool, str]:
    try:
        import mediapipe  # noqa: F401
    except Exception as exc:
        return False, f"未安装 mediapipe（自动使用轻量肤色算法）：{exc.__class__.__name__}"
    path = default_model_path(models_dir)
    if not os.path.isfile(path):
        return False, f"未找到语义模型 {path}（自动使用轻量肤色算法）"
    return True, "MediaPipe 人脸＋身体皮肤语义蒙版"


def ensure_model(models_dir: str, allow_download: bool) -> Optional[str]:
    path = default_model_path(models_dir)
    if os.path.isfile(path):
        return path
    if not allow_download:
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".part"
    try:
        urllib.request.urlretrieve(MODEL_URL, temporary)
        os.replace(temporary, path)
        return path
    except Exception:
        try:
            if os.path.exists(temporary):
                os.remove(temporary)
        except OSError:
            pass
        return None


def _get_segmenter(path: str):
    global _SEGMENTER, _SEGMENTER_PATH
    with _LOCK:
        if _SEGMENTER is not None and _SEGMENTER_PATH == path:
            return _SEGMENTER
        import mediapipe as mp

        options = mp.tasks.vision.ImageSegmenterOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=path),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            output_confidence_masks=True,
            output_category_mask=False,
        )
        _SEGMENTER = mp.tasks.vision.ImageSegmenter.create_from_options(options)
        _SEGMENTER_PATH = path
        return _SEGMENTER


def segment_skin(images: torch.Tensor, models_dir: str, allow_download: bool = False) -> Tuple[Optional[torch.Tensor], str]:
    """Segment face skin + body skin and return a BHW float mask."""

    try:
        import mediapipe as mp
        import numpy as np
    except Exception as exc:
        return None, f"MediaPipe 不可用，已回退轻量算法：{exc.__class__.__name__}"

    path = ensure_model(models_dir, allow_download)
    if not path:
        return None, "MediaPipe 模型不存在或下载失败，已回退轻量算法"
    try:
        segmenter = _get_segmenter(path)
        masks = []
        for image in images[..., :3]:
            array = (image.detach().float().clamp(0, 1).cpu().numpy() * 255.0 + 0.5).astype(np.uint8)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=array)
            result = segmenter.segment(mp_image)
            confidence = result.confidence_masks
            if len(confidence) < 4:
                raise RuntimeError(f"语义模型只返回了 {len(confidence)} 个类别")
            body = torch.from_numpy(confidence[2].numpy_view().copy()).float()
            face = torch.from_numpy(confidence[3].numpy_view().copy()).float()
            mask = torch.maximum(body.squeeze(), face.squeeze()).clamp(0, 1)
            if mask.shape != image.shape[:2]:
                mask = F.interpolate(mask[None, None], size=image.shape[:2], mode="bilinear", align_corners=False)[0, 0]
            masks.append(mask)
        return torch.stack(masks, dim=0), "MediaPipe 人脸＋身体皮肤语义蒙版"
    except Exception as exc:
        return None, f"MediaPipe 执行失败，已安全回退轻量算法：{exc}"
