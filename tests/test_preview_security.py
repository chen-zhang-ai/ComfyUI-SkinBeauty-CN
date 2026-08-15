from __future__ import annotations

import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import torch  # noqa: F401
except ModuleNotFoundError:
    torch = None


ROOT = Path(__file__).resolve().parents[1]


def load_nodes():
    name = "skinbeauty_preview_test_package"
    spec = importlib.util.spec_from_file_location(name, ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    return sys.modules[f"{name}.nodes"]


@unittest.skipIf(torch is None, "PyTorch is required to import the node module")
class PreviewFileSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes = load_nodes()

    def test_old_file_reading_preview_route_is_removed(self):
        source = (ROOT / "nodes.py").read_text(encoding="utf-8")
        self.assertNotIn("_resolve_input_image", source)
        self.assertNotIn("/skin_beauty_cn/preview", source)

    def test_preview_write_uses_atomic_replace_and_cleans_partial_file(self):
        source = (ROOT / "nodes.py").read_text(encoding="utf-8")
        self.assertIn("os.replace(temporary, target)", source)
        self.assertIn("temporary.unlink(missing_ok=True)", source)
        self.assertNotIn("extra_pnginfo", source)

    def test_display_png_is_bounded_without_changing_source_tensor(self):
        from PIL import Image
        import torch

        with tempfile.TemporaryDirectory() as directory:
            stub = types.SimpleNamespace(get_temp_directory=lambda: directory)
            previous = sys.modules.get("folder_paths")
            sys.modules["folder_paths"] = stub
            source = torch.rand(1, 100, 1700, 4)
            original_shape = tuple(source.shape)
            try:
                info = self.nodes._save_temp_preview(source, "shape-test")
            finally:
                if previous is None:
                    sys.modules.pop("folder_paths", None)
                else:
                    sys.modules["folder_paths"] = previous
            target = Path(directory) / info["subfolder"] / info["filename"]
            with Image.open(target) as image:
                self.assertLessEqual(max(image.size), 1600)
                self.assertEqual(image.mode, "RGB")
            self.assertEqual(tuple(source.shape), original_shape)
            self.assertEqual(list(target.parent.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
