"""Folder Tree Explorer widget with Ubuntu-style Places and solid system icons."""

from pathlib import Path
from typing import Callable, Optional, List, Tuple
import os

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


def scan_dir_children(directory: Path, show_hidden: bool = False) -> List[Tuple[Path, bool]]:
    """Return list of (subdir_path, has_nested_subdirs) in a single fast pass."""
    subdirs = []
    try:
        with os.scandir(directory) as it:
            for entry in it:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        if not show_hidden and entry.name.startswith("."):
                            continue
                        subdirs.append(Path(entry.path))
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        return []

    subdirs.sort(key=lambda p: p.name.lower())
    results = []
    for sub in subdirs:
        has_sub = False
        try:
            with os.scandir(sub) as it2:
                for subentry in it2:
                    if subentry.is_dir(follow_symlinks=False) and (show_hidden or not subentry.name.startswith(".")):
                        has_sub = True
                        break
        except (PermissionError, OSError):
            has_sub = False
        results.append((sub, has_sub))
    return results


def get_icon_for_path(path: Path) -> str:
    """Return appropriate solid Ubuntu/FreeDesktop system icon for given directory."""
    home = Path.home()
    if path == home:
        return "user-home"
    if path == home / "Desktop":
        return "user-desktop"
    if path == home / "Downloads":
        return "folder-download"
    if path == home / "Documents":
        return "folder-documents"
    if path == home / "Pictures":
        return "folder-pictures"
    if path == home / "Videos":
        return "folder-videos"
    if path == home / "Music":
        return "folder-music"
    if path == Path("/"):
        return "drive-harddisk"
    if "/media" in str(path) or "/run/media" in str(path):
        return "drive-removable-media"
    return "folder"


