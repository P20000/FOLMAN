# Folder Manager

A modular, lightweight GTK desktop application and automated file organization utility.

[![Repository](https://img.shields.io/badge/repo-P20000/folder_manager-blue)](https://github.com/P20000/folder_manager)

---

## Features

- **Folder Tree Explorer**: Windows Explorer-style expandable sidebar tree with lazy loading of nested directories and quick location bookmarks.
- **Multiple Organization Modes**:
  - **By Category**: Organizes files into smart semantic folders (`Documents/`, `Images/`, `Audio/`, `Video/`, `Archives/`, `Code/`, etc.).
  - **By Extension**: Direct uppercase extension folders (`PDF/`, `PNG/`, `PY/`, etc.).
  - **By Date**: Temporal organization by file modification date (`YYYY-MM`).
- **Dry-Run Preview**: Inspect exactly what operations will occur before moving files.
- **Safe Collision Handling**: Auto-renames duplicates (`invoice_1.pdf`) to avoid data loss, with options to skip or overwrite.
- **One-Click Undo**: Revert moved files back to their original source locations.
- **Zero Heavy Dependencies**: Built solely on Python's standard library and `PyGObject` (`GTK 3`).

---

## How to Run

### 1. Launch the GTK GUI Application
```bash
python3 app.py
```

### 2. Command Line Interface (CLI)
You can also run Folder Manager directly from your terminal:

```bash
# Preview changes in dry-run mode
python3 app.py /path/to/messy_folder --preview

# Sort by Category with auto-rename collision policy
python3 app.py /path/to/messy_folder --mode category

# Sort by File Extension recursively
python3 app.py /path/to/messy_folder --mode extension --recursive
```

---

## Running Tests

Run the built-in test suite:
```bash
python3 -m unittest discover -s tests -v
```

---

## Architecture & Code Guidelines

This project strictly enforces:
- **Maximum 500 Lines per File** (see [AGENTS.md](AGENTS.md)).
- Modular segregation into dedicated single-responsibility components:
  - `src/folder_manager/constants.py`: Category maps and enums.
  - `src/folder_manager/models.py`: Data models (`SortPlan`, `FileOperation`, `SortOptions`, `SortStats`).
  - `src/folder_manager/sorter.py`: Core scanning, planning, execution, and undo engine.
  - `src/folder_manager/tree_explorer.py`: Expandable nested directory tree sidebar with lazy evaluation.
  - `src/folder_manager/styles.py`: GTK CSS dark theme tokens.
  - `src/folder_manager/ui.py`: Multi-threaded GTK 3 desktop application.

