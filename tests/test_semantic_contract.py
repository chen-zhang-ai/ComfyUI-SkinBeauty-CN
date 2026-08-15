from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SemanticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes = (ROOT / "nodes.py").read_text(encoding="utf-8")
        cls.core = (ROOT / "skin_core.py").read_text(encoding="utf-8")
        cls.mediapipe = (ROOT / "semantic_mediapipe.py").read_text(encoding="utf-8")

    def test_auto_mode_uses_existing_mediapipe_without_download(self):
        self.assertIn(
            'SEMANTIC_MODES = ("自动：已有模型则使用", "纯算法：零依赖",',
            self.nodes,
        )
        self.assertIn('allow_download = mode == "MediaPipe：允许首次下载"', self.nodes)

    def test_semantic_location_is_combined_with_colour_probability(self):
        self.assertIn("mask = sem * (0.30 + 0.70 * auto)", self.core)
        self.assertIn("torch.maximum(body.squeeze(), face.squeeze())", self.mediapipe)

    def test_download_mode_reuses_existing_model_first(self):
        existing = self.mediapipe.index("if _is_valid_model(path):")
        download_guard = self.mediapipe.index("if not allow_download:", existing)
        self.assertLess(existing, download_guard)

    def test_download_is_pinned_bounded_and_atomic(self):
        self.assertIn("/float32/1/", self.mediapipe)
        self.assertNotIn("/latest/", self.mediapipe)
        self.assertIn(
            'MODEL_SHA256 = "c6748b1253a99067ef71f7e26ca71096cd449baefa8f101900ea23016507e0e0"',
            self.mediapipe,
        )
        self.assertIn("MODEL_MAX_BYTES", self.mediapipe)
        self.assertIn("MODEL_TIMEOUT_SECONDS", self.mediapipe)
        self.assertIn('temporary = Path(str(path) + ".part")', self.mediapipe)
        self.assertIn("_validate_model_load(str(temporary))", self.mediapipe)
        self.assertIn("os.replace(temporary, path)", self.mediapipe)
        self.assertNotIn("urlretrieve", self.mediapipe)

    def test_download_label_keeps_internal_value_compatible(self):
        self.assertIn('allow_download = mode == "MediaPipe：允许首次下载"', self.nodes)
        self.assertIn("Keep the V2.2 enum value stable", self.nodes)


if __name__ == "__main__":
    unittest.main()
