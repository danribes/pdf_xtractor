"""
PySide6 Desktop GUI for PDF Extractor.

Features:
- Drag and drop PDF files
- Format selection checkboxes
- Progress indicator
- Output folder selection
"""

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, QMimeData
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QCheckBox, QProgressBar, QFileDialog,
    QGroupBox, QListWidget, QListWidgetItem, QMessageBox,
    QFrame, QSplitter, QTextEdit
)
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont, QPalette, QColor

from converter import PDFProcessor, ExportOptions, ProcessingResult


class ProcessingWorker(QThread):
    """Background worker for PDF processing."""
    progress = Signal(str, int)  # message, percent
    finished = Signal(ProcessingResult)

    def __init__(self, processor: PDFProcessor, file_path: str,
                 output_folder: str, options: ExportOptions):
        super().__init__()
        self.processor = processor
        self.file_path = file_path
        self.output_folder = output_folder
        self.options = options

    def run(self):
        result = self.processor.process(
            self.file_path,
            self.output_folder,
            self.options,
            progress_callback=self.progress.emit
        )
        self.finished.emit(result)


class DropZone(QFrame):
    """Drag-and-drop zone for PDF files."""
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(150)
        self.setFrameStyle(QFrame.Box | QFrame.Sunken)
        self._setup_ui()
        self._update_style(False)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.icon_label = QLabel("📄")
        self.icon_label.setFont(QFont("Segoe UI Emoji", 48))
        self.icon_label.setAlignment(Qt.AlignCenter)

        self.text_label = QLabel("Drag & Drop PDF files here\nor click to browse")
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setFont(QFont("Segoe UI", 12))

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)

    def _update_style(self, hovering: bool):
        if hovering:
            self.setStyleSheet("""
                DropZone {
                    background-color: #e3f2fd;
                    border: 3px dashed #2196f3;
                    border-radius: 10px;
                }
            """)
        else:
            self.setStyleSheet("""
                DropZone {
                    background-color: #f5f5f5;
                    border: 3px dashed #cccccc;
                    border-radius: 10px;
                }
                DropZone:hover {
                    background-color: #eeeeee;
                    border-color: #999999;
                }
            """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(url.toLocalFile().lower().endswith('.pdf') for url in urls):
                event.acceptProposedAction()
                self._update_style(True)
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._update_style(False)

    def dropEvent(self, event: QDropEvent):
        self._update_style(False)
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.pdf'):
                files.append(file_path)
        if files:
            self.files_dropped.emit(files)

    def mousePressEvent(self, event):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select PDF Files", "",
            "PDF Files (*.pdf);;All Files (*)"
        )
        if files:
            self.files_dropped.emit(files)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.processor = PDFProcessor()
        self.output_folder = str(Path.home() / "Documents" / "PDF_Extractor_Output")
        self.pending_files: list[str] = []
        self.current_worker: Optional[ProcessingWorker] = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        self.setWindowTitle("PDF Extractor - Powered by IBM Docling")
        self.setMinimumSize(700, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("PDF Extractor")
        header.setFont(QFont("Segoe UI", 24, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        subtitle = QLabel("Extract text, tables, and structured data from PDF documents")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)

        # Drop zone
        self.drop_zone = DropZone()
        layout.addWidget(self.drop_zone)

        # Main content area
        content_layout = QHBoxLayout()

        # Left side - Options
        options_group = QGroupBox("Export Formats")
        options_layout = QVBoxLayout(options_group)

        self.cb_json = QCheckBox("JSON (Structured data)")
        self.cb_json.setChecked(True)
        self.cb_markdown = QCheckBox("Markdown (Plain text)")
        self.cb_markdown.setChecked(True)
        self.cb_csv = QCheckBox("CSV (Tables)")
        self.cb_csv.setChecked(True)
        self.cb_excel = QCheckBox("Excel (Tables)")
        self.cb_excel.setChecked(True)
        self.cb_html = QCheckBox("HTML (Web view)")
        self.cb_html.setChecked(True)

        for cb in [self.cb_json, self.cb_markdown, self.cb_csv,
                   self.cb_excel, self.cb_html]:
            options_layout.addWidget(cb)

        options_layout.addStretch()
        content_layout.addWidget(options_group)

        # Right side - File queue
        queue_group = QGroupBox("File Queue")
        queue_layout = QVBoxLayout(queue_group)
        self.file_list = QListWidget()
        self.file_list.setMinimumWidth(300)
        queue_layout.addWidget(self.file_list)

        btn_layout = QHBoxLayout()
        self.btn_clear = QPushButton("Clear")
        self.btn_remove = QPushButton("Remove Selected")
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addWidget(self.btn_remove)
        queue_layout.addLayout(btn_layout)

        content_layout.addWidget(queue_group, stretch=1)
        layout.addLayout(content_layout)

        # Output folder selection
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Output Folder:"))
        self.folder_label = QLabel(self.output_folder)
        self.folder_label.setStyleSheet("""
            background-color: #f0f0f0;
            padding: 8px;
            border-radius: 4px;
        """)
        folder_layout.addWidget(self.folder_label, stretch=1)
        self.btn_browse = QPushButton("Browse...")
        folder_layout.addWidget(self.btn_browse)
        layout.addLayout(folder_layout)

        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.status_label)

        layout.addWidget(progress_group)

        # Process button
        self.btn_process = QPushButton("Process Files")
        self.btn_process.setMinimumHeight(50)
        self.btn_process.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.btn_process.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.btn_process.setEnabled(False)
        layout.addWidget(self.btn_process)

    def _connect_signals(self):
        self.drop_zone.files_dropped.connect(self._add_files)
        self.btn_clear.clicked.connect(self._clear_files)
        self.btn_remove.clicked.connect(self._remove_selected)
        self.btn_browse.clicked.connect(self._browse_folder)
        self.btn_process.clicked.connect(self._start_processing)

    def _add_files(self, files: list[str]):
        for file_path in files:
            if file_path not in self.pending_files:
                self.pending_files.append(file_path)
                item = QListWidgetItem(Path(file_path).name)
                item.setData(Qt.UserRole, file_path)
                item.setToolTip(file_path)
                self.file_list.addItem(item)
        self._update_process_button()

    def _clear_files(self):
        self.pending_files.clear()
        self.file_list.clear()
        self._update_process_button()

    def _remove_selected(self):
        for item in self.file_list.selectedItems():
            file_path = item.data(Qt.UserRole)
            if file_path in self.pending_files:
                self.pending_files.remove(file_path)
            self.file_list.takeItem(self.file_list.row(item))
        self._update_process_button()

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", self.output_folder
        )
        if folder:
            self.output_folder = folder
            self.folder_label.setText(folder)

    def _update_process_button(self):
        has_files = len(self.pending_files) > 0
        not_processing = self.current_worker is None
        self.btn_process.setEnabled(has_files and not_processing)

    def _get_export_options(self) -> ExportOptions:
        return ExportOptions(
            json=self.cb_json.isChecked(),
            markdown=self.cb_markdown.isChecked(),
            csv=self.cb_csv.isChecked(),
            excel=self.cb_excel.isChecked(),
            html=self.cb_html.isChecked()
        )

    def _start_processing(self):
        if not self.pending_files:
            return

        self._set_processing_state(True)
        self._process_next_file()

    def _process_next_file(self):
        if not self.pending_files:
            self._set_processing_state(False)
            self.status_label.setText("All files processed!")
            QMessageBox.information(
                self, "Complete",
                f"All files have been processed.\n\nOutput folder:\n{self.output_folder}"
            )
            return

        file_path = self.pending_files[0]
        self.status_label.setText(f"Processing: {Path(file_path).name}")

        self.current_worker = ProcessingWorker(
            self.processor,
            file_path,
            self.output_folder,
            self._get_export_options()
        )
        self.current_worker.progress.connect(self._on_progress)
        self.current_worker.finished.connect(self._on_file_finished)
        self.current_worker.start()

    def _on_progress(self, message: str, percent: int):
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    def _on_file_finished(self, result: ProcessingResult):
        self.current_worker = None

        if result.success:
            # Remove processed file from queue
            if self.pending_files:
                self.pending_files.pop(0)
            if self.file_list.count() > 0:
                self.file_list.takeItem(0)
        else:
            QMessageBox.warning(self, "Error", result.message)
            # Still remove failed file to continue
            if self.pending_files:
                self.pending_files.pop(0)
            if self.file_list.count() > 0:
                self.file_list.takeItem(0)

        self._process_next_file()

    def _set_processing_state(self, processing: bool):
        self.btn_process.setEnabled(not processing)
        self.drop_zone.setEnabled(not processing)
        self.btn_clear.setEnabled(not processing)
        self.btn_remove.setEnabled(not processing)

        if not processing:
            self.progress_bar.setValue(0)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Set application-wide font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
