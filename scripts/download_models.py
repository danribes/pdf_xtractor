#!/usr/bin/env python3
"""
Download Docling models for offline bundling.

Run this script before building the application to include
models in the distributable package.

Usage:
    python scripts/download_models.py
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


def main():
    print("=" * 60)
    print("PDF Extractor - Model Downloader")
    print("=" * 60)
    print()

    # Set up model directory
    models_dir = Path(__file__).parent.parent / 'models'
    models_dir.mkdir(parents=True, exist_ok=True)

    # Configure cache directories
    os.environ["HF_HOME"] = str(models_dir / "huggingface")
    os.environ["TRANSFORMERS_CACHE"] = str(models_dir / "transformers")

    print(f"Model directory: {models_dir}")
    print()
    print("Downloading models... This may take a few minutes.")
    print()

    try:
        # Import Docling and trigger model download
        from docling.document_converter import DocumentConverter

        print("Initializing DocumentConverter (this downloads models)...")
        converter = DocumentConverter()

        # Optionally process a simple test to ensure all models are cached
        print("Models downloaded successfully!")
        print()
        print(f"Total size: {get_dir_size(models_dir):.1f} MB")
        print()
        print("You can now build the application with bundled models:")
        print("  pyinstaller build/pdfextractor.spec")

    except ImportError as e:
        print(f"Error: Could not import docling. Install it first:")
        print(f"  pip install docling")
        print(f"\nDetails: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error downloading models: {e}")
        sys.exit(1)


def get_dir_size(path: Path) -> float:
    """Get directory size in MB."""
    total = 0
    for file in path.rglob('*'):
        if file.is_file():
            total += file.stat().st_size
    return total / (1024 * 1024)


if __name__ == "__main__":
    main()
