from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "web" / "skin_beauty.js"
BACKEND = ROOT / "nodes.py"


class FrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.javascript = FRONTEND.read_text(encoding="utf-8")
        cls.backend = BACKEND.read_text(encoding="utf-8")

    def test_short_exact_status_and_ellipsizing(self):
        self.assertIn('state.statusKey = "exactComplete"', self.javascript)
        self.assertIn('exactComplete: "Exact preview ready"', self.javascript)
        self.assertIn('exactComplete: "精确预览完成"', self.javascript)
        self.assertIn("function ellipsizedText", self.javascript)

    def test_custom_buttons_precede_comparer(self):
        exact = self.javascript.index('"exact",')
        comparer = self.javascript.index("node.addCustomWidget(compareWidget())", exact)
        self.assertLess(exact, comparer)
        self.assertNotIn('node.addWidget("button"', self.javascript)
        self.assertNotIn('"approximate",', self.javascript)
        self.assertNotIn("刷新即时预览", self.javascript)

    def test_comparer_has_drag_interaction(self):
        self.assertIn("SKIN_BEAUTY_COMPARE", self.javascript)
        self.assertIn("state.compareDragging = true", self.javascript)
        self.assertIn("updateSplit()", self.javascript)

    def test_comparer_tracks_node_level_mouse_move(self):
        self.assertIn("const originalMouseMove = node.onMouseMove", self.javascript)
        self.assertIn("updateCompareFromNodePosition(this, pos)", self.javascript)
        self.assertIn("state.split = Math.max", self.javascript)

    def test_comparer_fills_resizable_remainder_with_fine_line(self):
        self.assertIn("Number(owner.size?.[1] || 0) - viewportY - 8", self.javascript)
        self.assertIn("function displayCanvas(image, longest = 1600)", self.javascript)
        self.assertIn("ctx.lineWidth = 1", self.javascript)
        self.assertNotIn('ctx.fillText("原图"', self.javascript)
        self.assertNotIn('ctx.fillText(state.exact ? "结果"', self.javascript)
        self.assertNotIn("ctx.arc(splitX", self.javascript)

    def test_buttons_are_compact(self):
        self.assertIn("return [width, 23]", self.javascript)
        self.assertIn("name: labelKey", self.javascript)

    def test_v1_semantic_mode_is_default(self):
        self.assertIn(
            'SEMANTIC_MODES = ("自动：已有模型则使用", "纯算法：零依赖",',
            self.backend,
        )

    def test_exact_preview_is_automatic_and_approximation_removed(self):
        self.assertIn("scheduleExact(node, 500)", self.javascript)
        self.assertIn("const scheduledToken = ++state.exactToken", self.javascript)
        self.assertNotIn("function renderApproximate", self.javascript)
        self.assertNotIn("function refreshApproximate", self.javascript)
        self.assertIn('"实时精确预览": ("BOOLEAN", {"default": True})', self.backend)

    def test_ui_thumbnail_is_private_and_image_output_is_full_size(self):
        self.assertIn('"skin_beauty_preview"', self.backend)
        self.assertNotIn('"ui": {"images"', self.backend)
        self.assertIn("preview = result", self.backend)

    def test_canvas_i18n_uses_public_setting_and_safe_fallbacks(self):
        self.assertIn('setting?.get?.("Comfy.Locale")', self.javascript)
        self.assertIn('getSettingValue?.("Comfy.Locale")', self.javascript)
        self.assertIn("document.documentElement?.lang", self.javascript)
        self.assertIn("navigator.language", self.javascript)
        self.assertIn('"Comfy.Locale.change"', self.javascript)
        self.assertIn("locale: currentLocale()", self.javascript)


if __name__ == "__main__":
    unittest.main()
