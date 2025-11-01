# Google Sheet File Downloader

Download all files linked in Google Sheets or CSV files.

## Installation

Requires Python 3.7+ and requests:

```bash
pip install requests
# or
poetry install
```

## Usage

From the repository root:

```bash
# Download from Google Sheet
python -m src.download.enhanced_sheet_downloader "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit" -o downloads

# Download from local CSV file
python -m src.download.enhanced_sheet_downloader "data.csv" -o downloads

# Dry run (analyze without downloading)
python -m src.download.enhanced_sheet_downloader "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit" --dry-run
```

### Using Poetry

```bash
# With poetry run
poetry run python -m src.download.enhanced_sheet_downloader "SHEET_URL" -o downloads
```

### Example with the Bridge2AI Sheet

```bash
# Analyze the sheet
python -m src.download.enhanced_sheet_downloader "https://docs.google.com/spreadsheets/d/1pF_XlQ8zlei-QcxJ7yhkvi50qEI4jfOYly_-_18JjKE/edit?gid=0#gid=0" --dry-run

# Download all files
python -m src.download.enhanced_sheet_downloader "https://docs.google.com/spreadsheets/d/1pF_XlQ8zlei-QcxJ7yhkvi50qEI4jfOYly_-_18JjKE/edit?gid=0#gid=0" -o my_downloads
```

## Features

- Downloads files from public Google Sheets
- Downloads files from local CSV files
- Supports many file types (PDF, DOC, images, archives, etc.)
- Detailed analysis of found URLs
- Dry-run mode for preview
- Progress tracking and reporting
- Automatic handling of duplicate filenames

## Supported File Types

Documents, spreadsheets, presentations, archives, data files (JSON, XML, YAML), images, code files, and media files.

## Requirements

- Google Sheets must be publicly accessible ("Anyone with the link can view")
- Direct file URLs only (not web pages or DOI links)