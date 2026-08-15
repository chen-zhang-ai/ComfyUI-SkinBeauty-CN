from __future__ import annotations

import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path

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
class PreviewPathSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes = load_nodes()

    def test_accepts_existing_file_beneath_comfy_input_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "input"
            path = root / "safe" / "photo.png"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"test")
            stub = types.SimpleNamespace(get_input_directory=lambda: str(root))
            previous = sys.modules.get("folder_paths")
            sys.modules["folder_paths"] = stub
            try:
                resolved = self.nodes._resolve_input_image(
                    {"type": "input", "subfolder": "safe", "filename": "photo.png"}
                )
            finally:
                if previous is None:
                    sys.modules.pop("folder_paths", None)
                else:
                    sys.modules["folder_paths"] = previous
            self.assertEqual(Path(resolved), path.resolve())

    def test_rejects_output_type_traversal_and_missing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "input"
            root.mkdir()
            outside = Path(directory) / "private.png"
            outside.write_bytes(b"private")
            stub = types.SimpleNamespace(get_input_directory=lambda: str(root))
            previous = sys.modules.get("folder_paths")
            sys.modules["folder_paths"] = stub
            try:
                with self.assertRaisesRegex(ValueError, "input directory"):
                    self.nodes._resolve_input_image({"type": "output", "filename": "private.png"})
                with self.assertRaisesRegex(ValueError, "outside the allowed path"):
                    self.nodes._resolve_input_image(
                        {"type": "input", "subfolder": "..", "filename": "private.png"}
                    )
                with self.assertRaisesRegex(ValueError, "missing"):
                    self.nodes._resolve_input_image({"type": "input", "filename": "missing.png"})
            finally:
                if previous is None:
                    sys.modules.pop("folder_paths", None)
                else:
                    sys.modules["folder_paths"] = previous


if __name__ == "__main__":
    unittest.main()
