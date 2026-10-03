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
    date_format: str = "%Y-%m"  # e.g., '2026-10' or '%Y/%B'


@dataclass
class FileOperation:
    """Represents a planned or executed file move."""
    source_path: Path
    target_path: Path
    group_name: str
    original_filename: str
    target_filename: str
    size_bytes: int = 0
    executed: bool = False
    status_message: str = "Pending"
    error: Optional[str] = None


@dataclass
class SortPlan:
    """Represents the complete dry-run plan before execution."""
    root_folder: Path
    operations: List[FileOperation] = field(default_factory=list)
    options: SortOptions = field(default_factory=SortOptions)

    @property
    def total_files(self) -> int:
        return len(self.operations)

    @property
    def total_bytes(self) -> int:
        return sum(op.size_bytes for op in self.operations)

    @property
    def target_folders(self) -> Dict[str, int]:
        """Summary count of files grouped by target folder name."""
        counts: Dict[str, int] = {}
        for op in self.operations:
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
