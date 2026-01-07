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
    Models are downloaded on first run to a user-writable location.
    """
    # Always use user-writable directory for models
    # This avoids:
    # - Windows: symlink permission issues
    # - macOS: read-only .app bundle issues
    # - All: ensures models persist across app updates
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

    # Set Hugging Face cache directory FIRST (before any HF imports)
    hf_home = models_dir / "huggingface"
    os.environ["HF_HOME"] = str(hf_home)
    os.environ["HF_HUB_CACHE"] = str(hf_home / "hub")
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(hf_home / "hub")
    os.environ["TRANSFORMERS_CACHE"] = str(models_dir / "transformers")

    # CRITICAL: Disable symlinks on Windows to avoid privilege errors
    # Windows requires admin privileges to create symlinks by default
    # This causes "[WinError 1314] A required privilege is not held by the client"
    if sys.platform == "win32":
        # Environment variables for huggingface_hub
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        os.environ["HF_HUB_LOCAL_DIR_USE_SYMLINKS"] = "False"

        # Also patch the huggingface_hub constants directly
        try:
            import huggingface_hub.constants as hf_constants
            # Force disable symlinks at the module level
            if hasattr(hf_constants, 'HF_HUB_LOCAL_DIR_USE_SYMLINKS'):
                hf_constants.HF_HUB_LOCAL_DIR_USE_SYMLINKS = False
        except ImportError:
            pass

        try:
            # Patch the file_download module if available
            from huggingface_hub import file_download
            if hasattr(file_download, 'HF_HUB_LOCAL_DIR_USE_SYMLINKS'):
                file_download.HF_HUB_LOCAL_DIR_USE_SYMLINKS = False
        except (ImportError, AttributeError):
            pass

    # macOS: Symlinks work fine, but ensure we're not writing to the .app bundle
    # The models_dir is already set to ~/Library/Application Support/PDFExtractor
    # which is user-writable and persists across app updates

    # Ensure directories exist with proper permissions
    hf_home.mkdir(parents=True, exist_ok=True)
    (hf_home / "hub").mkdir(parents=True, exist_ok=True)
    (models_dir / "transformers").mkdir(parents=True, exist_ok=True)

    # Verify the directory is writable
    test_file = hf_home / ".write_test"
    try:
        test_file.touch()
        test_file.unlink()
    except (OSError, PermissionError) as e:
        # If we can't write to the directory, fall back to temp directory
        import tempfile
        fallback_dir = Path(tempfile.gettempdir()) / "PDFExtractor" / "models"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        os.environ["HF_HOME"] = str(fallback_dir / "huggingface")
        os.environ["HF_HUB_CACHE"] = str(fallback_dir / "huggingface" / "hub")
        os.environ["TRANSFORMERS_CACHE"] = str(fallback_dir / "transformers")
        print(f"Warning: Using fallback model directory: {fallback_dir}")


# Application metadata
APP_NAME = "PDF Extractor"
APP_VERSION = "1.0.4"
APP_AUTHOR = "Dan Ribes"
APP_IDENTIFIER = "com.pdfextractor.app"
