from __future__ import annotations

import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
EXPECTED = {"presets.png", "before.png", "after.png", "before-after-comparison.png"}


def png_chunks(path: Path):
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AssertionError(f"not a PNG: {path}")
    offset = 8
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        yield kind, payload
        offset += 12 + length


class MediaContractTests(unittest.TestCase):
    def test_expected_images_exist_without_private_metadata(self):
        self.assertEqual({path.name for path in ASSETS.glob("*.png")}, EXPECTED)
        forbidden_chunks = {b"tEXt", b"zTXt", b"iTXt", b"eXIf", b"tIME"}
        for path in ASSETS.glob("*.png"):
            chunks = list(png_chunks(path))
            self.assertEqual(chunks[0][0], b"IHDR")
            self.assertEqual(chunks[-1][0], b"IEND")
            self.assertTrue(forbidden_chunks.isdisjoint(kind for kind, _ in chunks), path.name)
            raw = path.read_bytes().lower()
            for marker in (b"workflow", b"prompt", b"api_key", b"token", b"cookie", b"encoder"):
                self.assertNotIn(marker, raw, f"{path.name}: {marker!r}")


if __name__ == "__main__":
    unittest.main()
