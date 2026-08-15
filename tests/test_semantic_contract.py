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
        existing = self.mediapipe.index("if os.path.isfile(path):")
        download_guard = self.mediapipe.index("if not allow_download:", existing)
        self.assertLess(existing, download_guard)


if __name__ == "__main__":
    unittest.main()
