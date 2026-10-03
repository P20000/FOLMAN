"""Unit tests for folder sorting business logic using standard library unittest."""

import sys
import tempfile
import unittest
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from folder_manager.constants import SortMode, CollisionPolicy
from folder_manager.models import SortOptions
from folder_manager.sorter import plan_sorting, execute_sorting, undo_sorting


class TestSorter(unittest.TestCase):
    """Test suite for Folder Manager sorting engine."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sample_folder = Path(self.temp_dir.name)

        # Create dummy sample files
        (self.sample_folder / "document.pdf").write_text("dummy pdf")
        (self.sample_folder / "photo.png").write_text("dummy png")
        (self.sample_folder / "song.mp3").write_text("dummy audio")
        (self.sample_folder / "script.py").write_text("print('hello')")
        (self.sample_folder / "unknown.xyz123").write_text("random")
        (self.sample_folder / ".hidden_file.txt").write_text("hidden")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_plan_and_sort_by_category(self):
        """Test sorting files into category folders."""
        options = SortOptions(mode=SortMode.CATEGORY, include_hidden=False)
        plan = plan_sorting(self.sample_folder, options)

        self.assertEqual(plan.total_files, 5)  # hidden excluded
        self.assertIn("Documents", plan.target_folders)
        self.assertIn("Images", plan.target_folders)
        self.assertIn("Audio", plan.target_folders)
        self.assertIn("Code", plan.target_folders)
        self.assertIn("Other", plan.target_folders)

        # Execute
        stats = execute_sorting(plan)
        self.assertEqual(stats.moved_count, 5)
        self.assertEqual(stats.failed_count, 0)

        self.assertTrue((self.sample_folder / "Documents" / "document.pdf").exists())
        self.assertTrue((self.sample_folder / "Images" / "photo.png").exists())
        self.assertTrue((self.sample_folder / "Audio" / "song.mp3").exists())
        self.assertTrue((self.sample_folder / "Code" / "script.py").exists())
        self.assertTrue((self.sample_folder / "Other" / "unknown.xyz123").exists())
        self.assertTrue((self.sample_folder / ".hidden_file.txt").exists())

    def test_sort_by_extension(self):
        """Test sorting files by uppercase extension."""
        options = SortOptions(mode=SortMode.EXTENSION)
        plan = plan_sorting(self.sample_folder, options)

        stats = execute_sorting(plan)
        self.assertEqual(stats.moved_count, 5)
        self.assertTrue((self.sample_folder / "PDF" / "document.pdf").exists())
        self.assertTrue((self.sample_folder / "PNG" / "photo.png").exists())
        self.assertTrue((self.sample_folder / "MP3" / "song.mp3").exists())
        self.assertTrue((self.sample_folder / "PY" / "script.py").exists())

    def test_collision_handling_rename(self):
        """Test renaming collision policy."""
        doc_folder = self.sample_folder / "Documents"
        doc_folder.mkdir()
        (doc_folder / "document.pdf").write_text("existing")

        options = SortOptions(mode=SortMode.CATEGORY, collision_policy=CollisionPolicy.RENAME)
        plan = plan_sorting(self.sample_folder, options)

        stats = execute_sorting(plan)
        self.assertEqual(stats.moved_count, 5)
        self.assertTrue((doc_folder / "document.pdf").exists())
        self.assertTrue((doc_folder / "document_1.pdf").exists())

    def test_collision_handling_skip(self):
        """Test skip collision policy."""
        doc_folder = self.sample_folder / "Documents"
        doc_folder.mkdir()
        (doc_folder / "document.pdf").write_text("existing")

        options = SortOptions(mode=SortMode.CATEGORY, collision_policy=CollisionPolicy.SKIP)
        plan = plan_sorting(self.sample_folder, options)

        stats = execute_sorting(plan)
        self.assertTrue((self.sample_folder / "document.pdf").exists())

    def test_undo_sorting(self):
        """Test reverting sorted files back to original positions."""
        options = SortOptions(mode=SortMode.CATEGORY)
        plan = plan_sorting(self.sample_folder, options)
        execute_sorting(plan)

        self.assertFalse((self.sample_folder / "photo.png").exists())
        self.assertTrue((self.sample_folder / "Images" / "photo.png").exists())

        # Undo
        undo_stats = undo_sorting(plan)
        self.assertEqual(undo_stats.moved_count, 5)
        self.assertTrue((self.sample_folder / "photo.png").exists())
        self.assertTrue((self.sample_folder / "document.pdf").exists())


if __name__ == "__main__":
    unittest.main()
