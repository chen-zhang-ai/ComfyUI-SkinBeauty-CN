from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
FULL_SHA_USE = re.compile(r"(?m)^\s*-?\s*uses:\s+([^\s@]+)@([0-9a-f]{40})(?:\s+#\s+.+)?$")
ANY_REMOTE_USE = re.compile(r"(?m)^\s*-?\s*uses:\s+([^\s@./][^\s@]*)@([^\s#]+)")


class CIContractTests(unittest.TestCase):
    def text(self, name: str) -> str:
        return (WORKFLOWS / name).read_text(encoding="utf-8")

    def test_every_remote_action_is_pinned_to_a_full_commit(self):
        for path in WORKFLOWS.glob("*.yml"):
            text = path.read_text(encoding="utf-8")
            full = {(owner, ref) for owner, ref in FULL_SHA_USE.findall(text)}
            for owner, ref in ANY_REMOTE_USE.findall(text):
                self.assertIn((owner, ref), full, f"unpinned action in {path.name}: {owner}@{ref}")

    def test_release_calls_complete_reusable_quality_before_writing(self):
        quality = self.text("quality.yml")
        release = self.text("release.yml")
        self.assertIn("workflow_call:", quality)
        self.assertIn("name: Quality Gate", quality)
        self.assertIn("uses: ./.github/workflows/quality.yml", release)
        self.assertRegex(release, r"(?s)release:\s+needs:\s+quality")
        self.assertNotIn("workflow_dispatch:", release)
        self.assertIn('git rev-parse "$TAG^{}"', release)
        self.assertIn('git rev-parse HEAD', release)
        self.assertNotIn("COMMIT: ${{ github.sha }}", release)
        self.assertIn("gh release download v2.2.1", release)
        self.assertIn("skinbeauty-video-comparison.mp4", release)
        self.assertIn("2e830967a4ea99900478fb592e995862da297b3b0652b3da81d98097efe0ae28", release)

    def test_quality_matrix_and_deterministic_double_build_are_enforced(self):
        quality = self.text("quality.yml")
        self.assertIn('python: ["3.10", "3.11", "3.12"]', quality)
        self.assertIn("os: [ubuntu-latest, windows-latest]", quality)
        self.assertIn("test_javascript_runtime.py", quality)
        self.assertIn("dist-one", quality)
        self.assertIn("dist-two", quality)
        self.assertIn("cmp", quality)
        self.assertIn("torch==2.9.1", quality)
        self.assertIn("Pillow==11.3.0", quality)
        self.assertIn("numpy==1.26.4", quality)

    def test_permissions_are_minimal_by_workflow(self):
        self.assertIn("permissions:\n  contents: read", self.text("quality.yml"))
        self.assertIn("permissions:\n  contents: write", self.text("release.yml"))
        self.assertIn("permissions:\n  contents: read", self.text("publish_action.yml"))

    def test_dependabot_updates_pinned_github_actions(self):
        dependabot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
        self.assertIn("version: 2", dependabot)
        self.assertIn("package-ecosystem: github-actions", dependabot)
        self.assertIn('directory: "/"', dependabot)

    def test_registry_publish_is_manual_version_locked_and_secret_scoped(self):
        publish = self.text("publish_action.yml")
        self.assertIn("workflow_dispatch:", publish)
        self.assertIn("publish-v2.2.2", publish)
        self.assertIn('version = "2.2.2"', publish)
        self.assertIn('PublisherId = "chen-zhang-ai"', publish)
        self.assertIn('Repository = "https://github.com/chen-zhang-ai/ComfyUI-SkinBeauty-CN"', publish)
        self.assertIn("--json isDraft --jq .isDraft", publish)
        self.assertIn("--json isPrerelease --jq .isPrerelease", publish)
        self.assertIn("secrets.REGISTRY_ACCESS_TOKEN", publish)
        self.assertNotIn("pull_request:", publish)


if __name__ == "__main__":
    unittest.main()
