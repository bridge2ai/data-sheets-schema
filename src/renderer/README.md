# Data Sheets Renderer

This module converts data sheets from docx and xlsx formats to human-readable text-only documents with proper styling.

## Features

- Extract JSON schema text from docx files
- Extract text tables from xlsx files
- Identify document structure (headings, sections, content)
- Generate output in multiple formats:
  - Plain text (.txt) with proper heading and formatting
  - HTML (.html) with styled presentation
  - PDF (.pdf) with structured layout

## Requirements

Required Python packages:
- python-docx
- openpyxl
- pandas
- fpdf

Install required packages:
```
pip install python-docx openpyxl pandas fpdf
```

## Usage

### Command Line

Process a single file:
```
python -m src.renderer.cli /path/to/file.docx
```

Process all files in a directory:
```
python -m src.renderer.cli /path/to/directory
```

### Python API

```python
from src.renderer import DataSheetConverter

# Convert a single file
converter = DataSheetConverter("/path/to/file.docx")
output_files = converter.convert()  # Returns list of generated files

# Process a whole directory
from src.renderer import process_directory
process_directory("/path/to/directory")
```

## Output

For each input file, the converter generates:
1. A plain text (.txt) file with structured content
2. An HTML (.html) file with styled presentation
3. A PDF (.pdf) document with formatted layout

All output files are saved in the same directory as the input file, but with different extensions.