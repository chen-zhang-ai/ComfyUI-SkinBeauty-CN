from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import semantic_mediapipe as semantic  # noqa: E402


class FakeResponse:
    def __init__(self, payload: bytes, url: str = semantic.MODEL_URL, content_length: int | None = None):
        self.payload = payload
        self.offset = 0
        self.url = url
        self.headers = {"Content-Length": str(content_length if content_length is not None else len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def geturl(self):
        return self.url

    def read(self, size: int):
        chunk = self.payload[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


class MediaPipeHardeningTests(unittest.TestCase):
    def test_auto_mode_never_downloads(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            semantic.urllib.request, "urlopen"
        ) as urlopen:
            self.assertIsNone(semantic.ensure_model(directory, allow_download=False))
            urlopen.assert_not_called()

    def test_verified_download_is_loaded_then_atomically_installed(self):
        payload = b"verified model bytes"
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            semantic, "MODEL_SHA256", digest
        ), mock.patch.object(
            semantic.urllib.request, "urlopen", return_value=FakeResponse(payload)
        ), mock.patch.object(semantic, "_validate_model_load") as validate:
            path = semantic.ensure_model(directory, allow_download=True)
            self.assertEqual(Path(path).read_bytes(), payload)
            self.assertFalse(Path(str(path) + ".part").exists())
            validate.assert_called_once()

    def test_hash_failure_keeps_existing_file_and_removes_part(self):
        expected = hashlib.sha256(b"expected").hexdigest()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            semantic, "MODEL_SHA256", expected
        ), mock.patch.object(
            semantic.urllib.request, "urlopen", return_value=FakeResponse(b"wrong")
        ), mock.patch.object(semantic, "_validate_model_load") as validate:
            path = Path(semantic.default_model_path(directory))
            path.parent.mkdir(parents=True)
            path.write_bytes(b"existing unverified file")
            self.assertIsNone(semantic.ensure_model(directory, allow_download=True))
            self.assertEqual(path.read_bytes(), b"existing unverified file")
            self.assertFalse(Path(str(path) + ".part").exists())
            validate.assert_not_called()

    def test_oversized_response_falls_back(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            semantic.urllib.request,
            "urlopen",
            return_value=FakeResponse(b"x", content_length=semantic.MODEL_MAX_BYTES + 1),
        ):
            self.assertIsNone(semantic.ensure_model(directory, allow_download=True))

    def test_inference_failure_returns_pure_algorithm_fallback(self):
        image = torch.zeros(1, 8, 8, 3)
        with mock.patch.object(semantic, "ensure_model", return_value="model.tflite"), mock.patch.object(
            semantic, "_get_segmenter", side_effect=RuntimeError("failure")
        ):
            mask, report = semantic.segment_skin(image, "models", locale="en")
        self.assertIsNone(mask)
        self.assertIn("fallback", report)
        self.assertNotIn("failure", report)


if __name__ == "__main__":
    unittest.main()
