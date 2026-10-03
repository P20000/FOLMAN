"""GTK 3 Graphical User Interface with Ubuntu-style layout, navigation history, and live preview."""

from pathlib import Path
import threading
from typing import List, Optional

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango

from folder_manager.constants import SortMode, CollisionPolicy
from folder_manager.models import SortOptions, SortPlan, FileOperation
from folder_manager.sorter import plan_sorting, execute_sorting, undo_sorting
from folder_manager.styles import MODERN_DARK_THEME
from folder_manager.tree_explorer import FolderTreeExplorer
from folder_manager.utils import format_bytes, get_folder_stats, create_icon_button, show_error_dialog


class FolderManagerWindow(Gtk.Window):
    """Main application window with cached asynchronous folder sizes and live preview."""

    def __init__(self):
        super().__init__(title="FOLMAN")
        self.set_default_size(1060, 700)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.get_style_context().add_class("folder-manager")

        initial_folder = str(Path.home())
        self.current_folder: str = initial_folder
        self.current_plan: Optional[SortPlan] = None
        self.is_busy = False
        self._scan_counter = 0

        # Navigation History Stack
        self.history: List[str] = [initial_folder]
        self.history_index: int = 0
        self._is_navigating_history = False

        self._apply_styling()
        self._build_ui()
        self._update_nav_buttons()
        self._trigger_live_scan()

    def _apply_styling(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(MODERN_DARK_THEME)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _build_ui(self):
        # GNOME Header Bar
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.props.title = "FOLMAN"
        header.props.subtitle = "Fast Desktop File Organizer"
        self.set_titlebar(header)

        # Paned Layout: Left Sidebar (Places / Devices) | Right Main Panel
        self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.paned.set_position(260)
        self.paned.set_margin_top(10)
        self.paned.set_margin_bottom(10)
        self.paned.set_margin_start(12)
        self.paned.set_margin_end(12)
        self.add(self.paned)

        # Left Sidebar (Places & Explorer)
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        left_box.get_style_context().add_class("sidebar-pane")
        self.tree_explorer = FolderTreeExplorer(on_folder_selected=self._on_tree_folder_selected)
        left_box.pack_start(self.tree_explorer, True, True, 0)
        self.paned.pack1(left_box, resize=False, shrink=False)

        # Right Main Panel
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        right_box.set_margin_start(8)
        self.paned.pack2(right_box, resize=True, shrink=False)

        # 1. Location Bar Card with Linked Navigation Controls
        location_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        location_card.get_style_context().add_class("card")

        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        nav_box.get_style_context().add_class("linked")

        self.btn_back = Gtk.Button.new_from_icon_name("go-previous-symbolic", Gtk.IconSize.BUTTON)
        self.btn_back.set_tooltip_text("Go back")
        self.btn_back.get_style_context().add_class("tool-btn")
        self.btn_back.connect("clicked", self._on_back_clicked)
        nav_box.pack_start(self.btn_back, False, False, 0)

        self.btn_forward = Gtk.Button.new_from_icon_name("go-next-symbolic", Gtk.IconSize.BUTTON)
        self.btn_forward.set_tooltip_text("Go forward")
        self.btn_forward.get_style_context().add_class("tool-btn")
        self.btn_forward.connect("clicked", self._on_forward_clicked)
        nav_box.pack_start(self.btn_forward, False, False, 0)

        self.btn_up = Gtk.Button.new_from_icon_name("go-up", Gtk.IconSize.BUTTON)
        self.btn_up.set_tooltip_text("Open parent directory")
        self.btn_up.get_style_context().add_class("tool-btn")
        self.btn_up.connect("clicked", self._on_go_up_clicked)
        nav_box.pack_start(self.btn_up, False, False, 0)

        location_card.pack_start(nav_box, False, False, 0)

        loc_icon = Gtk.Image.new_from_icon_name("folder-open", Gtk.IconSize.MENU)
        location_card.pack_start(loc_icon, False, False, 0)

        lbl_loc = Gtk.Label(label="Location:")
        lbl_loc.get_style_context().add_class("section-title")
        location_card.pack_start(lbl_loc, False, False, 0)

        self.lbl_selected_path = Gtk.Label(label=str(Path.home()))
        self.lbl_selected_path.get_style_context().add_class("path-badge")
        self.lbl_selected_path.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self.lbl_selected_path.set_xalign(0.0)
        location_card.pack_start(self.lbl_selected_path, True, True, 0)
        right_box.pack_start(location_card, False, False, 0)

        # 2. Options Card
        options_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        options_card.get_style_context().add_class("card")

        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        mode_box.pack_start(Gtk.Label(label="Strategy:"), False, False, 0)
        self.mode_combo = Gtk.ComboBoxText()
        self.mode_combo.append(SortMode.CATEGORY, "By Category (Docs, Media, Code)")
        self.mode_combo.append(SortMode.EXTENSION, "By Extension (.PDF, .PNG)")
        self.mode_combo.append(SortMode.DATE, "By Date (YYYY-MM)")
        self.mode_combo.set_active_id(SortMode.CATEGORY)
        self.mode_combo.connect("changed", lambda _: self._trigger_live_scan())
        mode_box.pack_start(self.mode_combo, False, False, 0)
        options_card.pack_start(mode_box, False, False, 0)

        col_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        col_box.pack_start(Gtk.Label(label="Duplicates:"), False, False, 0)
        self.collision_combo = Gtk.ComboBoxText()
        self.collision_combo.append(CollisionPolicy.RENAME, "Auto-Rename (_1, _2)")
        self.collision_combo.append(CollisionPolicy.SKIP, "Skip")
        self.collision_combo.append(CollisionPolicy.OVERWRITE, "Replace")
        self.collision_combo.set_active_id(CollisionPolicy.RENAME)
        self.collision_combo.connect("changed", lambda _: self._trigger_live_scan())
        col_box.pack_start(self.collision_combo, False, False, 0)
        options_card.pack_start(col_box, False, False, 0)

        self.chk_recursive = Gtk.CheckButton(label="Recursive")
        self.chk_recursive.connect("toggled", lambda _: self._trigger_live_scan())
        options_card.pack_start(self.chk_recursive, False, False, 0)

        self.chk_hidden = Gtk.CheckButton(label="Hidden Files")
        self.chk_hidden.connect("toggled", lambda _: self._trigger_live_scan())
        options_card.pack_start(self.chk_hidden, False, False, 0)
        right_box.pack_start(options_card, False, False, 0)

        # 3. Action Toolbar & Summary Bar
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.btn_sort = create_icon_button("system-run", "Organize Files", "primary-action-btn")
        self.btn_sort.set_sensitive(False)
        self.btn_sort.connect("clicked", self._on_sort_clicked)
        actions_box.pack_start(self.btn_sort, False, False, 0)

        self.btn_undo = create_icon_button("edit-undo", "Undo", "undo-action-btn")
        self.btn_undo.set_sensitive(False)
        self.btn_undo.connect("clicked", self._on_undo_clicked)
        actions_box.pack_start(self.btn_undo, False, False, 0)

        self.lbl_summary = Gtk.Label(label="Scanning directory...")
        self.lbl_summary.get_style_context().add_class("stats-label")
        self.lbl_summary.set_xalign(1.0)
        actions_box.pack_end(self.lbl_summary, True, True, 0)
        right_box.pack_start(actions_box, False, False, 0)

        # 4. Live Contents Table (ListStore & TreeView)
        self.liststore = Gtk.ListStore(str, str, str, str, str, str, str, bool)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.treeview.set_rules_hint(True)
        self.treeview.connect("row-activated", self._on_row_activated)

        col_name = Gtk.TreeViewColumn("Name")
        cell_icon = Gtk.CellRendererPixbuf()
        cell_name = Gtk.CellRendererText()
        cell_name.set_property("ellipsize", Pango.EllipsizeMode.END)
        col_name.pack_start(cell_icon, False)
        col_name.add_attribute(cell_icon, "icon-name", 0)
        col_name.pack_start(cell_name, True)
        col_name.add_attribute(cell_name, "text", 1)
        col_name.set_resizable(True)
        col_name.set_min_width(240)
        self.treeview.append_column(col_name)

        other_cols = [
            ("Size", 2, 110),
            ("Destination", 3, 120),
            ("Target Path", 4, 180),
            ("Status", 5, 140)
        ]
        for title, model_idx, width in other_cols:
            renderer = Gtk.CellRendererText()
            renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
            col = Gtk.TreeViewColumn(title, renderer, text=model_idx)
            col.set_resizable(True)
            col.set_min_width(width)
            self.treeview.append_column(col)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.add(self.treeview)
        right_box.pack_start(scrolled, True, True, 0)

        # 5. Status Bar
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_fraction(0.0)
        status_box.pack_start(self.progress_bar, True, True, 0)

        status_icon = Gtk.Image.new_from_icon_name("dialog-information", Gtk.IconSize.MENU)
        status_box.pack_start(status_icon, False, False, 0)

        self.lbl_status = Gtk.Label(label="Ready")
        status_box.pack_start(self.lbl_status, False, False, 0)
        right_box.pack_start(status_box, False, False, 0)

    def _get_selected_options(self) -> SortOptions:
        return SortOptions(
            mode=SortMode(self.mode_combo.get_active_id() or SortMode.CATEGORY),
            collision_policy=CollisionPolicy(self.collision_combo.get_active_id() or CollisionPolicy.RENAME),
            include_hidden=self.chk_hidden.get_active(),
            recursive=self.chk_recursive.get_active()
        )

    def _update_nav_buttons(self):
        """Update sensitivity of navigation buttons based on current state."""
        self.btn_back.set_sensitive(not self.is_busy and self.history_index > 0)
        self.btn_forward.set_sensitive(not self.is_busy and self.history_index < len(self.history) - 1)
        curr = Path(self.current_folder)
        self.btn_up.set_sensitive(not self.is_busy and curr.parent != curr and curr.parent.is_dir())

    def _on_tree_folder_selected(self, folder_path: str):
        if not self._is_navigating_history:
            if self.history[self.history_index] != folder_path:
                self.history = self.history[:self.history_index + 1]
                self.history.append(folder_path)
                self.history_index = len(self.history) - 1

        self.current_folder = folder_path
        self.lbl_selected_path.set_text(folder_path)
        self._update_nav_buttons()
        self._trigger_live_scan()

    def _on_back_clicked(self, _button):
        if self.history_index > 0:
            self.history_index -= 1
            target = self.history[self.history_index]
            self._is_navigating_history = True
            try:
                self.tree_explorer.select_path(target)
            finally:
                self._is_navigating_history = False

    def _on_forward_clicked(self, _button):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            target = self.history[self.history_index]
            self._is_navigating_history = True
            try:
                self.tree_explorer.select_path(target)
            finally:
                self._is_navigating_history = False

    def _on_go_up_clicked(self, _button):
        curr = Path(self.current_folder)
        if curr.parent and curr.parent != curr and curr.parent.is_dir():
            self.tree_explorer.select_path(str(curr.parent))

    def _on_row_activated(self, treeview, path, _column):
        """Handle double-click on a row to navigate into nested folders."""
        model = treeview.get_model()
        tree_iter = model.get_iter(path)
        if not tree_iter:
            return

        is_dir = model.get_value(tree_iter, 7)
        full_path_str = model.get_value(tree_iter, 6)

        if is_dir and full_path_str and Path(full_path_str).is_dir():
            self.tree_explorer.select_path(full_path_str)

    def _trigger_live_scan(self):
        """Immediately scan and live-update the contents table with background size loading."""
        if not self.current_folder or not Path(self.current_folder).is_dir():
            return

        self._scan_counter += 1
        current_req = self._scan_counter
        options = self._get_selected_options()

        self.lbl_status.set_text("Scanning contents...")
        self.progress_bar.set_fraction(0.0)

        def worker():
            try:
                plan = plan_sorting(self.current_folder, options)
                if current_req == self._scan_counter:
                    GLib.idle_add(self._display_live_preview, plan, current_req)
            except Exception as e:
                if current_req == self._scan_counter:
                    GLib.idle_add(self._display_error, f"Folder scan failed: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _display_live_preview(self, plan: SortPlan, scan_id: int):
        self.current_plan = plan
        self.liststore.clear()

        has_pending_sizes = False

        for op in plan.operations:
            if op.is_directory:
                if op.size_bytes < 0:
                    size_str = "Calculating..."
                    has_pending_sizes = True
                elif op.item_count > 0:
                    size_str = f"{format_bytes(op.size_bytes)} ({op.item_count} items)"
                else:
                    size_str = "Empty"
                rel_target = "—"
            else:
                size_str = format_bytes(op.size_bytes)
                rel_target = str(op.target_path.relative_to(plan.root_folder))

            self.liststore.append([
                op.icon_name,
                op.original_filename,
                size_str,
                op.group_name,
                rel_target,
                op.status_message,
                str(op.source_path),
                op.is_directory
            ])

        pending = plan.pending_count
        files_cnt = plan.total_files
        dirs_cnt = plan.total_directories
        total_size = format_bytes(plan.root_total_bytes)
        groups = plan.target_folders
        group_summary = ", ".join(f"{k}: {v}" for k, v in sorted(groups.items()))

        summary_text = f"{files_cnt} files, {dirs_cnt} folders ({total_size})"
        if pending > 0:
            self.lbl_summary.set_text(f"{summary_text} — {pending} to organize [{group_summary}]")
            self.btn_sort.set_sensitive(not self.is_busy)
            self.lbl_status.set_text(f"{pending} files ready.")
        else:
            self.lbl_summary.set_text(f"{summary_text} — All organized.")
            self.btn_sort.set_sensitive(False)
            self.lbl_status.set_text("Organized.")

        # Background async worker to compute un-cached subfolder sizes progressively
        if has_pending_sizes:
            threading.Thread(target=self._async_load_folder_sizes, args=(plan, scan_id), daemon=True).start()

    def _async_load_folder_sizes(self, plan: SortPlan, scan_id: int):
        """Asynchronously compute subfolder sizes on the go and update row items live."""
        for idx, op in enumerate(plan.operations):
            if scan_id != self._scan_counter:
                return
            if op.is_directory and op.size_bytes < 0:
                b_size, count = get_folder_stats(op.source_path, include_hidden=plan.options.include_hidden)
                op.size_bytes = b_size
                op.item_count = count
                if scan_id == self._scan_counter:
                    GLib.idle_add(self._update_row_size, idx, b_size, count)

    def _update_row_size(self, row_idx: int, size_bytes: int, item_count: int):
        """Live update a single folder row with its calculated size."""
        if row_idx < len(self.liststore):
            tree_iter = self.liststore.get_iter(Gtk.TreePath.new_from_string(str(row_idx)))
            if tree_iter:
                size_str = f"{format_bytes(size_bytes)} ({item_count} items)" if item_count > 0 else "Empty"
                self.liststore.set_value(tree_iter, 2, size_str)

    def _set_busy(self, busy: bool):
        self.is_busy = busy
        self.tree_explorer.set_sensitive(not busy)
        self._update_nav_buttons()
        self.btn_sort.set_sensitive(not busy and (self.current_plan is not None and self.current_plan.pending_count > 0))
        self.mode_combo.set_sensitive(not busy)
        self.collision_combo.set_sensitive(not busy)
        self.chk_recursive.set_sensitive(not busy)
        self.chk_hidden.set_sensitive(not busy)

    def _on_sort_clicked(self, _button):
        if not self.current_plan or not self.current_plan.pending_moves:
            return

        self._set_busy(True)
        self.btn_undo.set_sensitive(False)
        self.lbl_status.set_text("Organizing files in progress...")

        def on_progress(current: int, total: int, op: FileOperation):
            def update():
                self.progress_bar.set_fraction(current / max(total, 1))
                self.lbl_status.set_text(f"Moving ({current}/{total}): {op.original_filename}")
            GLib.idle_add(update)

        def worker():
            try:
                stats = execute_sorting(self.current_plan, progress_callback=on_progress)
                GLib.idle_add(self._on_sort_finished, stats)
            except Exception as e:
                GLib.idle_add(self._display_error, f"Execution failed: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _on_sort_finished(self, stats):
        self._set_busy(False)
        self.btn_undo.set_sensitive(stats.moved_count > 0)
        self.progress_bar.set_fraction(1.0)
        msg = f"Complete: {stats.moved_count} moved, {stats.skipped_count} skipped, {stats.failed_count} errors"
        self.lbl_status.set_text(msg)
        self._trigger_live_scan()
        self.tree_explorer.populate_roots()

    def _on_undo_clicked(self, _button):
        if not self.current_plan:
            return

        self._set_busy(True)
        self.lbl_status.set_text("Reverting operations...")

        def on_progress(current: int, total: int, op: FileOperation):
            def update():
                self.progress_bar.set_fraction(current / max(total, 1))
                self.lbl_status.set_text(f"Reverting ({current}/{total}): {op.original_filename}")
            GLib.idle_add(update)

        def worker():
            try:
                stats = undo_sorting(self.current_plan, progress_callback=on_progress)
                GLib.idle_add(self._on_undo_finished, stats)
            except Exception as e:
                GLib.idle_add(self._display_error, f"Undo failed: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _on_undo_finished(self, stats):
        self._set_busy(False)
        self.btn_undo.set_sensitive(False)
        self.progress_bar.set_fraction(1.0)
        self.lbl_status.set_text(f"Reverted {stats.moved_count} files.")
        self._trigger_live_scan()
        self.tree_explorer.populate_roots()

    def _display_error(self, message: str):
        self._set_busy(False)
        self.lbl_status.set_text(f"Error: {message}")
        show_error_dialog(self, message)


def launch_gui():
    """Launch the GTK 3 FOLMAN window."""
    win = FolderManagerWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    launch_gui()
