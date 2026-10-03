#!/usr/bin/env python3
"""Folder Manager - Entry Point.

Launches the GTK 3 desktop application by default, or runs in CLI mode.
"""

import argparse
import sys
from pathlib import Path

# Add src to sys.path so folder_manager can be imported without installation
sys.path.insert(0, str(Path(__file__).parent / "src"))

from folder_manager import (
    SortMode,
    CollisionPolicy,
    SortOptions,
    plan_sorting,
    execute_sorting,
    launch_gui,
)


def run_cli(folder_path: str, mode: str, collision: str, recursive: bool, preview: bool):
    """Run folder sorting directly from the command line."""
    folder = Path(folder_path).resolve()
    if not folder.is_dir():
        print(f"❌ Error: '{folder}' is not a valid directory.")
        sys.exit(1)

    options = SortOptions(
        mode=SortMode(mode),
        collision_policy=CollisionPolicy(collision),
        recursive=recursive,
    )

    print(f"🔍 Scanning '{folder}' [Mode: {mode}, Collision: {collision}]...")
    plan = plan_sorting(folder, options)

    if not plan.operations:
        print("✨ Folder is already organized! No files to move.")
        return

    print(f"\n📋 Planned operations ({plan.total_files} files):")
    for op in plan.operations:
        rel_target = op.target_path.relative_to(plan.root_folder)
        print(f"  • {op.original_filename} → {rel_target}")

    if preview:
        print("\n🔎 Dry-run preview complete. No files were moved.")
        return

    confirm = input("\nProceed with moving files? [y/N]: ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Aborted.")
        return

    print("\n⚡ Executing...")
    stats = execute_sorting(
        plan,
        progress_callback=lambda cur, tot, op: print(f"[{cur}/{tot}] {op.original_filename} -> {op.group_name}")
    )
    print(f"\n🎯 Done! Moved: {stats.moved_count}, Skipped: {stats.skipped_count}, Failed: {stats.failed_count}")


def main():
    parser = argparse.ArgumentParser(description="Folder Manager — Smart File Organizer")
    parser.add_argument("folder", nargs="?", help="Folder path to sort (CLI mode)")
    parser.add_argument("--cli", action="store_true", help="Force CLI mode")
    parser.add_argument("--mode", choices=["category", "extension", "date"], default="category", help="Sorting strategy")
    parser.add_argument("--collision", choices=["rename", "skip", "overwrite"], default="rename", help="Collision policy")
    parser.add_argument("--recursive", "-r", action="store_true", help="Recursively process subdirectories")
    parser.add_argument("--preview", "-p", action="store_true", help="Dry run / preview only (CLI)")

    args = parser.parse_args()

    if args.folder or args.cli:
        target = args.folder or input("Enter folder path: ").strip()
        run_cli(target, args.mode, args.collision, args.recursive, args.preview)
    else:
        try:
            launch_gui()
        except Exception as e:
            print(f"Failed to launch GTK GUI: {e}")
            print("Falling back to CLI mode.")
            target = input("Enter folder path: ").strip()
            run_cli(target, args.mode, args.collision, args.recursive, args.preview)


if __name__ == "__main__":
    main()
