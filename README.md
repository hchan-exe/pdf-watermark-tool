# PDF Watermark Tool

A desktop GUI for adding tiled, multi-line, diagonal watermarks to PDF documents — similar to "Strictly Private and Confidential" stamps on legal and financial documents.

## Features

- Multi-line watermark text with alternating rows
- Adjustable font size, angle, spacing, gray level, and opacity
- Optional first-page preview (requires PyMuPDF)
- Batch-friendly single-file workflow

## Requirements

- Python 3.8+
- Windows 10/11

## Installation

```bash
pip install -r requirements.txt
```

Optional preview support:

```bash
pip install PyMuPDF
```

## Usage

Double-click `Run Watermark Tool.bat`, or run:

```bash
python pdf_watermark_gui.py
```

1. Browse for an input PDF
2. Enter watermark lines (one per row)
3. Adjust styling options
4. Click **Generate Watermarked PDF** and choose a save location

## License

MIT
