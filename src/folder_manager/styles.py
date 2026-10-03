"""Modern Ubuntu / GNOME styled CSS theme for GTK 3 interface."""

MODERN_DARK_THEME = b"""
/* Global Window Styling */
window.folder-manager {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: system-ui, -apple-system, 'Ubuntu', 'Noto Sans', sans-serif;
}

/* Resizable Divider */
paned > separator {
    background-color: #313244;
    min-width: 2px;
    margin: 0 4px;
}

/* Sidebar Styling */
.sidebar-pane {
    background-color: #181825;
    border-radius: 8px;
    padding: 8px;
    border: 1px solid #313244;
}

.sidebar-heading {
    font-size: 11px;
    font-weight: 700;
    color: #6c7086;
    letter-spacing: 0.8px;
    padding: 6px 4px 2px 4px;
}

/* Cards & Content Containers */
.card {
    background-color: #181825;
    border-radius: 8px;
    padding: 8px 12px;
    border: 1px solid #313244;
}

.section-title {
    font-weight: 600;
    font-size: 13px;
    color: #89b4fa;
}

.stats-label {
    font-size: 12px;
    color: #a6adc8;
}

/* Path Pill */
.path-badge {
    font-family: 'Ubuntu Mono', monospace;
    font-size: 12px;
    color: #a6e3a1;
    background-color: #11111b;
    padding: 5px 10px;
    border-radius: 6px;
    border: 1px solid #313244;
}

/* Primary Action Buttons */
button.primary-action-btn {
    background-color: #89b4fa;
    color: #11111b;
    font-weight: 600;
    font-size: 13px;
    border-radius: 6px;
    padding: 6px 14px;
    border: none;
    transition: all 150ms ease;
}

button.primary-action-btn:hover {
    background-color: #b4befe;
}

button.primary-action-btn:disabled {
    background-color: #313244;
    color: #585b70;
}

/* Secondary & Toolbar Buttons */
button.tool-btn {
    background-color: #313244;
    color: #cdd6f4;
    border-radius: 6px;
    padding: 5px 10px;
    border: 1px solid #45475a;
}

button.tool-btn:hover {
    background-color: #45475a;
}

button.tool-btn:disabled {
    background-color: #181825;
    color: #585b70;
    border-color: #313244;
}

/* Linked Navigation Buttons */
.linked > button {
    border-radius: 0;
    border-right-width: 0;
}
.linked > button:first-child {
    border-top-left-radius: 6px;
    border-bottom-left-radius: 6px;
}
.linked > button:last-child {
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    border-right-width: 1px;
}

/* Undo / Revert Button */
button.undo-action-btn {
    background-color: #313244;
    color: #f38ba8;
    font-weight: 600;
    border-radius: 6px;
    padding: 6px 12px;
    border: 1px solid #45475a;
}

button.undo-action-btn:hover {
    background-color: #f38ba8;
    color: #11111b;
}

button.undo-action-btn:disabled {
    background-color: #181825;
    color: #585b70;
    border-color: #313244;
}

/* TreeView & ListStore */
treeview {
    background-color: #181825;
    color: #cdd6f4;
    border-radius: 6px;
}

treeview:selected {
    background-color: #45475a;
    color: #ffffff;
}

treeview.sidebar-tree {
    background-color: transparent;
}

/* Inputs & Combos */
entry {
    background-color: #11111b;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 5px 8px;
}

entry:focus {
    border-color: #89b4fa;
}

combobox button {
    background-color: #11111b;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 4px 8px;
}

/* Progress Bar */
progressbar trough {
    background-color: #11111b;
    border: 1px solid #313244;
    border-radius: 4px;
    min-height: 8px;
}

progressbar progress {
    background-color: #89b4fa;
    border-radius: 3px;
}
"""
