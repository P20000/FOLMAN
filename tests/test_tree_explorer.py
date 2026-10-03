"""Unit tests for optimized FolderTreeExplorer and tree helper functions."""

import sys
import tempfile
import unittest
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from folder_manager.tree_explorer import (
    scan_dir_children,
    get_icon_for_path,
)


class TestTreeExplorer(unittest.TestCase):
    """Test suite for tree explorer directory scanning."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scan_dir_children_empty_and_files(self):
        # Empty directory
        self.assertEqual(scan_dir_children(self.root), [])

        # Add only a file
        (self.root / "sample.txt").write_text("content")
        self.assertEqual(scan_dir_children(self.root), [])

    def test_scan_dir_children_subdirs_and_nesting(self):
        sub_alpha = self.root / "alpha"
        sub_beta = self.root / "beta"
        sub_hidden = self.root / ".hidden_folder"

        sub_alpha.mkdir()
        sub_beta.mkdir()
        sub_hidden.mkdir()

        # Nested folder inside alpha
        (sub_alpha / "nested_inside").mkdir()

        # Without hidden
        visible = scan_dir_children(self.root, show_hidden=False)
        self.assertEqual(len(visible), 2)
        self.assertEqual(visible[0], (sub_alpha, True))   # alpha has nested dirs
        self.assertEqual(visible[1], (sub_beta, False))   # beta has no nested dirs

        # With hidden
        all_dirs = scan_dir_children(self.root, show_hidden=True)
        names = [d[0].name for d in all_dirs]
        self.assertEqual(names, [".hidden_folder", "alpha", "beta"])

    def test_get_icon_for_path(self):
        home = Path.home()
        self.assertEqual(get_icon_for_path(home), "user-home")
        self.assertEqual(get_icon_for_path(home / "Downloads"), "folder-download")
        self.assertEqual(get_icon_for_path(Path("/")), "drive-harddisk")
        self.assertEqual(get_icon_for_path(self.root), "folder")


if __name__ == "__main__":
    unittest.main()
