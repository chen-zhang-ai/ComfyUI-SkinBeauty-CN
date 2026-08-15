from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_package():
    spec = importlib.util.spec_from_file_location(
        "skinbeauty_test_package",
        ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)],
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = package
    spec.loader.exec_module(package)
    return package


class I18nContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = load_package()
        cls.nodes_module = sys.modules["skinbeauty_test_package.nodes"]
        cls.main = {}
        cls.node_defs = {}
        for locale in ("en", "zh"):
            cls.main[locale] = json.loads((ROOT / "locales" / locale / "main.json").read_text(encoding="utf-8"))
            cls.node_defs[locale] = json.loads(
                (ROOT / "locales" / locale / "nodeDefs.json").read_text(encoding="utf-8")
            )
        cls.public_classes = {
            class_id: node_class
            for class_id, node_class in cls.package.NODE_CLASS_MAPPINGS.items()
            if not getattr(node_class, "DEV_ONLY", False)
        }

    def test_class_ids_are_stable_and_not_duplicated_per_language(self):
        self.assertEqual(
            set(self.public_classes),
            {"SkinBeautySettingsCN", "SkinBeautyProcessorCN"},
        )
        self.assertTrue(self.package.NODE_CLASS_MAPPINGS["SkinBeautyPreviewSinkCN"].DEV_ONLY)
        for locale in ("en", "zh"):
            self.assertEqual(set(self.node_defs[locale]), set(self.public_classes))

    def test_all_internal_input_keys_have_translations(self):
        classes = self.public_classes
        for class_id, node_class in classes.items():
            schema = node_class.INPUT_TYPES()
            expected = set(schema.get("required", {})) | set(schema.get("optional", {}))
            for locale in ("en", "zh"):
                translated = set(self.node_defs[locale][class_id]["inputs"])
                self.assertEqual(translated, expected, f"{locale}/{class_id}")

    def test_combo_option_keys_preserve_python_internal_values(self):
        classes = self.public_classes
        for class_id, node_class in classes.items():
            schema = node_class.INPUT_TYPES()
            for input_name, definition in schema.get("required", {}).items():
                values = definition[0]
                if not isinstance(values, (list, tuple)) or len(values) < 2:
                    continue
                for locale in ("en", "zh"):
                    options = self.node_defs[locale][class_id]["inputs"][input_name].get("options", {})
                    self.assertEqual(set(options), set(values), f"{locale}/{class_id}/{input_name}")

    def test_output_indexes_and_canvas_keys_are_complete(self):
        for class_id, node_class in self.public_classes.items():
            expected_outputs = {str(index) for index in range(len(node_class.RETURN_TYPES))}
            for locale in ("en", "zh"):
                self.assertEqual(set(self.node_defs[locale][class_id]["outputs"]), expected_outputs)
        self.assertEqual(
            set(self.main["en"]["skinBeautyCN"]),
            set(self.main["zh"]["skinBeautyCN"]),
        )

    def test_download_mode_display_text_is_safe_but_internal_value_is_stable(self):
        internal = "MediaPipe：允许首次下载"
        self.assertIn(internal, self.nodes_module.SEMANTIC_MODES)
        self.assertEqual(
            self.node_defs["zh"]["SkinBeautyProcessorCN"]["inputs"]["语义蒙版"]["options"][internal],
            "MediaPipe：仅允许下载模型，不安装Python包",
        )
        self.assertIn(
            "never installs Python packages",
            self.node_defs["en"]["SkinBeautyProcessorCN"]["inputs"]["语义蒙版"]["options"][internal],
        )


if __name__ == "__main__":
    unittest.main()
