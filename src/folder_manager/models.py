"""Data models for folder sorting configuration and operations."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict
from folder_manager.constants import SortMode, CollisionPolicy


@dataclass
class SortOptions:
    """User-configured sorting options."""
    mode: SortMode = SortMode.CATEGORY
    collision_policy: CollisionPolicy = CollisionPolicy.RENAME
    include_hidden: bool = False
    recursive: bool = False
    date_format: str = "%Y-%m"


@dataclass
class FileOperation:
    """Represents a file or folder item and its destination or current organized state."""
    source_path: Path
    target_path: Path
    group_name: str
    original_filename: str
    target_filename: str
    size_bytes: int = 0
    item_count: int = 0
    is_directory: bool = False
    icon_name: str = "text-x-generic"
    requires_move: bool = True
    executed: bool = False
    status_message: str = "Pending"
    error: Optional[str] = None


@dataclass
class SortPlan:
    """Represents the complete live preview and plan of a folder's contents."""
    root_folder: Path
    operations: List[FileOperation] = field(default_factory=list)
    options: SortOptions = field(default_factory=SortOptions)
    root_total_bytes: int = 0
    root_file_count: int = 0

    @property
    def total_files(self) -> int:
        return sum(1 for op in self.operations if not op.is_directory)

    @property
    def total_directories(self) -> int:
        return sum(1 for op in self.operations if op.is_directory)

    @property
    def pending_moves(self) -> List[FileOperation]:
        return [op for op in self.operations if op.requires_move and not op.is_directory]

    @property
    def pending_count(self) -> int:
        return sum(1 for op in self.operations if op.requires_move and not op.is_directory)

    @property
    def total_bytes(self) -> int:
        return sum(op.size_bytes for op in self.operations if not op.is_directory)

    @property
    def target_folders(self) -> Dict[str, int]:
        """Summary count of pending moves grouped by target category/folder."""
        counts: Dict[str, int] = {}
        for op in self.operations:
            if op.requires_move and not op.is_directory:
                counts[op.group_name] = counts.get(op.group_name, 0) + 1
        return counts


@dataclass
class SortStats:
    """Statistics after executing or undoing a sort plan."""
    total_planned: int = 0
    moved_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    errors: List[str] = field(default_factory=list)
