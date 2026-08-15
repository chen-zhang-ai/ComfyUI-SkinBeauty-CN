from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / "workflows"
WORKFLOW = WORKFLOW_DIR / "MiniMax_H3_SkinBeauty_Integration.json"
MINIMAL_PURE = WORKFLOW_DIR / "SkinBeauty_Minimal_Pure_Algorithm.json"
MINIMAL_AUTO = WORKFLOW_DIR / "SkinBeauty_Minimal_Auto_Semantic.json"


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
        cls.nodes = {node["id"]: node for node in cls.workflow["nodes"]}
        cls.links = {link[0]: link for link in cls.workflow["links"]}

    def test_expected_nodes_exist(self):
        self.assertEqual(self.nodes[272]["type"], "SkinBeautySettingsCN")
        self.assertEqual(self.nodes[273]["type"], "SkinBeautyProcessorCN")
        self.assertEqual(self.nodes[274]["type"], "SkinBeautyProcessorCN")
        self.assertEqual(self.nodes[275]["type"], "MarkdownNote")

    def test_both_processed_images_feed_node_186(self):
        self.assertEqual(self.nodes[186]["inputs"][3]["link"], 647)
        self.assertEqual(self.nodes[186]["inputs"][4]["link"], 650)
        self.assertEqual(self.links[647][1:6], [273, 0, 186, 3, "IMAGE"])
        self.assertEqual(self.links[650][1:6], [274, 0, 186, 4, "IMAGE"])

    def test_sources_are_redirected_without_swapping(self):
        self.assertEqual(self.links[582][1:6], [139, 0, 273, 0, "IMAGE"])
        self.assertEqual(self.links[550][1:6], [137, 0, 274, 0, "IMAGE"])
        self.assertEqual(self.nodes[273]["inputs"][0]["link"], 582)
        self.assertEqual(self.nodes[274]["inputs"][0]["link"], 550)

    def test_original_bypass_state_is_preserved(self):
        self.assertEqual(self.nodes[139]["mode"], 4)
        self.assertEqual(self.nodes[273]["mode"], 4)
        self.assertEqual(self.nodes[137]["mode"], 0)
        self.assertEqual(self.nodes[274]["mode"], 0)

    def test_v1_semantic_defaults_and_embedded_help(self):
        self.assertEqual(self.nodes[273]["widgets_values"][1], "自动：已有模型则使用")
        self.assertEqual(self.nodes[274]["widgets_values"][1], "自动：已有模型则使用")
        help_text = self.nodes[275]["widgets_values"][0]
        self.assertIn("左右", help_text)
        self.assertIn("保持原始宽高", help_text)
        self.assertIn("恢复V1", help_text)
        self.assertIn("自动防抖刷新精确预览", help_text)
        self.assertIn("仅允许下载模型，不安装Python包", help_text)
        self.assertIn("never installs Python packages", help_text)
        self.assertNotIn("刷新即时预览", help_text)

    def test_only_active_reference_auto_previews(self):
        self.assertFalse(self.nodes[273]["widgets_values"][5])
        self.assertTrue(self.nodes[274]["widgets_values"][5])

    def test_processor_preview_outputs_do_not_feed_resize_nodes(self):
        self.assertEqual(self.nodes[273]["outputs"][2]["links"], [])
        self.assertEqual(self.nodes[274]["outputs"][2]["links"], [])

    def test_every_link_has_valid_registered_endpoints(self):
        self.assertEqual(len(self.nodes), len(self.workflow["nodes"]))
        self.assertEqual(len(self.links), len(self.workflow["links"]))
        for link_id, link in self.links.items():
            _, source_id, source_slot, target_id, target_slot, _ = link
            source = self.nodes[source_id]
            target = self.nodes[target_id]
            self.assertIn(link_id, source["outputs"][source_slot].get("links") or [])
            self.assertEqual(target["inputs"][target_slot].get("link"), link_id)

    def test_minimal_workflows_use_only_core_and_project_nodes(self):
        for path, semantic_mode in (
            (MINIMAL_PURE, "纯算法：零依赖"),
            (MINIMAL_AUTO, "自动：已有模型则使用"),
        ):
            workflow = json.loads(path.read_text(encoding="utf-8"))
            nodes = {node["id"]: node for node in workflow["nodes"]}
            self.assertEqual(
                {node["type"] for node in workflow["nodes"]},
                {"LoadImage", "SkinBeautySettingsCN", "SkinBeautyProcessorCN", "PreviewImage"},
            )
            processor = next(node for node in workflow["nodes"] if node["type"] == "SkinBeautyProcessorCN")
            self.assertEqual(processor["widgets_values"][1], semantic_mode)
            links = {link[0]: link for link in workflow["links"]}
            for link_id, link in links.items():
                _, source_id, source_slot, target_id, target_slot, link_type = link
                self.assertIn(link_id, nodes[source_id]["outputs"][source_slot].get("links") or [])
                self.assertEqual(nodes[target_id]["inputs"][target_slot].get("link"), link_id)
                self.assertEqual(nodes[source_id]["outputs"][source_slot]["type"], link_type)
                self.assertEqual(nodes[target_id]["inputs"][target_slot]["type"], link_type)

    def test_workflows_have_no_absolute_paths_or_sensitive_fields(self):
        windows_path = re.compile(r"(?i)(?<![a-z])[a-z]:[\\/](?![\\/])")
        unix_path = re.compile(r"(?:^|[\s\"'])/(?:home|Users)/")
        sensitive_key = re.compile(r"(?i)(api.?key|access.?token|password|bearer|authorization|cookie|fullpath)")

        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    self.assertIsNone(sensitive_key.search(key), key)
                    yield from walk(item)
            elif isinstance(value, list):
                for item in value:
                    yield from walk(item)
            elif isinstance(value, str):
                yield value

        for path in (WORKFLOW, MINIMAL_PURE, MINIMAL_AUTO):
            workflow = json.loads(path.read_text(encoding="utf-8"))
            for text in walk(workflow):
                self.assertIsNone(windows_path.search(text), f"{path.name}: {text}")
                self.assertIsNone(unix_path.search(text), f"{path.name}: {text}")

    def test_third_party_widget_object_serialization_is_preserved(self):
        nodes = {node["id"]: node for node in self.workflow["nodes"]}
        self.assertIsInstance(nodes[144]["widgets_values"], dict)
        self.assertIsInstance(nodes[168]["widgets_values"], dict)


if __name__ == "__main__":
    unittest.main()
