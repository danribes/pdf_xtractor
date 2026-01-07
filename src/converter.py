"""
Core PDF processing logic using IBM Docling.

This module handles document conversion and exports to various formats:
- JSON (lossless structured format)
- Markdown (high-fidelity text output)
- CSV/Excel (table extraction)
- HTML (web visualization)
- Images (extracted pictures/figures)
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Callable
import json

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableFormerMode,
    OcrOptions,
)
import pandas as pd


@dataclass
class ExportOptions:
    """Configuration for export formats."""
    json: bool = True
    markdown: bool = True
    csv: bool = True
    excel: bool = True
    html: bool = True
    images: bool = True  # Extract pictures/figures as image files


@dataclass
class ProcessingResult:
    """Result of document processing."""
    success: bool
    message: str
    output_files: list[str]
    table_count: int = 0
    page_count: int = 0
    picture_count: int = 0


class PDFProcessor:
    """
    Handles PDF document conversion using IBM Docling.

    Docling provides AI-powered document understanding with:
    - Layout detection
    - Table extraction with ACCURATE mode
    - Text hierarchy preservation
    - OCR for scanned documents
    - Picture/figure extraction
    - Formula and code detection
    """

    def __init__(self):
        self._converter = None

    def _create_pipeline_options(self) -> PdfPipelineOptions:
        """Create comprehensive pipeline options for exhaustive extraction."""
        pipeline_options = PdfPipelineOptions()

        # Enable OCR for scanned documents and images
        pipeline_options.do_ocr = True
        pipeline_options.ocr_options.force_full_page_ocr = False  # Only OCR where needed
        pipeline_options.ocr_options.bitmap_area_threshold = 0.01  # Lower threshold to catch more images

        # Enable table structure extraction with ACCURATE mode
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
        pipeline_options.table_structure_options.do_cell_matching = True

        # Enable formula enrichment (for mathematical content)
        pipeline_options.do_formula_enrichment = True

        # Enable code enrichment (for code blocks)
        pipeline_options.do_code_enrichment = True

        # Enable picture classification
        pipeline_options.do_picture_classification = True

        # Generate page images for picture extraction
        pipeline_options.generate_page_images = True
        pipeline_options.generate_picture_images = True
        pipeline_options.images_scale = 2.0  # Higher resolution for better quality

        return pipeline_options

    @property
    def converter(self) -> DocumentConverter:
        """Lazy initialization of DocumentConverter with comprehensive options."""
        if self._converter is None:
            pipeline_options = self._create_pipeline_options()
            self._converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
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
                progress_callback("Extracting tables...", 65)

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
                progress_callback("Extracting pictures...", 80)

            # Export pictures/figures as image files
            picture_count = 0
            if options.images:
                pictures = list(doc.pictures) if hasattr(doc, 'pictures') else []
                images_folder = output_folder / f"{base_name}_images"

                for i, picture in enumerate(pictures):
                    try:
                        # Try to get the image from the picture item
                        image = None
                        if hasattr(picture, 'get_image'):
                            image = picture.get_image(doc)
                        elif hasattr(picture, 'image') and picture.image is not None:
                            image = picture.image

                        if image is not None:
                            # Create images folder only if we have images
                            images_folder.mkdir(parents=True, exist_ok=True)
                            img_path = images_folder / f"figure_{i+1}.png"
                            image.save(str(img_path))
                            output_files.append(str(img_path))
                            picture_count += 1
                    except Exception as e:
                        print(f"Warning: Could not export picture {i}: {e}")

            if progress_callback:
                progress_callback("Exporting key-value data...", 90)

            # Export key-value items if present (forms, structured data)
            if hasattr(doc, 'key_value_items') and doc.key_value_items:
                kv_data = []
                for kv in doc.key_value_items:
                    try:
                        kv_entry = {}
                        if hasattr(kv, 'key'):
                            kv_entry['key'] = str(kv.key) if kv.key else ''
                        if hasattr(kv, 'value'):
                            kv_entry['value'] = str(kv.value) if kv.value else ''
                        if kv_entry:
                            kv_data.append(kv_entry)
                    except Exception:
                        pass

                if kv_data:
                    kv_path = output_folder / f"{base_name}_key_values.json"
                    with open(kv_path, "w", encoding="utf-8") as f:
                        json.dump(kv_data, f, indent=4, ensure_ascii=False)
                    output_files.append(str(kv_path))

            # Export form items if present
            if hasattr(doc, 'form_items') and doc.form_items:
                form_data = []
                for form in doc.form_items:
                    try:
                        form_entry = {}
                        if hasattr(form, 'name'):
                            form_entry['name'] = str(form.name) if form.name else ''
                        if hasattr(form, 'value'):
                            form_entry['value'] = str(form.value) if form.value else ''
                        if form_entry:
                            form_data.append(form_entry)
                    except Exception:
                        pass

                if form_data:
                    form_path = output_folder / f"{base_name}_form_data.json"
                    with open(form_path, "w", encoding="utf-8") as f:
                        json.dump(form_data, f, indent=4, ensure_ascii=False)
                    output_files.append(str(form_path))

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
                page_count=page_count,
                picture_count=picture_count
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
