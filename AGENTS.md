# Project Guidelines & Rules

## 1. File Length Constraint
- **Strict 500-Line Limit:** No source file or test file shall exceed **500 lines** of code.
- Aim for compact, focused modules (typically 100–300 lines) with a single, well-defined responsibility.
- If a module grows towards the limit, proactively refactor and segregate functionality into submodules.

## 2. Code Modularity & Segregation
- Separate core logic (data models, business logic, file system operations) cleanly from user interface (GTK components) and CLI code.
- Keep helper functions, constants, and data models in dedicated modules.
- Ensure all business logic is testable without initializing the UI.

## 3. Minimal & Lightweight Dependencies
- Avoid heavy or bloated external dependencies.
- Rely primarily on the Python standard library (`pathlib`, `shutil`, `os`, `threading`, `dataclasses`, `datetime`).
- Use `PyGObject` (`gi.repository.Gtk`, `GLib`, `Gdk`) for the desktop user interface.
