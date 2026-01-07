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

    For bundled apps, models are included in the package.
    For development, models are downloaded to user data dir.
    """
    if getattr(sys, 'frozen', False):
        # Bundled app - models are in the package
        return get_app_dir() / "models"
    else:
        # Development - use user cache
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

    # Set Hugging Face cache directory (used by Docling for model downloads)
    os.environ["HF_HOME"] = str(models_dir / "huggingface")
    os.environ["TRANSFORMERS_CACHE"] = str(models_dir / "transformers")

    # Ensure directories exist
    (models_dir / "huggingface").mkdir(parents=True, exist_ok=True)
    (models_dir / "transformers").mkdir(parents=True, exist_ok=True)


# Application metadata
APP_NAME = "PDF Extractor"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Your Name"
APP_IDENTIFIER = "com.yourcompany.pdfextractor"
