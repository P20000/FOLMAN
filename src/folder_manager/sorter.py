"""High-performance file and folder sorting, direct preview, and undo engine."""

import datetime
import os
from pathlib import Path
import shutil
from typing import Callable, List, Optional, Set, Tuple, Union

from folder_manager.constants import (
    SortMode,
    CollisionPolicy,
    EXTENSION_TO_CATEGORY,
    IGNORED_DIRECTORIES,
)
from folder_manager.models import FileOperation, SortOptions, SortPlan, SortStats
from folder_manager.utils import get_cached_folder_stats, get_folder_stats

# Mapping from category to solid FreeDesktop system icon
CATEGORY_ICONS = {
    "Documents": "x-office-document",
    "Spreadsheets": "x-office-spreadsheet",
    "Presentations": "x-office-presentation",
    "Images": "image-x-generic",
    "Videos": "video-x-generic",
    "Audio": "audio-x-generic",
    "Archives": "package-x-generic",
    "Code": "text-x-script",
    "Executables": "system-run",
    "Fonts": "font-x-generic",
    "Ebooks": "x-office-document",
    "Folder": "folder",
}


def get_icon_for_category(group: str, is_dir: bool = False) -> str:
    """Return appropriate solid system icon name."""
    if is_dir:
        return "folder"
    return CATEGORY_ICONS.get(group, "text-x-generic")


def get_target_group_fast(name: str, mtime: float, options: SortOptions) -> str:
    """Quickly determine the target destination category or group."""
    dot_idx = name.rfind(".")
    ext = name[dot_idx + 1:].lower() if (dot_idx > 0 and dot_idx < len(name) - 1) else ""

    if options.mode == SortMode.EXTENSION:
        return ext.upper() if ext else "NO_EXTENSION"
    elif options.mode == SortMode.DATE:
        try:
            return datetime.datetime.fromtimestamp(mtime).strftime(options.date_format)
        except Exception:
            return "UNKNOWN_DATE"
    else:  # SortMode.CATEGORY
        return EXTENSION_TO_CATEGORY.get(ext, "Other") if ext else "Other"


def resolve_collision_fast(
    target_folder: Path,
    filename: str,
    policy: CollisionPolicy,
    claimed_targets: Set[Path]
) -> Optional[Path]:
    """Resolve file collision using cached set of claimed paths for speed."""
    candidate = target_folder / filename

    if not candidate.exists() and candidate not in claimed_targets:
        claimed_targets.add(candidate)
        return candidate

    if policy == CollisionPolicy.SKIP:
        return None
    if policy == CollisionPolicy.OVERWRITE:
        claimed_targets.add(candidate)
        return candidate

    # RENAME policy
    dot_idx = filename.rfind(".")
    stem = filename[:dot_idx] if dot_idx > 0 else filename
    suffix = filename[dot_idx:] if dot_idx > 0 else ""
    counter = 1

    while True:
        renamed = target_folder / f"{stem}_{counter}{suffix}"
        if not renamed.exists() and renamed not in claimed_targets:
            claimed_targets.add(renamed)
            return renamed
        counter += 1


def scan_entries_fast(root: Path, recursive: bool, include_hidden: bool) -> Tuple[List[Path], List[tuple]]:
    """Fast single-pass scan returning (direct_subdirs, file_entries)."""
    file_results = []
    direct_subdirs = []
    stack = [root]

    while stack:
        current_dir = stack.pop()
        is_root = (current_dir == root)
        try:
            with os.scandir(current_dir) as it:
                for entry in it:
                    try:
                        name = entry.name
                        if not include_hidden and name.startswith("."):
                            continue

                        if entry.is_dir(follow_symlinks=False):
                            if name not in IGNORED_DIRECTORIES:
                                if is_root:
                                    direct_subdirs.append(Path(entry.path))
                                if recursive:
                                    stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            stat = entry.stat()
                            file_results.append((Path(entry.path), name, stat.st_size, stat.st_mtime, Path(current_dir)))
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            continue

    direct_subdirs.sort(key=lambda p: p.name.lower())
    return direct_subdirs, file_results


