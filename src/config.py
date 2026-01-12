"""
Configuration management for PDF Extractor.

Handles:
- Model paths and bundling
- Application settings
- Cross-platform path resolution
- Windows symlink workaround
"""

import os
import sys
import shutil
from pathlib import Path


def _patch_symlinks_for_windows():
    """
    Monkey-patch os.symlink to use file copy on Windows.

    This is necessary because Windows requires admin privileges to create symlinks,
    which causes [WinError 1314] for normal users. HuggingFace Hub uses symlinks
    extensively in its caching mechanism.
    """
    if sys.platform != "win32":
        return

    import time
    original_symlink = os.symlink

    def symlink_or_copy(src, dst, target_is_directory=False, *, dir_fd=None):
        """Replace symlink with copy on Windows to avoid privilege errors."""
        try:
            original_symlink(src, dst, target_is_directory, dir_fd=dir_fd)
        except OSError as e:
            if getattr(e, 'winerror', None) != 1314:  # Not ERROR_PRIVILEGE_NOT_HELD
                raise

            # Convert to Path objects for easier handling
            dst_path = Path(dst)
            src_path = Path(src)

            # Resolve relative symlinks (HuggingFace uses paths like "../../blobs/xxx")
            if not src_path.is_absolute():
                src_path = (dst_path.parent / src_path).resolve()
            else:
                src_path = src_path.resolve()

            # Ensure destination parent directory exists
            dst_path.parent.mkdir(parents=True, exist_ok=True)

            # Remove existing destination if present
            if dst_path.exists() or dst_path.is_symlink():
                if dst_path.is_dir() and not dst_path.is_symlink():
                    shutil.rmtree(dst_path)
                else:
                    dst_path.unlink()

            # Wait briefly for source file if it doesn't exist yet (race condition)
            if not src_path.exists():
                for _ in range(10):
                    time.sleep(0.1)
                    if src_path.exists():
                        break

            if not src_path.exists():
                raise FileNotFoundError(
                    f"Source file not found for symlink fallback: {src_path}"
                ) from e

            # Try hardlink first (works without admin on same volume, no space usage)
            try:
                os.link(src_path, dst_path)
                return
            except OSError:
                pass  # Hardlink failed, fall back to copy

            # Fall back to file copy
            if src_path.is_dir():
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)

    os.symlink = symlink_or_copy


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
    # FIRST: Patch symlinks on Windows (must happen before any HF imports)
    _patch_symlinks_for_windows()

    models_dir = get_models_dir()

    # Set Hugging Face cache directory (before any HF imports)
    hf_home = models_dir / "huggingface"
    os.environ["HF_HOME"] = str(hf_home)
    os.environ["HF_HUB_CACHE"] = str(hf_home / "hub")
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(hf_home / "hub")
    os.environ["TRANSFORMERS_CACHE"] = str(models_dir / "transformers")

    # Additional Windows symlink environment variables (belt and suspenders)
    if sys.platform == "win32":
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        os.environ["HF_HUB_LOCAL_DIR_USE_SYMLINKS"] = "False"

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
APP_VERSION = "1.0.11"
APP_AUTHOR = "Dan Ribes"
APP_IDENTIFIER = "com.pdfextractor.app"
