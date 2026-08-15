from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class JavaScriptRuntimeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is not available")
    def test_exact_preview_prompt_and_single_flight(self):
        completed = subprocess.run(
            ["node", "--test", str(ROOT / "tests" / "js" / "test_exact_preview_prompt.mjs")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, (completed.stdout or "") + (completed.stderr or ""))


if __name__ == "__main__":
    unittest.main()
