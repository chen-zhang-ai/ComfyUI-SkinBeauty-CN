"""Optional MediaPipe face/body skin segmentation.

The MediaPipe and NumPy packages are imported only when semantic processing is
requested, so the node pack remains usable with ComfyUI's existing PyTorch.
"""

from __future__ import annotations

import hashlib
import os
import threading
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Tuple

import torch
import torch.nn.functional as F


MODEL_NAME = "selfie_multiclass_256x256.tflite"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/image_segmenter/"
    "selfie_multiclass_256x256/float32/1/"
    + MODEL_NAME
)
MODEL_SHA256 = "c6748b1253a99067ef71f7e26ca71096cd449baefa8f101900ea23016507e0e0"
MODEL_MAX_BYTES = 32 * 1024 * 1024
MODEL_TIMEOUT_SECONDS = 60
ALLOWED_MODEL_HOSTS = frozenset({"storage.googleapis.com"})
_LOCK = threading.Lock()
_SEGMENTER = None
_SEGMENTER_PATH: Optional[str] = None
_LAST_MODEL_ERROR = ""


def _message(zh: str, en: str, locale: Optional[str] = None) -> str:
    if locale == "zh":
        return zh
    if locale == "en":
        return en
    return f"{zh} / {en}"


def default_model_path(models_dir: str) -> str:
    return str(Path(models_dir) / "mediapipe" / MODEL_NAME)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_valid_model(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size <= MODEL_MAX_BYTES and _sha256(path) == MODEL_SHA256
    except OSError:
        return False


def status(models_dir: str, locale: Optional[str] = None) -> Tuple[bool, str]:
    try:
        import mediapipe  # noqa: F401
    except Exception as exc:
        return False, _message(
            f"未安装 MediaPipe，已回退纯算法（{exc.__class__.__name__}）",
            f"MediaPipe is not installed; using the pure algorithm fallback ({exc.__class__.__name__})",
            locale,
        )
    path = Path(default_model_path(models_dir))
    if not _is_valid_model(path):
        return False, _message(
            "MediaPipe 模型缺失或校验失败，已回退纯算法",
            "The MediaPipe model is missing or failed verification; using the pure algorithm fallback",
            locale,
        )
    return True, _message(
        "MediaPipe 人脸＋身体皮肤语义蒙版",
        "MediaPipe face and body skin semantic mask",
        locale,
    )


def ensure_model(models_dir: str, allow_download: bool) -> Optional[str]:
    """Return a verified model, downloading only after explicit opt-in.

    The existing file is never replaced until the complete download has the
    pinned hash and can be loaded by MediaPipe.  No Python package operation is
    performed here or anywhere else in this project.
    """

    global _LAST_MODEL_ERROR
    path = Path(default_model_path(models_dir))
    if _is_valid_model(path):
        _LAST_MODEL_ERROR = ""
        return str(path)
    if not allow_download:
        _LAST_MODEL_ERROR = "download_not_allowed"
        return None

    parsed = urlparse(MODEL_URL)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_MODEL_HOSTS:
        _LAST_MODEL_ERROR = "unsafe_model_url"
        return None

    with _LOCK:
        if _is_valid_model(path):
            _LAST_MODEL_ERROR = ""
            return str(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(str(path) + ".part")
        try:
            temporary.unlink(missing_ok=True)
            request = urllib.request.Request(
                MODEL_URL,
                headers={"User-Agent": "ComfyUI-SkinBeauty-CN/2.2.1"},
            )
            total = 0
            digest = hashlib.sha256()
            with urllib.request.urlopen(request, timeout=MODEL_TIMEOUT_SECONDS) as response:
                final_url = urlparse(response.geturl())
                if final_url.scheme != "https" or final_url.hostname not in ALLOWED_MODEL_HOSTS:
                    raise ValueError("unsafe_redirect")
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MODEL_MAX_BYTES:
                    raise ValueError("model_too_large")
                with temporary.open("wb") as handle:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > MODEL_MAX_BYTES:
                            raise ValueError("model_too_large")
                        digest.update(chunk)
                        handle.write(chunk)
            if total == 0 or digest.hexdigest() != MODEL_SHA256:
                raise ValueError("model_hash_mismatch")
            _validate_model_load(str(temporary))
            os.replace(temporary, path)
            _LAST_MODEL_ERROR = ""
            return str(path)
        except Exception as exc:
            _LAST_MODEL_ERROR = exc.__class__.__name__
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            return None


def _new_segmenter(path: str):
    import mediapipe as mp

    options = mp.tasks.vision.ImageSegmenterOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=path),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        output_confidence_masks=True,
        output_category_mask=False,
    )
    return mp.tasks.vision.ImageSegmenter.create_from_options(options)


def _validate_model_load(path: str) -> None:
    segmenter = _new_segmenter(path)
    close = getattr(segmenter, "close", None)
    if callable(close):
        close()


def _get_segmenter(path: str):
    global _SEGMENTER, _SEGMENTER_PATH
    with _LOCK:
        if _SEGMENTER is not None and _SEGMENTER_PATH == path:
            return _SEGMENTER
        _SEGMENTER = _new_segmenter(path)
        _SEGMENTER_PATH = path
        return _SEGMENTER


def segment_skin(
    images: torch.Tensor,
    models_dir: str,
    allow_download: bool = False,
    locale: Optional[str] = None,
) -> Tuple[Optional[torch.Tensor], str]:
    """Segment face skin + body skin and return a BHW float mask."""

    try:
        import mediapipe as mp
        import numpy as np
    except Exception as exc:
        return None, _message(
            f"MediaPipe 不可用，已回退纯算法（{exc.__class__.__name__}）",
            f"MediaPipe is unavailable; using the pure algorithm fallback ({exc.__class__.__name__})",
            locale,
        )

    path = ensure_model(models_dir, allow_download)
    if not path:
        reason = _LAST_MODEL_ERROR or "model_unavailable"
        return None, _message(
            f"MediaPipe 模型不可用，已回退纯算法（{reason}）",
            f"The MediaPipe model is unavailable; using the pure algorithm fallback ({reason})",
            locale,
        )
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
        return torch.stack(masks, dim=0), _message(
            "MediaPipe 人脸＋身体皮肤语义蒙版",
            "MediaPipe face and body skin semantic mask",
            locale,
        )
    except Exception as exc:
        return None, _message(
            f"MediaPipe 推理失败，已安全回退纯算法（{exc.__class__.__name__}）",
            f"MediaPipe inference failed; safely using the pure algorithm fallback ({exc.__class__.__name__})",
            locale,
        )