class FolderTreeExplorer(Gtk.Box):
    """Explorer sidebar tree with expandable nested folders and Ubuntu-style Places."""

    def __init__(self, on_folder_selected: Optional[Callable[[str], None]] = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.on_folder_selected_callback = on_folder_selected
        self.selected_path: Optional[str] = None
        self.show_hidden = False

        self._build_ui()
        self.populate_roots()

    def _build_ui(self):
        # Header Toolbar
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        top_bar.set_margin_start(4)
        top_bar.set_margin_end(4)

        icon_title = Gtk.Image.new_from_icon_name("folder", Gtk.IconSize.MENU)
        top_bar.pack_start(icon_title, False, False, 0)

        lbl = Gtk.Label(label="Files & Locations")
        lbl.get_style_context().add_class("section-title")
        top_bar.pack_start(lbl, False, False, 0)

        self.btn_refresh = Gtk.Button.new_from_icon_name("view-refresh", Gtk.IconSize.BUTTON)
        self.btn_refresh.set_tooltip_text("Refresh folders")
        self.btn_refresh.get_style_context().add_class("tool-btn")
        self.btn_refresh.connect("clicked", lambda _: self.populate_roots())
        top_bar.pack_end(self.btn_refresh, False, False, 0)

        self.btn_home = Gtk.Button.new_from_icon_name("user-home", Gtk.IconSize.BUTTON)
        self.btn_home.set_tooltip_text("Home")
        self.btn_home.get_style_context().add_class("tool-btn")
        self.btn_home.connect("clicked", lambda _: self.select_path(str(Path.home())))
        top_bar.pack_end(self.btn_home, False, False, 0)

        self.pack_start(top_bar, False, False, 0)

        # Quick Path Navigation Entry
        self.path_entry = Gtk.Entry()
        self.path_entry.set_placeholder_text("Enter folder path...")
        self.path_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, "folder-open")
        self.path_entry.connect("activate", self._on_path_entered)
        self.pack_start(self.path_entry, False, False, 2)

        # TreeStore: [icon_name (str), display_name (str), full_path (str), is_loaded (bool), is_header (bool)]
        self.store = Gtk.TreeStore(str, str, str, bool, bool)
        self.treeview = Gtk.TreeView(model=self.store)
        self.treeview.set_headers_visible(False)
        self.treeview.get_style_context().add_class("sidebar-tree")
        self.treeview.set_enable_search(True)
        self.treeview.set_search_column(1)

        col = Gtk.TreeViewColumn("Locations")
        cell_icon = Gtk.CellRendererPixbuf()
        cell_text = Gtk.CellRendererText()

        col.pack_start(cell_icon, False)
        col.add_attribute(cell_icon, "icon-name", 0)

        col.pack_start(cell_text, True)
        col.add_attribute(cell_text, "text", 1)

        self.treeview.append_column(col)
        self.treeview.connect("row-expanded", self._on_row_expanded)

        selection = self.treeview.get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        selection.connect("changed", self._on_selection_changed)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.add(self.treeview)
        self.pack_start(scrolled, True, True, 0)

    def _add_section_header(self, title: str) -> Gtk.TreeIter:
        """Add a section heading row (e.g., PLACES, DEVICES)."""
        return self.store.append(None, ["", title, "", True, True])

    def populate_roots(self):
        """Populate sidebar with Ubuntu-style Places, Locations, and Devices."""
        self.store.clear()
        home = Path.home()
        cwd = Path.cwd()

        # 1. Places Section
        iter_places = self._add_section_header("PLACES")

        # Home
        home_iter = self.store.append(iter_places, ["user-home", "Home", str(home), False, False])
        if scan_dir_children(home, self.show_hidden):
            self.store.append(home_iter, ["folder", "Loading...", "", False, False])

        # Standard User Directories
        for sub, label in [
            ("Desktop", "Desktop"),
            ("Documents", "Documents"),
            ("Downloads", "Downloads"),
            ("Music", "Music"),
            ("Pictures", "Pictures"),
            ("Videos", "Videos"),
        ]:
            p = home / sub
            if p.is_dir():
                icon = get_icon_for_path(p)
                p_iter = self.store.append(iter_places, [icon, label, str(p), False, False])
                if scan_dir_children(p, self.show_hidden):
                    self.store.append(p_iter, ["folder", "Loading...", "", False, False])

        # 2. Devices & Drives Section
        iter_devices = self._add_section_header("DEVICES & DRIVES")

        # Filesystem / Computer Root
        root_path = Path("/")
        root_iter = self.store.append(iter_devices, ["drive-harddisk", "Computer", str(root_path), False, False])
        if scan_dir_children(root_path, self.show_hidden):
            self.store.append(root_iter, ["folder", "Loading...", "", False, False])

        # Mounted Removable Drives
        user_login = os.getenv("USER") or ""
        media_paths: List[Path] = []
        for media_base in [Path(f"/run/media/{user_login}"), Path(f"/media/{user_login}"), Path("/media")]:
            if media_base.is_dir():
                try:
                    for entry in media_base.iterdir():
                        if entry.is_dir() and entry not in media_paths:
                            media_paths.append(entry)
                except (PermissionError, OSError):
                    pass

        for m_path in media_paths:
            m_iter = self.store.append(iter_devices, ["drive-removable-media", m_path.name, str(m_path), False, False])
            if scan_dir_children(m_path, self.show_hidden):
                self.store.append(m_iter, ["folder", "Loading...", "", False, False])

        # 3. Workspace (if different from Home)
        if cwd != home and cwd.is_dir():
            iter_ws = self._add_section_header("WORKSPACE")
            ws_iter = self.store.append(iter_ws, ["folder-open", cwd.name, str(cwd), False, False])
            if scan_dir_children(cwd, self.show_hidden):
                self.store.append(ws_iter, ["folder", "Loading...", "", False, False])

        # Expand section headers by default
        self.treeview.expand_all()

    def _on_row_expanded(self, _treeview, parent_iter, _path):
        """Dynamically load child directories when expanded."""
        if self.store.get_value(parent_iter, 3):
            return

        parent_path_str = self.store.get_value(parent_iter, 2)
        if not parent_path_str:
            return

        parent_path = Path(parent_path_str)

        # Clear placeholder
        child_iter = self.store.iter_children(parent_iter)
        while child_iter:
            self.store.remove(child_iter)
            child_iter = self.store.iter_children(parent_iter)

        children = scan_dir_children(parent_path, self.show_hidden)
        for subdir, has_nested in children:
            icon = get_icon_for_path(subdir)
            node = self.store.append(parent_iter, [icon, subdir.name, str(subdir), False, False])
            if has_nested:
                self.store.append(node, ["folder", "Loading...", "", False, False])

        self.store.set_value(parent_iter, 3, True)

    def _on_selection_changed(self, selection: Gtk.TreeSelection):
        """Handle folder selection from tree."""
        model, tree_iter = selection.get_selected()
        if not tree_iter:
            return

        is_header = model.get_value(tree_iter, 4)
        if is_header:
            return

        path_str = model.get_value(tree_iter, 2)
        if path_str and Path(path_str).is_dir():
            self.selected_path = path_str
            self.path_entry.set_text(path_str)
            if self.on_folder_selected_callback:
                self.on_folder_selected_callback(path_str)

    def _on_path_entered(self, entry: Gtk.Entry):
        """Handle manual path input in the entry."""
        text = entry.get_text().strip()
        if text and Path(text).is_dir():
            self.select_path(text)

    def select_path(self, target_path_str: str):
        """Set active path and notify callbacks."""
        target = Path(target_path_str).resolve()
        if not target.is_dir():
            return

        self.selected_path = str(target)
        self.path_entry.set_text(str(target))
        if self.on_folder_selected_callback:
            self.on_folder_selected_callback(str(target))
