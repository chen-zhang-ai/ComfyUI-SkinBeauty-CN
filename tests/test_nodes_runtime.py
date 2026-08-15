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


if __name__ == "__main__":
    unittest.main()
