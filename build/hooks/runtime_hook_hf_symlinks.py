"""
Runtime hook to disable HuggingFace symlinks on Windows.

This hook runs BEFORE any other code, ensuring symlinks are patched
before huggingface_hub is imported.

Fixes [WinError 1314] "A required privilege is not held by the client"
which occurs when creating symlinks without Developer Mode or Admin rights.
"""

import os
import sys
import shutil
import time
from pathlib import Path

if sys.platform == "win32":
    # Disable symlinks via environment variables
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    os.environ["HF_HUB_LOCAL_DIR_USE_SYMLINKS"] = "False"
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

    # Monkey-patch os.symlink to use file copy instead
    # This is the most reliable fix for [WinError 1314]
    _original_symlink = os.symlink

    def _symlink_or_copy(src, dst, target_is_directory=False, *, dir_fd=None):
        """Replace symlink with copy on Windows to avoid privilege errors."""
        try:
            _original_symlink(src, dst, target_is_directory, dir_fd=dir_fd)
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
            # HuggingFace sometimes creates symlinks before the blob is fully written
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

    os.symlink = _symlink_or_copy
