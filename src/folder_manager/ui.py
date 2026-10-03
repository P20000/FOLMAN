"""GTK 3 Graphical User Interface for Folder Manager."""

from pathlib import Path
import threading
from typing import Optional

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango

from folder_manager.constants import SortMode, CollisionPolicy
from folder_manager.models import SortOptions, SortPlan, FileOperation
from folder_manager.sorter import plan_sorting, execute_sorting, undo_sorting
from folder_manager.styles import MODERN_DARK_THEME


def format_bytes(size: int) -> str:
    """Format bytes into readable human format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
        size /= 1024.0
    return f"{size:.1f} PB"


class FolderManagerWindow(Gtk.Window):
    """Main application window for Folder Manager."""

    def __init__(self):
        super().__init__(title="Folder Manager — Smart File Organizer")
        self.set_default_size(880, 620)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.get_style_context().add_class("folder-manager")

        self.current_plan: Optional[SortPlan] = None
        self.is_busy = False

        self._apply_styling()
        self._build_ui()

    def _apply_styling(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(MODERN_DARK_THEME)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _build_ui(self):
        # Header bar
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.props.title = "Folder Manager"
        header.props.subtitle = "Fast, modular desktop file organizer"
        self.set_titlebar(header)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        main_box.set_margin_start(14)
        main_box.set_margin_end(14)
        self.add(main_box)

        # 1. Folder Selection Row
        folder_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        folder_card.get_style_context().add_class("card")

        lbl_folder = Gtk.Label(label="📁 Target Folder:")
        lbl_folder.get_style_context().add_class("section-title")
        folder_card.pack_start(lbl_folder, False, False, 0)

        self.file_chooser = Gtk.FileChooserButton(
            title="Select folder to organize",
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        self.file_chooser.set_current_folder(str(Path.home()))
        self.file_chooser.connect("file-set", self._on_folder_selected)
        folder_card.pack_start(self.file_chooser, True, True, 0)

        main_box.pack_start(folder_card, False, False, 0)

        # 2. Options Card
        options_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        options_card.get_style_context().add_class("card")

        # Mode Selector
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        mode_box.pack_start(Gtk.Label(label="Sort Mode:"), False, False, 0)
        self.mode_combo = Gtk.ComboBoxText()
        self.mode_combo.append(SortMode.CATEGORY, "By Category (Docs, Images, Code...)")
        self.mode_combo.append(SortMode.EXTENSION, "By Extension (.PDF, .PNG...)")
        self.mode_combo.append(SortMode.DATE, "By Date (YYYY-MM)")
        self.mode_combo.set_active_id(SortMode.CATEGORY)
        self.mode_combo.connect("changed", self._on_options_changed)
        mode_box.pack_start(self.mode_combo, False, False, 0)
        options_card.pack_start(mode_box, False, False, 0)

        # Collision Selector
        collision_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        collision_box.pack_start(Gtk.Label(label="Collisions:"), False, False, 0)
        self.collision_combo = Gtk.ComboBoxText()
        self.collision_combo.append(CollisionPolicy.RENAME, "Auto-Rename (_1, _2)")
        self.collision_combo.append(CollisionPolicy.SKIP, "Skip existing")
        self.collision_combo.append(CollisionPolicy.OVERWRITE, "Overwrite")
        self.collision_combo.set_active_id(CollisionPolicy.RENAME)
        self.collision_combo.connect("changed", self._on_options_changed)
        collision_box.pack_start(self.collision_combo, False, False, 0)
        options_card.pack_start(collision_box, False, False, 0)

        # Checkboxes
        self.chk_recursive = Gtk.CheckButton(label="Recursive (subfolders)")
        self.chk_recursive.connect("toggled", self._on_options_changed)
        options_card.pack_start(self.chk_recursive, False, False, 0)

        self.chk_hidden = Gtk.CheckButton(label="Include Hidden")
        self.chk_hidden.connect("toggled", self._on_options_changed)
        options_card.pack_start(self.chk_hidden, False, False, 0)

        main_box.pack_start(options_card, False, False, 0)

        # 3. Action Toolbar & Summary
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self.btn_preview = Gtk.Button(label="🔍 Preview Organization")
        self.btn_preview.get_style_context().add_class("secondary-btn")
        self.btn_preview.connect("clicked", self._on_preview_clicked)
        actions_box.pack_start(self.btn_preview, False, False, 0)

        self.btn_sort = Gtk.Button(label="⚡ Sort Files Now")
        self.btn_sort.get_style_context().add_class("primary-btn")
        self.btn_sort.set_sensitive(False)
        self.btn_sort.connect("clicked", self._on_sort_clicked)
        actions_box.pack_start(self.btn_sort, False, False, 0)

        self.btn_undo = Gtk.Button(label="↩ Undo Last Sort")
        self.btn_undo.get_style_context().add_class("undo-btn")
        self.btn_undo.set_sensitive(False)
        self.btn_undo.connect("clicked", self._on_undo_clicked)
        actions_box.pack_start(self.btn_undo, False, False, 0)

        self.lbl_summary = Gtk.Label(label="Select a folder and click Preview to begin.")
        self.lbl_summary.get_style_context().add_class("stats-label")
        self.lbl_summary.set_xalign(1.0)
        actions_box.pack_end(self.lbl_summary, True, True, 0)

        main_box.pack_start(actions_box, False, False, 0)

        # 4. Preview Table (ListStore & TreeView)
        self.liststore = Gtk.ListStore(str, str, str, str, str)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.treeview.set_rules_hint(True)

        col_names = ["File Name", "Size", "Group / Folder", "Target Path", "Status"]
        col_widths = [200, 80, 120, 260, 120]

        for i, title in enumerate(col_names):
            renderer = Gtk.CellRendererText()
            renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
            col = Gtk.TreeViewColumn(title, renderer, text=i)
            col.set_resizable(True)
            col.set_min_width(col_widths[i])
            self.treeview.append_column(col)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.add(self.treeview)
        main_box.pack_start(scrolled, True, True, 0)

        # 5. Progress Bar & Status
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_fraction(0.0)
        status_box.pack_start(self.progress_bar, True, True, 0)

        self.lbl_status = Gtk.Label(label="Ready")
        status_box.pack_start(self.lbl_status, False, False, 0)
        main_box.pack_start(status_box, False, False, 0)

    def _get_selected_options(self) -> SortOptions:
        return SortOptions(
            mode=SortMode(self.mode_combo.get_active_id() or SortMode.CATEGORY),
            collision_policy=CollisionPolicy(self.collision_combo.get_active_id() or CollisionPolicy.RENAME),
            include_hidden=self.chk_hidden.get_active(),
            recursive=self.chk_recursive.get_active()
        )

    def _on_folder_selected(self, widget):
        self._on_options_changed(widget)

    def _on_options_changed(self, _widget):
        self.current_plan = None
        self.btn_sort.set_sensitive(False)
        self.lbl_summary.set_text("Options changed. Click Preview to view updated plan.")

    def _set_busy(self, busy: bool):
        self.is_busy = busy
        self.file_chooser.set_sensitive(not busy)
        self.btn_preview.set_sensitive(not busy)
        self.btn_sort.set_sensitive(not busy and (self.current_plan is not None and len(self.current_plan.operations) > 0))
        self.mode_combo.set_sensitive(not busy)
        self.collision_combo.set_sensitive(not busy)
        self.chk_recursive.set_sensitive(not busy)
        self.chk_hidden.set_sensitive(not busy)

    def _on_preview_clicked(self, _button):
        folder = self.file_chooser.get_filename()
        if not folder or not Path(folder).is_dir():
            self.lbl_status.set_text("Please choose a valid directory.")
            return

        options = self._get_selected_options()
        self._set_busy(True)
        self.lbl_status.set_text("Scanning and generating preview...")
        self.progress_bar.set_fraction(0.0)

        def worker():
            try:
                plan = plan_sorting(folder, options)
                GLib.idle_add(self._display_preview, plan)
            except Exception as e:
                GLib.idle_add(self._display_error, f"Preview failed: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _display_preview(self, plan: SortPlan):
        self.current_plan = plan
        self.liststore.clear()

        for op in plan.operations:
            rel_target = str(op.target_path.relative_to(plan.root_folder))
            self.liststore.append([
                op.original_filename,
                format_bytes(op.size_bytes),
                op.group_name,
                rel_target,
                op.status_message
            ])

        groups = plan.target_folders
        group_summary = ", ".join(f"{k}: {v}" for k, v in sorted(groups.items()))
        total_size = format_bytes(plan.total_bytes)

        if plan.total_files > 0:
            self.lbl_summary.set_text(f"Plan: {plan.total_files} files ({total_size}) into {len(groups)} folders [{group_summary}]")
            self.btn_sort.set_sensitive(True)
            self.lbl_status.set_text("Preview ready.")
        else:
            self.lbl_summary.set_text("No files require moving.")
            self.btn_sort.set_sensitive(False)
            self.lbl_status.set_text("Folder already clean / organized.")

        self._set_busy(False)

    def _on_sort_clicked(self, _button):
        if not self.current_plan or not self.current_plan.operations:
            return

        self._set_busy(True)
        self.btn_undo.set_sensitive(False)
        self.lbl_status.set_text("Sorting files in progress...")

        def on_progress(current: int, total: int, op: FileOperation):
            def update():
                self.progress_bar.set_fraction(current / max(total, 1))
                self.lbl_status.set_text(f"Processing ({current}/{total}): {op.original_filename}")
                if current - 1 < len(self.liststore):
                    row_iter = self.liststore.get_iter(Gtk.TreePath.new_from_string(str(current - 1)))
                    if row_iter:
                        self.liststore.set_value(row_iter, 4, op.status_message)
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
        self.btn_sort.set_sensitive(False)
        self.btn_undo.set_sensitive(stats.moved_count > 0)
        self.progress_bar.set_fraction(1.0)
        msg = f"Done! Moved: {stats.moved_count}, Skipped: {stats.skipped_count}, Failed: {stats.failed_count}"
        self.lbl_status.set_text(msg)
        self.lbl_summary.set_text(msg)

    def _on_undo_clicked(self, _button):
        if not self.current_plan:
            return

        self._set_busy(True)
        self.lbl_status.set_text("Undoing operations...")

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
        self.btn_sort.set_sensitive(True)
        self.progress_bar.set_fraction(1.0)
        msg = f"Undo Complete. Reverted {stats.moved_count} files."
        self.lbl_status.set_text(msg)
        self.lbl_summary.set_text(msg)

        for row in self.liststore:
            row[4] = "Reverted (Ready)"

    def _display_error(self, message: str):
        self._set_busy(False)
        self.lbl_status.set_text(f"Error: {message}")
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Operation Error"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()


def launch_gui():
    """Launch the GTK 3 Folder Manager window."""
    win = FolderManagerWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    launch_gui()
