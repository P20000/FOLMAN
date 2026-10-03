"""Core business logic for file sorting, dry-run planning, and undo."""

import datetime
import os
from pathlib import Path
import shutil
from typing import Callable, Optional, Set, Union

from folder_manager.constants import (
    SortMode,
    CollisionPolicy,
    EXTENSION_TO_CATEGORY,
    IGNORED_DIRECTORIES,
)
from folder_manager.models import FileOperation, SortOptions, SortPlan, SortStats


def get_target_group(file_path: Path, options: SortOptions) -> str:
    """Determine the destination folder name for a given file based on sort options."""
    if options.mode == SortMode.EXTENSION:
        ext = file_path.suffix.lstrip(".").lower()
        return ext.upper() if ext else "NO_EXTENSION"

    elif options.mode == SortMode.DATE:
        try:
            mtime = file_path.stat().st_mtime
            dt = datetime.datetime.fromtimestamp(mtime)
            return dt.strftime(options.date_format)
        except Exception:
            return "UNKNOWN_DATE"

    else:  # SortMode.CATEGORY
        ext = file_path.suffix.lstrip(".").lower()
        if not ext:
            return "Other"
        return EXTENSION_TO_CATEGORY.get(ext, "Other")


def resolve_collision(
    target_folder: Path,
    filename: str,
    policy: CollisionPolicy,
    claimed_paths: Set[Path]
) -> Optional[Path]:
    """Resolve file name collisions according to policy and in-flight claimed paths."""
    candidate = target_folder / filename

    if not candidate.exists() and candidate not in claimed_paths:
        claimed_paths.add(candidate)
        return candidate

    if policy == CollisionPolicy.SKIP:
        return None

    if policy == CollisionPolicy.OVERWRITE:
        claimed_paths.add(candidate)
        return candidate

    # CollisionPolicy.RENAME: Append numeric suffix
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1

    while True:
        renamed = target_folder / f"{stem}_{counter}{suffix}"
        if not renamed.exists() and renamed not in claimed_paths:
            claimed_paths.add(renamed)
            return renamed
        counter += 1


def plan_sorting(
    folder_path: Union[str, Path],
    options: Optional[SortOptions] = None
) -> SortPlan:
    """Scan a folder and create a dry-run SortPlan without altering the disk."""
    root = Path(folder_path).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Directory does not exist: {root}")

    opts = options or SortOptions()
    operations = []
    claimed_targets: Set[Path] = set()

    # Collect candidate files
    if opts.recursive:
        walker = root.rglob("*")
    else:
        walker = root.glob("*")

    for item in walker:
        # Skip directories
        if not item.is_file():
            continue

        # Skip ignored internal directories if inside them
        if any(part in IGNORED_DIRECTORIES for part in item.relative_to(root).parts[:-1]):
            continue

        # Handle hidden files
        if not opts.include_hidden and (item.name.startswith(".") or any(p.startswith(".") for p in item.relative_to(root).parts)):
            continue

        # Determine target group and directory
        group = get_target_group(item, opts)
        target_dir = root / group

        # If file is already located directly in the target category folder, skip
        if item.parent == target_dir:
            continue

        target_path = resolve_collision(target_dir, item.name, opts.collision_policy, claimed_targets)
        if target_path is None:
            # File was skipped due to collision policy
            continue

        try:
            size = item.stat().st_size
        except OSError:
            size = 0

        operations.append(FileOperation(
            source_path=item,
            target_path=target_path,
            group_name=group,
            original_filename=item.name,
            target_filename=target_path.name,
            size_bytes=size,
            status_message="Ready"
        ))

    return SortPlan(root_folder=root, operations=operations, options=opts)


def execute_sorting(
    plan: SortPlan,
    progress_callback: Optional[Callable[[int, int, FileOperation], None]] = None
) -> SortStats:
    """Execute a planned sorting operation, moving files to their target locations."""
    stats = SortStats(total_planned=len(plan.operations))
    total = len(plan.operations)

    for idx, op in enumerate(plan.operations):
        try:
            # Ensure target parent folder exists
            op.target_path.parent.mkdir(parents=True, exist_ok=True)

            # Move file
            shutil.move(str(op.source_path), str(op.target_path))
            op.executed = True
            op.status_message = "Moved successfully"
            stats.moved_count += 1
        except Exception as exc:
            op.executed = False
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
    """Revert executed operations back to their original source locations."""
    stats = SortStats(total_planned=sum(1 for op in plan.operations if op.executed))
    total = stats.total_planned
    step = 0

    for op in reversed(plan.operations):
        if not op.executed:
            continue

        step += 1
        try:
            op.source_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(op.target_path), str(op.source_path))
            op.executed = False
            op.status_message = "Reverted"
            stats.moved_count += 1
        except Exception as exc:
            op.error = str(exc)
            op.status_message = f"Undo failed: {exc}"
            stats.failed_count += 1
            stats.errors.append(f"{op.target_filename}: {exc}")

        if progress_callback:
            progress_callback(step, total, op)

    return stats
