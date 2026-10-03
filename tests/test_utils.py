"""Unit tests for utils formatting, caching, and folder statistics."""

import sys
import tempfile
import unittest
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from folder_manager.utils import format_bytes, get_folder_stats, get_cached_folder_stats, clear_stats_cache


class TestUtils(unittest.TestCase):
    """Test suite for utility helper functions."""

    def setUp(self):
        clear_stats_cache()

    def test_format_bytes(self):
        self.assertEqual(format_bytes(-1), "Calculating...")
        self.assertEqual(format_bytes(0), "0 B")
        self.assertEqual(format_bytes(512), "512 B")
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(1024 * 1024), "1.0 MB")
        self.assertEqual(format_bytes(1024 * 1024 * 1024 * 2), "2.0 GB")

    def test_get_folder_stats_and_caching(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.txt").write_text("12345")  # 5 bytes
            (root / "b.txt").write_text("1234567890")  # 10 bytes

            subdir = root / "nested"
            subdir.mkdir()
            (subdir / "c.txt").write_text("12345")  # 5 bytes

            # First call calculates and populates cache
            total_bytes, count = get_folder_stats(root)
            self.assertEqual(count, 3)
            self.assertEqual(total_bytes, 20)

            # Cached lookup returns in O(1)
            cached = get_cached_folder_stats(root)
            self.assertIsNotNone(cached)
            self.assertEqual(cached, (20, 3))

            sub_bytes, sub_count = get_folder_stats(subdir)
            self.assertEqual(sub_count, 1)
            self.assertEqual(sub_bytes, 5)


if __name__ == "__main__":
    unittest.main()
