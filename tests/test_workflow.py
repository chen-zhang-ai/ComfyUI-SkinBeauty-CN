from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "workflows" / "MiniMax_H3_2026-08-10_肤色美白版_V2.2.json"


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


if __name__ == "__main__":
    unittest.main()
