"""Utility helper functions for formatting, cached disk statistics, and GTK widgets."""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

# In-memory LRU/dict cache for folder stats: path_str -> (mtime, total_bytes, file_count)
_FOLDER_STATS_CACHE: Dict[str, Tuple[float, int, int]] = {}


def format_bytes(size: int) -> str:
    """Format bytes into readable human format."""
    if size < 0:
        return "Calculating..."
    if size == 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
        size /= 1024.0
    return f"{size:.1f} PB"


def get_cached_folder_stats(folder: Path) -> Optional[Tuple[int, int]]:
    """Retrieve folder statistics from cache in O(1) if mtime is unchanged."""
    path_key = str(folder)
    try:
        mtime = folder.stat().st_mtime
        cached = _FOLDER_STATS_CACHE.get(path_key)
        if cached and cached[0] == mtime:
            return cached[1], cached[2]
    except (PermissionError, OSError):
        pass
    return None


def get_folder_stats(folder: Path, include_hidden: bool = False) -> Tuple[int, int]:
    """Calculate (total_size_bytes, file_count) for a directory with automatic caching."""
    cached = get_cached_folder_stats(folder)
    if cached is not None:
        return cached

    total_bytes = 0
    file_count = 0
    stack = [folder]

    while stack:
        current_dir = stack.pop()
        try:
            with os.scandir(current_dir) as it:
                for entry in it:
                    try:
                        name = entry.name
                        if not include_hidden and name.startswith("."):
                            continue

                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            total_bytes += entry.stat().st_size
                            file_count += 1
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            continue

    # Update cache
    try:
        mtime = folder.stat().st_mtime
        _FOLDER_STATS_CACHE[str(folder)] = (mtime, total_bytes, file_count)
    except (PermissionError, OSError):
        pass

    return total_bytes, file_count


def clear_stats_cache():
    """Clear in-memory folder statistics cache."""
    _FOLDER_STATS_CACHE.clear()


def create_icon_button(icon_name: str, label_text: str, css_class: str) -> Gtk.Button:
    """Helper to build consistent GTK button with system icon and label."""
    btn = Gtk.Button()
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
    lbl = Gtk.Label(label=label_text)
    box.pack_start(icon, False, False, 0)
    box.pack_start(lbl, False, False, 0)
    btn.add(box)
    btn.get_style_context().add_class(css_class)
    return btn


def show_error_dialog(parent: Gtk.Window, message: str):
    """Display an error message dialog transient to parent window."""
    dialog = Gtk.MessageDialog(
        transient_for=parent,
        flags=0,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text="Operation Error"
    )
    dialog.format_secondary_text(message)
    dialog.run()
    dialog.destroy()

