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
from dataclasses import dataclass, field
from typing import Callable
import json
import re

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
    extract_values: bool = True  # Extract numeric values when no tables found


@dataclass
class ExtractedValue:
    """A numeric value extracted from text with context."""
    value: str
    numeric_value: float
    tag: str
    context: str
    confidence: str  # "high", "medium", "low"


@dataclass
class ProcessingResult:
    """Result of document processing."""
    success: bool
    message: str
    output_files: list[str]
    table_count: int = 0
    page_count: int = 0
    picture_count: int = 0
    extracted_values_count: int = 0


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

    def _extract_numeric_values(self, text: str) -> list[ExtractedValue]:
        """
        Extract numeric values from text and tag them based on context.

        Uses pattern matching and contextual analysis to identify and
        categorize numbers found in the document text.
        """
        extracted = []

        # Patterns for different numeric formats
        patterns = [
            # Currency with symbol prefix: $1,234.56 or €1.234,56
            (r'[\$\€\£\¥]\s*[\d,\.]+(?:\.\d{2})?', 'currency', 'high'),
            # Currency with code: USD 1,234.56 or 1,234.56 USD
            (r'(?:USD|EUR|GBP|JPY|CNY)\s*[\d,\.]+|[\d,\.]+\s*(?:USD|EUR|GBP|JPY|CNY)', 'currency', 'high'),
            # Percentage: 12.5% or 12,5%
            (r'[\d,\.]+\s*%', 'percentage', 'high'),
            # Date patterns: 2024-01-15, 01/15/2024, 15-Jan-2024
            (r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b', 'date', 'high'),
            (r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', 'date', 'medium'),
            # Year: standalone 4-digit year
            (r'\b(?:19|20)\d{2}\b', 'year', 'medium'),
            # Phone numbers
            (r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', 'phone', 'high'),
            # Decimal numbers with thousands separators: 1,234,567.89
            (r'\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b', 'quantity', 'medium'),
            # Simple decimals: 123.45
            (r'\b\d+\.\d+\b', 'decimal', 'medium'),
            # Integers
            (r'\b\d+\b', 'integer', 'low'),
        ]

        # Context keywords for better tagging
        context_tags = {
            'price': ['price', 'cost', 'fee', 'charge', 'amount', 'total', 'subtotal', 'payment', 'paid'],
            'quantity': ['qty', 'quantity', 'count', 'number', 'units', 'items', 'pieces', 'pcs'],
            'percentage': ['percent', 'rate', 'ratio', 'discount', 'tax', 'vat', 'interest'],
            'date': ['date', 'dated', 'issued', 'due', 'expires', 'valid', 'from', 'to', 'until'],
            'id': ['id', 'number', 'no', 'ref', 'reference', 'code', 'invoice', 'order', 'account'],
            'measurement': ['kg', 'lb', 'oz', 'g', 'mg', 'km', 'mi', 'cm', 'mm', 'm', 'ft', 'in', 'l', 'ml', 'gal'],
            'temperature': ['°c', '°f', 'celsius', 'fahrenheit', 'temp', 'temperature'],
            'dimension': ['width', 'height', 'length', 'size', 'dimension', 'area', 'volume'],
            'time': ['hour', 'minute', 'second', 'hr', 'min', 'sec', 'am', 'pm'],
            'age': ['age', 'years old', 'year old', 'yo'],
            'score': ['score', 'rating', 'grade', 'points', 'marks'],
        }

        seen_values = set()  # Avoid duplicates

        for pattern, default_tag, confidence in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value_str = match.group()

                # Skip if we've already captured this exact value at this position
                value_key = (match.start(), value_str)
                if value_key in seen_values:
                    continue
                seen_values.add(value_key)

                # Get surrounding context (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].replace('\n', ' ').strip()

                # Try to parse numeric value
                try:
                    # Clean the value for parsing
                    clean_value = re.sub(r'[^\d.,\-]', '', value_str)
                    # Handle European format (1.234,56 -> 1234.56)
                    if ',' in clean_value and '.' in clean_value:
                        if clean_value.rfind(',') > clean_value.rfind('.'):
                            clean_value = clean_value.replace('.', '').replace(',', '.')
                        else:
                            clean_value = clean_value.replace(',', '')
                    else:
                        clean_value = clean_value.replace(',', '')
                    numeric = float(clean_value) if clean_value else 0.0
                except ValueError:
                    numeric = 0.0

                # Determine tag based on context
                final_tag = default_tag
                context_lower = context.lower()

                for tag, keywords in context_tags.items():
                    if any(kw in context_lower for kw in keywords):
                        # Context keyword found - upgrade confidence and possibly change tag
                        if default_tag in ['integer', 'decimal', 'quantity']:
                            final_tag = tag
                            confidence = 'high' if confidence == 'medium' else confidence
                        break

                extracted.append(ExtractedValue(
                    value=value_str,
                    numeric_value=numeric,
                    tag=final_tag,
                    context=context,
                    confidence=confidence
                ))

        # Sort by position in text (using context as proxy) and remove low-confidence duplicates
        # Keep higher confidence matches when values overlap
        filtered = []
        for ev in extracted:
            # Skip low confidence integers that are likely noise (very short numbers)
            if ev.tag == 'integer' and ev.confidence == 'low' and ev.numeric_value < 10:
                continue
            filtered.append(ev)

        return filtered

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
            table_dataframes = []  # Collect dataframes for combined export

            for i, table in enumerate(tables):
                try:
                    # Pass doc argument to avoid deprecation warning
                    df = table.export_to_dataframe(doc=doc)
                    table_dataframes.append((f"Table_{i+1}", df))
                    table_count += 1
                except Exception as e:
                    # Continue processing other tables if one fails
                    print(f"Warning: Could not export table {i}: {e}")

            # Export all tables to a single Excel file with multiple sheets
            if options.excel and table_dataframes:
                xlsx_path = output_folder / f"{base_name}_tables.xlsx"
                with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
                    for sheet_name, df in table_dataframes:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                output_files.append(str(xlsx_path))

            # Export tables to individual CSV files (CSV doesn't support multiple sheets)
            if options.csv and table_dataframes:
                for sheet_name, df in table_dataframes:
                    csv_path = output_folder / f"{base_name}_{sheet_name.lower()}.csv"
                    df.to_csv(csv_path, index=False)
                    output_files.append(str(csv_path))

            # If no tables found, extract numeric values from text
            extracted_values_count = 0
            if table_count == 0 and options.extract_values:
                if progress_callback:
                    progress_callback("No tables found, extracting numeric values...", 70)

                # Get the full text content
                text_content = doc.export_to_markdown()
                extracted_values = self._extract_numeric_values(text_content)

                if extracted_values:
                    extracted_values_count = len(extracted_values)

                    # Export to JSON
                    values_data = [
                        {
                            "value": ev.value,
                            "numeric_value": ev.numeric_value,
                            "tag": ev.tag,
                            "context": ev.context,
                            "confidence": ev.confidence
                        }
                        for ev in extracted_values
                    ]
                    values_json_path = output_folder / f"{base_name}_extracted_values.json"
                    with open(values_json_path, "w", encoding="utf-8") as f:
                        json.dump(values_data, f, indent=4, ensure_ascii=False)
                    output_files.append(str(values_json_path))

                    # Also export to CSV for easy viewing
                    values_df = pd.DataFrame(values_data)
                    values_csv_path = output_folder / f"{base_name}_extracted_values.csv"
                    values_df.to_csv(values_csv_path, index=False)
                    output_files.append(str(values_csv_path))

                    # Export to Excel with summary
                    values_xlsx_path = output_folder / f"{base_name}_extracted_values.xlsx"
                    with pd.ExcelWriter(values_xlsx_path, engine='openpyxl') as writer:
                        values_df.to_excel(writer, sheet_name='All Values', index=False)
                        # Create summary by tag
                        summary = values_df.groupby('tag').agg({
                            'numeric_value': ['count', 'sum', 'mean', 'min', 'max']
                        }).round(2)
                        summary.columns = ['Count', 'Sum', 'Average', 'Min', 'Max']
                        summary.to_excel(writer, sheet_name='Summary by Tag')
                    output_files.append(str(values_xlsx_path))

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

            # Build informative message
            message = f"Successfully processed {file_path.name}"
            if table_count == 0 and extracted_values_count > 0:
                message += f" (no tables found, extracted {extracted_values_count} numeric values)"
            elif table_count == 0:
                message += " (no tables or numeric values found)"

            return ProcessingResult(
                success=True,
                message=message,
                output_files=output_files,
                table_count=table_count,
                page_count=page_count,
                picture_count=picture_count,
                extracted_values_count=extracted_values_count
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
