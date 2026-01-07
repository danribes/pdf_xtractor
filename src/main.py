"""
PDF Extractor - Main Entry Point

Cross-platform desktop application for extracting content from PDF documents
using IBM Docling's AI-powered document understanding.
"""

import sys


def main():
    # Setup model cache before any imports that might trigger model loading
    from config import setup_docling_cache, get_default_output_dir
    setup_docling_cache()

    # Now import and run the GUI
    from gui import QApplication, QFont, MainWindow

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Set application-wide font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Set application metadata
    app.setApplicationName("PDF Extractor")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Your Company")

    window = MainWindow()

    # Update default output folder from config
    window.output_folder = str(get_default_output_dir())
    window.folder_label.setText(window.output_folder)

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
