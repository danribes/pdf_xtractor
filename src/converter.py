"""
Core PDF processing logic using IBM Docling.

This module handles document conversion and exports to various formats:
- JSON (lossless structured format)
- Markdown (high-fidelity text output)
- CSV/Excel (table extraction)
- HTML (web visualization)
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Callable
import json

from docling.document_converter import DocumentConverter
import pandas as pd


@dataclass
class ExportOptions:
    """Configuration for export formats."""
    json: bool = True
    markdown: bool = True
    csv: bool = True
    excel: bool = True
    html: bool = True


@dataclass
class ProcessingResult:
    """Result of document processing."""
    success: bool
    message: str
    output_files: list[str]
    table_count: int = 0
    page_count: int = 0


class PDFProcessor:
    """
    Handles PDF document conversion using IBM Docling.

    Docling provides AI-powered document understanding with:
    - Layout detection
    - Table extraction
    - Text hierarchy preservation
    """

    def __init__(self):
        self._converter = None

    @property
    def converter(self) -> DocumentConverter:
        """Lazy initialization of DocumentConverter."""
        if self._converter is None:
            self._converter = DocumentConverter()
        return self._converter

    def process(
        self,
        file_path: str | Path,
        output_folder: str | Path,
        options: ExportOptions | None = None,
        progress_callback: Callable[[str, int], None] | None = None
    ) -> ProcessingResult:
        """
        Process a PDF file and export to selected formats.

        Args:
            file_path: Path to the input PDF file.
            output_folder: Directory for output files.
            options: Export format options.
            progress_callback: Optional callback(status_message, percent).

        Returns:
            ProcessingResult with success status and output file list.
        """
        if options is None:
            options = ExportOptions()

        file_path = Path(file_path)
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        output_files = []
        base_name = file_path.stem

        try:
            if progress_callback:
                progress_callback("Converting document...", 10)

            result = self.converter.convert(str(file_path))
            doc = result.document

            if progress_callback:
                progress_callback("Document converted, exporting...", 50)

            # Export JSON (lossless structured format)
            if options.json:
                json_path = output_folder / f"{base_name}.json"
                json_output = doc.export_to_dict()
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(json_output, f, indent=4, ensure_ascii=False)
                output_files.append(str(json_path))

            if progress_callback:
                progress_callback("Exporting text formats...", 60)

            # Export Markdown (high-fidelity text)
            if options.markdown:
                md_path = output_folder / f"{base_name}.md"
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(doc.export_to_markdown())
                output_files.append(str(md_path))

            # Export HTML
            if options.html:
                html_path = output_folder / f"{base_name}.html"
                html_content = self._generate_html(doc, base_name)
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                output_files.append(str(html_path))

            if progress_callback:
                progress_callback("Extracting tables...", 75)

            # Export tables to CSV/Excel
            table_count = 0
            tables = list(doc.tables) if hasattr(doc, 'tables') else []

            for i, table in enumerate(tables):
                try:
                    # Pass doc argument to avoid deprecation warning
                    df = table.export_to_dataframe(doc=doc)

                    if options.csv:
                        csv_path = output_folder / f"{base_name}_table_{i+1}.csv"
                        df.to_csv(csv_path, index=False)
                        output_files.append(str(csv_path))

                    if options.excel:
                        xlsx_path = output_folder / f"{base_name}_table_{i+1}.xlsx"
                        df.to_excel(xlsx_path, index=False)
                        output_files.append(str(xlsx_path))

                    table_count += 1
                except Exception as e:
                    # Continue processing other tables if one fails
                    print(f"Warning: Could not export table {i}: {e}")

            if progress_callback:
                progress_callback("Complete!", 100)

            # Get page count if available
            page_count = 0
            if hasattr(doc, 'pages'):
                page_count = len(list(doc.pages))

            return ProcessingResult(
                success=True,
                message=f"Successfully processed {file_path.name}",
                output_files=output_files,
                table_count=table_count,
                page_count=page_count
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                message=f"Error processing {file_path.name}: {str(e)}",
                output_files=[]
            )

    def _generate_html(self, doc, title: str) -> str:
        """Generate styled HTML output from document."""
        # Try native HTML export if available
        if hasattr(doc, 'export_to_html'):
            try:
                return doc.export_to_html()
            except Exception:
                pass

        # Fallback: Convert markdown to basic HTML
        md_content = doc.export_to_markdown()

        # Basic markdown to HTML conversion
        import html
        content = html.escape(md_content)

        # Convert markdown headers
        lines = content.split('\n')
        html_lines = []
        for line in lines:
            if line.startswith('### '):
                html_lines.append(f'<h3>{line[4:]}</h3>')
            elif line.startswith('## '):
                html_lines.append(f'<h2>{line[3:]}</h2>')
            elif line.startswith('# '):
                html_lines.append(f'<h1>{line[2:]}</h1>')
            elif line.strip() == '':
                html_lines.append('<br>')
            else:
                html_lines.append(f'<p>{line}</p>')

        body = '\n'.join(html_lines)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.6;
        }}
        h1, h2, h3 {{ color: #333; }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1rem 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{ background-color: #f5f5f5; }}
    </style>
</head>
<body>
{body}
</body>
</html>"""
