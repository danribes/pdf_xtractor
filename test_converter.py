#!/usr/bin/env python3
"""Test script for the PDF converter."""

import sys
sys.path.insert(0, 'src')

from pathlib import Path
from converter import PDFProcessor, ExportOptions

def progress_callback(message, percent):
    print(f"  [{percent:3d}%] {message}")

def main():
    pdf_path = Path("test_sample.pdf")
    output_dir = Path("test_output")

    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return 1

    print(f"Testing PDF Extractor with: {pdf_path}")
    print(f"Output directory: {output_dir}")
    print("-" * 50)

    processor = PDFProcessor()
    options = ExportOptions(
        json=True,
        markdown=True,
        csv=True,
        excel=True,
        html=True
    )

    result = processor.process(
        pdf_path,
        output_dir,
        options,
        progress_callback=progress_callback
    )

    print("-" * 50)
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    print(f"Tables found: {result.table_count}")
    print(f"Pages: {result.page_count}")
    print(f"\nOutput files ({len(result.output_files)}):")
    for f in result.output_files:
        size = Path(f).stat().st_size
        print(f"  - {Path(f).name} ({size:,} bytes)")

    return 0 if result.success else 1

if __name__ == "__main__":
    sys.exit(main())
