"""
Configuration management for PDF Extractor.

Handles:
- Model paths and bundling
- Application settings
- Cross-platform path resolution
"""

import os
import sys
from pathlib import Path


def get_app_dir() -> Path:
    """Get the application directory (handles PyInstaller bundling)."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys._MEIPASS)
    else:
        # Running as script
        return Path(__file__).parent


def get_data_dir() -> Path:
    """Get the user data directory for storing settings and cache."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    data_dir = base / "PDFExtractor"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_models_dir() -> Path:
    """
    Get the directory for Docling model weights.

    Always use user data directory to avoid permission issues.
    Models are downloaded on first run.
    """
    # Always use user-writable directory for models
    # This avoids symlink permission issues on Windows
    models_dir = get_data_dir() / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


def get_default_output_dir() -> Path:
    """Get the default output directory for processed files."""
    output_dir = Path.home() / "Documents" / "PDF_Extractor_Output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def setup_docling_cache():
    """
    Configure Docling to use the correct model cache directory.

    Call this before initializing DocumentConverter.
    """
    models_dir = get_models_dir()

    # CRITICAL: Disable symlinks on Windows to avoid privilege errors
    # Windows requires admin privileges to create symlinks by default
    # Setting HF_HUB_DISABLE_SYMLINKS_WARNING suppresses the warning
    # Setting HF_HUB_LOCAL_DIR_USE_SYMLINKS to False disables symlink creation
    if sys.platform == "win32":
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        os.environ["HF_HUB_LOCAL_DIR_USE_SYMLINKS"] = "False"

    # Set Hugging Face cache directory (used by Docling for model downloads)
    hf_home = models_dir / "huggingface"
    os.environ["HF_HOME"] = str(hf_home)
    os.environ["HF_HUB_CACHE"] = str(hf_home / "hub")
    os.environ["TRANSFORMERS_CACHE"] = str(models_dir / "transformers")

    # Ensure directories exist
    hf_home.mkdir(parents=True, exist_ok=True)
    (hf_home / "hub").mkdir(parents=True, exist_ok=True)
    (models_dir / "transformers").mkdir(parents=True, exist_ok=True)


# Application metadata
APP_NAME = "PDF Extractor"
APP_VERSION = "1.0.2"
APP_AUTHOR = "Dan Ribes"
APP_IDENTIFIER = "com.pdfextractor.app"
