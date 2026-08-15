from __future__ import annotations

import ast
import importlib.util
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "2.2.1"


class PackageContractTests(unittest.TestCase):
    def test_version_and_zero_dependency_metadata(self):
        init_text = (ROOT / "__init__.py").read_text(encoding="utf-8")
        project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f'__version__ = "{VERSION}"', init_text)
        self.assertRegex(project, rf'(?m)^version = "{re.escape(VERSION)}"$')
        self.assertRegex(project, r"(?m)^dependencies = \[\]$")
        self.assertIn(f"## [{VERSION}]", changelog)
        self.assertNotRegex(project, r"(?i)(replace[-_ ]?me|your[-_ ]?publisher|publisher.?id\s*=)")

    def test_no_manager_auto_install_entrypoints(self):
        for name in ("requirements.txt", "install.py", "uninstall.py"):
            self.assertFalse((ROOT / name).exists(), name)
        self.assertTrue((ROOT / "extras" / "requirements-mediapipe.txt").is_file())

    def test_runtime_python_has_no_dangerous_install_or_execution_calls(self):
        for name in ("__init__.py", "nodes.py", "semantic_mediapipe.py", "skin_core.py"):
            path = ROOT / name
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(path))
            imports = {
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.Import, ast.ImportFrom))
                for alias in node.names
            }
            self.assertNotIn("cv2", imports, name)
            self.assertNotIn("subprocess", imports, name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        self.assertNotIn(node.func.id, {"eval", "exec", "compile", "__import__"}, name)
                    if isinstance(node.func, ast.Attribute):
                        self.assertFalse(
                            isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "os"
                            and node.func.attr in {"system", "popen"},
                            name,
                        )
            self.assertNotRegex(text, r"(?i)(python\s+-m\s+pip|pip\s+install)")

    def test_all_json_and_locales_parse(self):
        files = list((ROOT / "locales").rglob("*.json")) + list((ROOT / "workflows").glob("*.json"))
        self.assertGreaterEqual(len(files), 7)
        for path in files:
            json.loads(path.read_text(encoding="utf-8"))

    def test_release_builder_is_deterministic_and_excludes_development_files(self):
        spec = importlib.util.spec_from_file_location("skinbeauty_build_release", ROOT / "tools" / "build_release.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            zip_one, hash_one, count_one = module.write_archive(Path(first))
            zip_two, hash_two, count_two = module.write_archive(Path(second))
            self.assertEqual((hash_one, count_one), (hash_two, count_two))
            with zipfile.ZipFile(zip_one) as bundle:
                names = bundle.namelist()
            self.assertTrue(names)
            self.assertEqual({name.split("/", 1)[0] for name in names}, {"ComfyUI-SkinBeauty-CN"})
            self.assertIn("ComfyUI-SkinBeauty-CN/__init__.py", names)
            for name in names:
                self.assertNotRegex(name, r"(?:^|/)(?:tests|tools|\.github|__pycache__|dist)(?:/|$)")
                self.assertFalse(name.endswith((".pyc", ".zip", ".mp4")), name)


if __name__ == "__main__":
    unittest.main()
