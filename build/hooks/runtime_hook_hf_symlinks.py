"""
Runtime hook to disable HuggingFace symlinks on Windows.

This hook runs BEFORE any other code, ensuring symlinks are patched
before huggingface_hub is imported.
"""

import os
import sys
import shutil
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
            if getattr(e, 'winerror', None) == 1314:  # ERROR_PRIVILEGE_NOT_HELD
                src_path = Path(src)
                dst_path = Path(dst)

                # Handle relative symlinks (HuggingFace uses these)
                if not src_path.is_absolute():
                    src_path = dst_path.parent / src_path

                try:
                    if src_path.is_dir():
                        if dst_path.exists():
                            shutil.rmtree(dst_path)
                        shutil.copytree(src_path, dst_path)
                    else:
                        dst_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_path, dst_path)
                except Exception:
                    raise e
            else:
                raise

    os.symlink = _symlink_or_copy
