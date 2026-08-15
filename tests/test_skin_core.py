from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

try:
    import torch
except ModuleNotFoundError:  # The test also runs in documentation-only CI images.
    torch = None


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

if torch is not None:
    from skin_core import (  # noqa: E402
        PRESETS,
        automatic_skin_mask,
        lab_to_rgb,
        process_images,
        resolve_config,
        rgb_to_lab,
    )


@unittest.skipIf(torch is None, "当前 Python 环境未安装 PyTorch；请在 ComfyUI 的 Python 环境运行")
class SkinCoreTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(7)

    def test_lab_round_trip(self):
        image = torch.rand(2, 3, 24, 31) * 0.96 + 0.02
        restored = lab_to_rgb(rgb_to_lab(image))
        self.assertLess(float((restored - image).abs().max()), 2e-4)

    def test_disabled_preset_is_identity_and_keeps_alpha(self):
        image = torch.rand(2, 32, 24, 4)
        config = resolve_config({"preset": "关闭", **PRESETS["关闭"]})
        result, mask = process_images(image, config)
        self.assertTrue(torch.equal(result, image))
        self.assertEqual(tuple(mask.shape), (2, 32, 24))

    def test_external_mask_changes_only_selected_area(self):
        image = torch.zeros(1, 40, 50, 3)
        image[:] = torch.tensor([0.18, 0.28, 0.55])
        image[:, 9:31, 12:38] = torch.tensor([0.68, 0.47, 0.34])
        external = torch.zeros(1, 40, 50)
        external[:, 9:31, 12:38] = 1
        config = replace(resolve_config({"preset": "高档·通透冷白", **PRESETS["高档·通透冷白"]}), mask_feather=0)
        result, mask = process_images(image, config, mask_mode="仅外部遮罩", external_mask=external)
        inside = (result[:, 9:31, 12:38] - image[:, 9:31, 12:38]).abs().mean()
        outside = (result[:, :8] - image[:, :8]).abs().max()
        self.assertGreater(float(inside), 0.01)
        self.assertLess(float(outside), 1e-7)
        self.assertTrue(torch.equal(mask, external))

    def test_batch_sequential_and_parallel_match(self):
        image = torch.rand(3, 48, 56, 3) * 0.55 + 0.2
        config = resolve_config({"preset": "中档·自然冷白", **PRESETS["中档·自然冷白"]})
        sequential, seq_mask = process_images(image, config, mask_mode="全图调色", sequential=True)
        parallel, par_mask = process_images(image, config, mask_mode="全图调色", sequential=False)
        self.assertEqual(tuple(sequential.shape), tuple(image.shape))
        self.assertTrue(torch.allclose(sequential, parallel, atol=1e-5, rtol=1e-5))
        self.assertTrue(torch.allclose(seq_mask, par_mask, atol=1e-6, rtol=1e-6))

    def test_cool_white_increases_lightness_and_reduces_lab_yellow(self):
        image = torch.tensor([0.67, 0.46, 0.29]).view(1, 1, 1, 3).expand(1, 20, 20, 3).clone()
        config = resolve_config({"preset": "冷白皮", **PRESETS["冷白皮"], "mask_feather": 0})
        result, _ = process_images(image, config, mask_mode="全图调色")
        before = rgb_to_lab(image.permute(0, 3, 1, 2))
        after = rgb_to_lab(result.permute(0, 3, 1, 2))
        self.assertGreater(float(after[:, 0].mean()), float(before[:, 0].mean()))
        self.assertLess(float(after[:, 2].mean()), float(before[:, 2].mean()))
        self.assertTrue(torch.isfinite(result).all())

    def test_mask_shape_and_config_clamping(self):
        image = torch.rand(2, 29, 37, 3)
        mask = automatic_skin_mask(image.permute(0, 3, 1, 2), sensitivity=100)
        self.assertEqual(tuple(mask.shape), (2, 1, 29, 37))
        self.assertGreaterEqual(float(mask.min()), 0)
        self.assertLessEqual(float(mask.max()), 1)
        config = resolve_config({"intensity": 999, "coolness": -999, "mask_feather": 900})
        self.assertEqual(config.intensity, 100)
        self.assertEqual(config.coolness, -100)
        self.assertEqual(config.mask_feather, 64)


if __name__ == "__main__":
    unittest.main()
