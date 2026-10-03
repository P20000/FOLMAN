"""CSS stylesheets and themes for the GTK 3 interface."""

MODERN_DARK_THEME = b"""
window.folder-manager {
    background-color: #1e1e2e;
    color: #cdd6f4;
}

.card {
    background-color: #181825;
    border-radius: 8px;
    padding: 12px;
    border: 1px solid #313244;
}

.section-title {
    font-weight: bold;
    font-size: 13px;
    color: #89b4fa;
}

.stats-label {
    font-size: 12px;
    color: #a6adc8;
}

button.primary-btn {
    background-color: #89b4fa;
    color: #11111b;
    font-weight: bold;
    border-radius: 6px;
    padding: 6px 14px;
}

button.primary-btn:hover {
    background-color: #b4befe;
}

button.secondary-btn {
    background-color: #313244;
    color: #cdd6f4;
    border-radius: 6px;
    padding: 6px 12px;
}

button.undo-btn {
    background-color: #f38ba8;
    color: #11111b;
    font-weight: bold;
    border-radius: 6px;
    padding: 6px 12px;
}

treeview {
    background-color: #181825;
    color: #cdd6f4;
}

treeview:selected {
    background-color: #45475a;
    color: #ffffff;
}
"""
