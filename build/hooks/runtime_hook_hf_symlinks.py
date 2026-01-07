"""
Runtime hook to disable HuggingFace symlinks on Windows.

This hook runs BEFORE any other code, ensuring the environment
variables are set before huggingface_hub is imported.
"""

import os
import sys

if sys.platform == "win32":
    # Disable symlinks - Windows requires admin privileges for symlinks
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    os.environ["HF_HUB_LOCAL_DIR_USE_SYMLINKS"] = "False"

    # Also set the newer variable name
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
