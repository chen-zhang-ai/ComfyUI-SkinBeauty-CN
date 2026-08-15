from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import torch
except ModuleNotFoundError:
    torch = None


ROOT = Path(__file__).resolve().parents[1]


def load_package():
    name = "skinbeauty_nodes_test_package"
    spec = importlib.util.spec_from_file_location(
        name,
        ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)],
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    return sys.modules[f"{name}.nodes"]


@unittest.skipIf(torch is None, "PyTorch is required for runtime tests")
class NodeRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes = load_package()

    def arguments(self):
        return {
            "图像": torch.rand(2, 24, 30, 3),
            "美白参数": {"preset": "关闭", "intensity": 0},
            "蒙版模式": "全图调色",
            "语义蒙版": "自动：已有模型则使用",
            "批处理": "整批并行",
            "计算设备": "自动",
            "生成节点预览": False,
            "实时精确预览": True,
        }

    def test_auto_device_oom_retries_parallel_then_sequential_then_cpu(self):
        args = self.arguments()
        calls = []

        def fake_process(images, config, **kwargs):
            calls.append((str(images.device), kwargs["sequential"]))
            if len(calls) < 3:
                raise RuntimeError("CUDA out of memory")
            return images, torch.zeros(images.shape[:3], device=images.device)

        # Avoid requiring a physical GPU in the lightweight CI contract test;
        # process_images itself is exercised on real CPU/GPU in test_skin_core.
        original_to = torch.Tensor.to

        def fake_to(tensor, *positional, **keywords):
            device = keywords.get("device", positional[0] if positional else None)
            if device is not None and torch.device(device).type == "cuda":
                keywords.pop("device", None)
                positional = positional[1:] if positional else positional
            return original_to(tensor, *positional, **keywords)

        with (
            patch.object(self.nodes, "_select_device", return_value=torch.device("cuda")),
            patch.object(self.nodes, "_semantic_for", return_value=(None, "test mask")),
            patch.object(self.nodes, "process_images", side_effect=fake_process),
            patch.object(torch.Tensor, "to", fake_to),
            patch.object(torch.cuda, "empty_cache"),
        ):
            result = self.nodes.SkinBeautyProcessorCN().process(**args)

        self.assertEqual([sequential for _, sequential in calls], [False, True, True])
        self.assertEqual(tuple(result[0].shape), tuple(args["图像"].shape))
        self.assertIn("回退 CPU", result[3])
        self.assertIn("fell back", result[3])

    def test_explicit_gpu_never_silently_falls_back_to_cpu(self):
        args = self.arguments()
        args["计算设备"] = "GPU"
        original_to = torch.Tensor.to

        def fake_to(tensor, *positional, **keywords):
            device = keywords.get("device", positional[0] if positional else None)
            if device is not None and torch.device(device).type == "cuda":
                keywords.pop("device", None)
                positional = positional[1:] if positional else positional
            return original_to(tensor, *positional, **keywords)

        with (
            patch.object(self.nodes, "_select_device", return_value=torch.device("cuda")),
            patch.object(self.nodes, "_semantic_for", return_value=(None, "test mask")),
            patch.object(self.nodes, "process_images", side_effect=RuntimeError("CUDA out of memory")) as process,
            patch.object(torch.Tensor, "to", fake_to),
            patch.object(torch.cuda, "empty_cache"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Skin-beauty processing ran out of memory"):
                self.nodes.SkinBeautyProcessorCN().process(**args)
        self.assertEqual(process.call_count, 2)

    def test_oom_error_does_not_expose_backend_paths(self):
        args = self.arguments()
        args["计算设备"] = "GPU"
        original_to = torch.Tensor.to

        def fake_to(tensor, *positional, **keywords):
            device = keywords.get("device", positional[0] if positional else None)
            if device is not None and torch.device(device).type == "cuda":
                keywords.pop("device", None)
                positional = positional[1:] if positional else positional
            return original_to(tensor, *positional, **keywords)

        private_detail = "CUDA out of memory while reading C:" + "\\Users\\Private\\secret.bin"
        with (
            patch.object(self.nodes, "_select_device", return_value=torch.device("cuda")),
            patch.object(self.nodes, "_semantic_for", return_value=(None, "test mask")),
            patch.object(self.nodes, "process_images", side_effect=RuntimeError(private_detail)),
            patch.object(torch.Tensor, "to", fake_to),
            patch.object(torch.cuda, "empty_cache"),
        ):
            with self.assertRaises(RuntimeError) as raised:
                self.nodes.SkinBeautyProcessorCN().process(**args)
        message = str(raised.exception)
        self.assertIn("人物肤色美白显存不足", message)
        self.assertIn("Skin-beauty processing ran out of memory", message)
        self.assertNotIn("Users", message)
        self.assertNotIn("secret.bin", message)

    def test_processor_delegates_to_the_shared_backend_entry(self):
        args = self.arguments()
        image = args["图像"]
        mask = torch.zeros(image.shape[:3])
        shared = self.nodes.SkinBeautyRun(image, mask, image, "shared report")
        with patch.object(self.nodes, "run_skin_beauty", return_value=shared) as run:
            result = self.nodes.SkinBeautyProcessorCN().process(**args)
        run.assert_called_once()
        self.assertIs(result[0], image)
        self.assertIs(result[1], mask)
        self.assertEqual(result[3], "shared report")

    def test_large_source_reaches_shared_processor_at_original_resolution(self):
        # expand() keeps this 3072x5440 contract test memory-light in CI.
        image = torch.zeros(1, 1, 1, 3).expand(1, 5440, 3072, 3)
        seen = []

        def fake_process(images, config, **kwargs):
            seen.append(tuple(images.shape))
            return images, torch.zeros(images.shape[:3])

        with (
            patch.object(self.nodes, "_select_device", return_value=torch.device("cpu")),
            patch.object(self.nodes, "_semantic_for", return_value=(None, "test mask")),
            patch.object(self.nodes, "process_images", side_effect=fake_process),
        ):
            run = self.nodes.run_skin_beauty(
                image,
                {"preset": "关闭", "intensity": 0},
                "全图调色",
                "自动：已有模型则使用",
                "逐张处理",
                "CPU",
            )
        self.assertEqual(seen, [(1, 5440, 3072, 3)])
        self.assertEqual(tuple(run.result.shape), (1, 5440, 3072, 3))
        self.assertEqual(tuple(run.preview.shape), (1, 5440, 3072, 3))

    def test_external_mask_modes_skip_semantic_and_keep_exact_result_source(self):
        image = torch.rand(1, 24, 30, 4)
        external = torch.zeros(1, 24, 30)
        external[:, 4:20, 6:24] = 1
        for mode in ("外部遮罩优先", "仅外部遮罩"):
            with patch.object(self.nodes, "_semantic_for") as semantic:
                run = self.nodes.run_skin_beauty(
                    image,
                    {"preset": "中档·自然冷白"},
                    mode,
                    "MediaPipe：允许首次下载",
                    "逐张处理",
                    "CPU",
                    external,
                )
            semantic.assert_not_called()
            self.assertTrue(torch.equal(run.result, run.preview))
            self.assertEqual(tuple(run.result.shape), tuple(image.shape))
            self.assertTrue(torch.equal(run.result[..., 3:], image[..., 3:]))

    def test_full_image_mode_skips_semantic_and_keeps_exact_result_source(self):
        image = torch.rand(2, 18, 26, 3)
        with patch.object(self.nodes, "_semantic_for") as semantic:
            run = self.nodes.run_skin_beauty(
                image,
                {"preset": "低档·自然提亮"},
                "全图调色",
                "MediaPipe：允许首次下载",
                "整批并行",
                "CPU",
            )
        semantic.assert_not_called()
        self.assertTrue(torch.equal(run.result, run.preview))
        self.assertEqual(tuple(run.result.shape), tuple(image.shape))

    def test_only_external_mask_has_clear_bilingual_error(self):
        with self.assertRaisesRegex(ValueError, "没有连接外部遮罩.*[Nn]o external mask is connected"):
            self.nodes.run_skin_beauty(
                torch.rand(1, 8, 9, 3),
                {"preset": "关闭"},
                "仅外部遮罩",
                "纯算法：零依赖",
                "逐张处理",
                "CPU",
            )

    def test_internal_preview_sink_scales_only_display_files(self):
        before = torch.rand(1, 1800, 3200, 4)
        after = before.clone()
        seen = []

        def fake_save(image, unique_id="preview"):
            seen.append((tuple(image.shape), unique_id))
            return {"filename": f"{unique_id}.png", "subfolder": "skinbeauty_cn", "type": "temp"}

        with patch.object(self.nodes, "_save_temp_preview", side_effect=fake_save):
            payload = self.nodes.SkinBeautyPreviewSinkCN().save_preview(before, after, "request-7")
        self.assertEqual(seen[0][0], tuple(before.shape))
        self.assertEqual(seen[1][0], tuple(after.shape))
        self.assertEqual(payload["ui"]["skin_beauty_request"], ["request-7"])
        self.assertIs(payload["result"], tuple())


if __name__ == "__main__":
    unittest.main()