def plan_sorting(
    folder_path: Union[str, Path],
    options: Optional[SortOptions] = None
) -> SortPlan:
    """Scan folder and build complete direct preview of subfolders, files, and planned moves."""
    root = Path(folder_path).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Directory does not exist: {root}")

    opts = options or SortOptions()
    direct_subdirs, raw_files = scan_entries_fast(root, opts.recursive, opts.include_hidden)
    operations: List[FileOperation] = []
    claimed_targets: Set[Path] = set()

    # 1. Add direct child folders at top of list
    for subdir in direct_subdirs:
        cached = get_cached_folder_stats(subdir)
        dir_bytes = cached[0] if cached else -1
        item_count = cached[1] if cached else 0

        operations.append(FileOperation(
            source_path=subdir,
            target_path=subdir,
            group_name="Folder",
            original_filename=subdir.name,
            target_filename=subdir.name,
            size_bytes=dir_bytes,
            item_count=item_count,
            is_directory=True,
            icon_name="folder",
            requires_move=False,
            status_message="Double-click to open"
        ))

    # 2. Add files
    for file_path, name, size, mtime, parent_dir in raw_files:
        group = get_target_group_fast(name, mtime, opts)
        target_dir = root / group
        icon = get_icon_for_category(group, is_dir=False)

        # If file is already inside its designated category folder, it's organized
        if parent_dir == target_dir:
            operations.append(FileOperation(
                source_path=file_path,
                target_path=file_path,
                group_name=group,
                original_filename=name,
                target_filename=name,
                size_bytes=size,
                is_directory=False,
                icon_name=icon,
                requires_move=False,
                status_message="Organized"
            ))
            continue

        target_path = resolve_collision_fast(target_dir, name, opts.collision_policy, claimed_targets)
        if target_path is None:
            operations.append(FileOperation(
                source_path=file_path,
                target_path=file_path,
                group_name=group,
                original_filename=name,
                target_filename=name,
                size_bytes=size,
                is_directory=False,
                icon_name=icon,
                requires_move=False,
                status_message="Skipped (Collision)"
            ))
            continue

        operations.append(FileOperation(
            source_path=file_path,
            target_path=target_path,
            group_name=group,
            original_filename=name,
            target_filename=target_path.name,
            size_bytes=size,
            is_directory=False,
            icon_name=icon,
            requires_move=True,
            status_message="Ready to move"
        ))

    root_cached = get_cached_folder_stats(root)
    root_bytes = root_cached[0] if root_cached else sum(op.size_bytes for op in operations if not op.is_directory)
    root_count = root_cached[1] if root_cached else len(raw_files)

    return SortPlan(
        root_folder=root,
        operations=operations,
        options=opts,
        root_total_bytes=root_bytes,
        root_file_count=root_count
    )


def execute_sorting(
    plan: SortPlan,
    progress_callback: Optional[Callable[[int, int, FileOperation], None]] = None
) -> SortStats:
    """Execute pending moves with optimized directory creation."""
    pending = [op for op in plan.operations if op.requires_move and not op.is_directory and not op.executed]
    stats = SortStats(total_planned=len(pending))
    total = len(pending)
    created_dirs: Set[Path] = set()

    for idx, op in enumerate(pending):
        try:
            parent_dir = op.target_path.parent
            if parent_dir not in created_dirs:
                parent_dir.mkdir(parents=True, exist_ok=True)
                created_dirs.add(parent_dir)

            shutil.move(str(op.source_path), str(op.target_path))
            op.executed = True
            op.requires_move = False
            op.status_message = "Moved"
            stats.moved_count += 1
        except Exception as exc:
            op.error = str(exc)
            op.status_message = f"Failed: {exc}"
            stats.failed_count += 1
            stats.errors.append(f"{op.original_filename}: {exc}")

        if progress_callback:
            progress_callback(idx + 1, total, op)

    return stats


def undo_sorting(
    plan: SortPlan,
    progress_callback: Optional[Callable[[int, int, FileOperation], None]] = None
) -> SortStats:
    """Revert executed operations back to original source paths."""
    executed_ops = [op for op in plan.operations if op.executed and not op.is_directory]
    stats = SortStats(total_planned=len(executed_ops))
    total = len(executed_ops)
    created_dirs: Set[Path] = set()

    for idx, op in enumerate(reversed(executed_ops)):
        try:
            parent_dir = op.source_path.parent
            if parent_dir not in created_dirs:
                parent_dir.mkdir(parents=True, exist_ok=True)
                created_dirs.add(parent_dir)

            shutil.move(str(op.target_path), str(op.source_path))
            op.executed = False
            op.requires_move = True
            op.status_message = "Reverted"
            stats.moved_count += 1
        except Exception as exc:
            op.error = str(exc)
            op.status_message = f"Undo error: {exc}"
            stats.failed_count += 1
            stats.errors.append(f"{op.target_filename}: {exc}")

        if progress_callback:
            progress_callback(idx + 1, total, op)

    return stats
