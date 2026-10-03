import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from folder_manager import mkdir_if_missing


class TestBasic(unittest.TestCase):
    def test_mkdir_if_missing_creates_directory(self):
        tmpdir = tempfile.mkdtemp()
        newdir = os.path.join(tmpdir, "subdir")
        try:
            # ensure it doesn't exist yet
            self.assertFalse(os.path.exists(newdir))
            created = mkdir_if_missing(newdir)
            self.assertTrue(created)
            self.assertTrue(os.path.isdir(newdir))
            # calling again should return False
            created_again = mkdir_if_missing(newdir)
            self.assertFalse(created_again)
        finally:
            # cleanup
            if os.path.isdir(newdir):
                os.rmdir(newdir)
            if os.path.isdir(tmpdir):
                os.rmdir(tmpdir)


if __name__ == "__main__":
    unittest.main()
