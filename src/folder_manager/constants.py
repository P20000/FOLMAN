"""Constants and category definitions for FOLMAN."""

from enum import Enum
from typing import Dict, List, Set


class SortMode(str, Enum):
    """Supported sorting modes."""
    EXTENSION = "extension"
    CATEGORY = "category"
    DATE = "date"


class CollisionPolicy(str, Enum):
    """Policies for handling file name collisions in target directory."""
    RENAME = "rename"  # Appends _1, _2, etc.
    SKIP = "skip"      # Skips moving this file
    OVERWRITE = "overwrite"  # Replaces existing file


# Default extension mappings into clean human-friendly categories
CATEGORY_MAPPINGS: Dict[str, List[str]] = {
    "Documents": [
        "pdf", "docx", "doc", "txt", "rtf", "odt", "tex", "wpd", "md", "markdown"
    ],
    "Spreadsheets": [
        "xlsx", "xls", "csv", "ods", "tsv"
    ],
    "Presentations": [
        "pptx", "ppt", "odp", "key"
    ],
    "Images": [
        "jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "tiff", "tif",
        "ico", "raw", "heic", "psd", "ai"
    ],
    "Videos": [
        "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "mpg", "mpeg"
    ],
    "Audio": [
        "mp3", "wav", "aac", "flac", "ogg", "m4a", "wma", "opus"
    ],
    "Archives": [
        "zip", "tar", "gz", "bz2", "xz", "7z", "rar", "tgz", "iso", "dmg"
    ],
    "Code": [
        "py", "js", "ts", "html", "css", "json", "xml", "yaml", "yml",
        "java", "c", "cpp", "h", "hpp", "cs", "go", "rs", "rb", "php",
        "sh", "bash", "zsh", "sql", "lua", "kt", "swift"
    ],
    "Executables": [
        "exe", "msi", "appimage", "deb", "rpm", "pkg", "apk", "bin"
    ],
    "Fonts": [
        "ttf", "otf", "woff", "woff2", "eot"
    ],
    "Ebooks": [
        "epub", "mobi", "azw", "azw3", "djvu"
    ]
}

# Inverted lookup cache: extension -> category name
EXTENSION_TO_CATEGORY: Dict[str, str] = {}
for category, extensions in CATEGORY_MAPPINGS.items():
    for ext in extensions:
        EXTENSION_TO_CATEGORY[ext.lower()] = category

# Standard directory names to skip unless explicitly instructed
IGNORED_DIRECTORIES: Set[str] = {
    ".git", ".svn", ".hg", ".venv", "venv", "env",
    "__pycache__", ".pytest_cache", ".mypy_cache",
    "node_modules", ".idea", ".vscode"
}
