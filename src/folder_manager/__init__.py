"""Folder Manager Package.

A modular, lightweight GTK desktop application and file organization engine.
"""

from folder_manager.constants import SortMode, CollisionPolicy, CATEGORY_MAPPINGS
from folder_manager.models import SortOptions, FileOperation, SortPlan, SortStats
from folder_manager.sorter import plan_sorting, execute_sorting, undo_sorting
from folder_manager.tree_explorer import FolderTreeExplorer
from folder_manager.ui import launch_gui
from folder_manager.utils import format_bytes, get_folder_stats

__all__ = [
    "SortMode",
    "CollisionPolicy",
    "CATEGORY_MAPPINGS",
    "SortOptions",
    "FileOperation",
    "SortPlan",
    "SortStats",
    "plan_sorting",
    "execute_sorting",
    "undo_sorting",
    "FolderTreeExplorer",
    "format_bytes",
    "get_folder_stats",
    "launch_gui",
    "mkdir_if_missing",
]



def mkdir_if_missing(path: str) -> bool:
    """Create directory `path` if it doesn't exist."""
    import os
    if os.path.isdir(path):
        return False
    os.makedirs(path, exist_ok=True)
    return True
