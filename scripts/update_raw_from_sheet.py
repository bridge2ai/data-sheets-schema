#!/usr/bin/env python3
"""
Update data/raw/ downloads using the B2AI GC Input Documents Google Sheet.

Reads the sheet via the Google Sheets API (service account credentials),
converts it to CSV, and feeds it to DriveAwareExtractor, a wrapper around
OrganizedDatasetExtractor that adds Google Drive / Google Docs download
support on top of the existing URL handlers.

Supported Drive URL patterns:
  drive.google.com/file/d/{ID}/...   → download binary via Drive API
  docs.google.com/document/d/{ID}/  → export as DOCX via Drive API
  docs.google.com/spreadsheets/...  → export as XLSX via Drive API

Falls back to the public direct-download URL if the SA lacks access.

Usage:
    poetry run python scripts/update_raw_from_sheet.py
    poetry run python scripts/update_raw_from_sheet.py --dry-run
    poetry run python scripts/update_raw_from_sheet.py --project VOICE
"""

import argparse
import csv
import io
import os
import re
import sys
import tempfile
from pathlib import Path
import requests

# Add repo src/ to path so we can import the extractor
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'src'))

from download.organized_dataset_extractor import (  # noqa: E402
    OrganizedDatasetExtractor,
    extract_urls,
    normalize_project_name,
)

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    GOOGLE_API_AVAILABLE = True
except ImportError:
    service_account = None
    build = None
    MediaIoBaseDownload = None
    GOOGLE_API_AVAILABLE = False

# ── Configuration ─────────────────────────────────────────────────────────────

SHEET_ID = '1jBD6sTp6TDemy6v75PGAHSVz5yfIAXZ8zdDPbmOGATM'
DEFAULT_SA_FILE = Path('/Users/marcin/Documents/VIMSS/ontology/KG-Hub/KG-Microbe/'
                       'CultureBotHT/CultureBotHT/credentials/service_account.json')
SA_FILE = Path(os.environ.get('B2AI_GOOGLE_SERVICE_ACCOUNT', DEFAULT_SA_FILE))
OUTPUT_DIR = REPO_ROOT / 'data' / 'raw'

SHEETS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
DRIVE_SCOPES  = ['https://www.googleapis.com/auth/drive.readonly']

# Map Google Workspace MIME types → export MIME + file extension
GDOCS_EXPORT = {
    'application/vnd.google-apps.document':
        (
            'application/vnd.openxmlformats-officedocument.'
            'wordprocessingml.document',
            '.docx',
        ),
    'application/vnd.google-apps.spreadsheet':
        ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx'),
    'application/vnd.google-apps.presentation':
        ('application/pdf', '.pdf'),
}


# ── Sheet reading ─────────────────────────────────────────────────────────────

def read_sheet(sheet_id: str) -> list[list[str]]:
    """Read all rows, using Google APIs when available and public CSV otherwise."""
    if GOOGLE_API_AVAILABLE and SA_FILE.exists():
        creds = service_account.Credentials.from_service_account_file(
            str(SA_FILE), scopes=SHEETS_SCOPES
        )
        svc = build('sheets', 'v4', credentials=creds)
        result = svc.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range='Sheet1',
            valueRenderOption='FORMATTED_VALUE',
        ).execute()
        return result.get('values', [])

    csv_url = (
        f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv'
    )
    response = requests.get(csv_url, timeout=30)
    response.raise_for_status()
    return list(csv.reader(io.StringIO(response.text)))


def rows_to_csv(rows: list[list[str]]) -> str:
    """Convert raw sheet rows to a CSV string the extractor can parse."""
    if not rows:
        return ''
    width = max(len(r) for r in rows)
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow(row + [''] * (width - len(row)))
    return buf.getvalue()


# ── Drive-aware extractor ─────────────────────────────────────────────────────

class DriveAwareExtractor:
    """
    Wraps OrganizedDatasetExtractor to intercept Google Drive / Docs URLs
    and download them via the Drive API before falling through to the base
    handler for all other URL types.
    """

    # Patterns that identify a Google-hosted file
    _GDRIVE_RE  = re.compile(r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)')
    _GDOCS_RE   = re.compile(r'docs\.google\.com/(?:document|spreadsheets|presentation)/d/([a-zA-Z0-9_-]+)')
    _OPEN_RE    = re.compile(r'drive\.google\.com/open\?(?:.*&)?id=([a-zA-Z0-9_-]+)')

    def __init__(self, output_dir: str):
        self._base = OrganizedDatasetExtractor(output_dir)
        self._drive_svc = None

    # ── forward attribute lookups to the base extractor ──────────────────────
    def __getattr__(self, name):
        return getattr(self._base, name)

    # ── Drive API lazily initialised ──────────────────────────────────────────
    def _drive(self):
        if not GOOGLE_API_AVAILABLE or not SA_FILE.exists():
            raise RuntimeError(
                'Google API credentials are unavailable; use the public handler'
            )
        if self._drive_svc is None:
            creds = service_account.Credentials.from_service_account_file(
                str(SA_FILE), scopes=DRIVE_SCOPES
            )
            self._drive_svc = build('drive', 'v3', credentials=creds)
        return self._drive_svc

    # ── file-ID extraction ────────────────────────────────────────────────────
    @classmethod
    def _file_id(cls, url: str) -> tuple[str | None, bool]:
        """Return (file_id, is_gdocs_workspace_file)."""
        m = cls._GDRIVE_RE.search(url)
        if m:
            return m.group(1), False
        m = cls._GDOCS_RE.search(url)
        if m:
            return m.group(1), True   # always a Workspace type → export
        m = cls._OPEN_RE.search(url)
        if m:
            return m.group(1), False
        return None, False

    # ── download via Drive API ────────────────────────────────────────────────
    def _download_drive(self, url: str, column_dir: Path, row: int) -> dict:
        info: dict = {'type': 'Google Drive', 'url': url, 'row': row}

        fid, is_workspace = self._file_id(url)
        if not fid:
            info['error'] = 'Could not extract file ID from URL'
            info['downloaded'] = False
            return info

        try:
            drive = self._drive()
            meta = drive.files().get(
                fileId=fid, fields='name,mimeType,size'
            ).execute()
            name = meta['name']
            mime = meta.get('mimeType', '')

            _, ext = os.path.splitext(name)

            # Choose request type
            if mime in GDOCS_EXPORT:
                export_mime, export_ext = GDOCS_EXPORT[mime]
                request = drive.files().export_media(
                    fileId=fid, mimeType=export_mime
                )
                filename = f'gdrive_{fid}_row{row}{export_ext}'
            else:
                if not ext:
                    # Guess from common MIME types
                    ext = {
                        'application/pdf': '.pdf',
                        'application/zip': '.zip',
                        'text/plain':      '.txt',
                        'text/csv':        '.csv',
                    }.get(mime, '')
                filename = f'gdrive_{fid}_row{row}{ext}'
                request = drive.files().get_media(fileId=fid)

            file_path = column_dir / filename
            with open(file_path, 'wb') as fh:
                dl = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    _, done = dl.next_chunk()

            info.update({'filename': filename, 'path': str(file_path),
                         'downloaded': True})
            return info

        except Exception as api_err:
            print(f'      ⚠ Drive API error ({api_err}), trying public URL …')

        fallback = self._base._download_google_drive(url, column_dir, row)
        if fallback.get('downloaded'):
            fallback['note'] = 'downloaded via public URL fallback'
        return fallback

    # ── override process_url to inject Drive handler ──────────────────────────
    def _process_url(self, url: str, column_dir: Path, row: int) -> dict:
        if 'drive.google.com' in url or 'docs.google.com/document' in url \
                or 'docs.google.com/spreadsheets' in url \
                or 'docs.google.com/presentation' in url:
            if not GOOGLE_API_AVAILABLE or not SA_FILE.exists():
                return OrganizedDatasetExtractor._process_url(
                    self._base, url, column_dir, row
                )
            return self._download_drive(url, column_dir, row)
        return OrganizedDatasetExtractor._process_url(
            self._base, url, column_dir, row
        )

    def process_spreadsheet(
        self,
        csv_path: str,
        projects: list[str] | None = None,
    ) -> dict:
        """Use the base parser/deduplication loop with the Drive API hook."""
        original_process_url = self._base._process_url
        self._base._process_url = self._process_url
        try:
            return self._base.process_spreadsheet(csv_path, projects=projects)
        finally:
            self._base._process_url = original_process_url


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Update data/raw/ from GC Input Sheet')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print URLs that would be downloaded (no downloads)')
    parser.add_argument('--project', choices=['CM4AI', 'VOICE', 'AI_READI', 'CHORUS'],
                        help='Download only this project (default: all)')
    args = parser.parse_args()

    print(f'Reading sheet {SHEET_ID} …')
    rows = read_sheet(SHEET_ID)
    print(f'  → {len(rows)} rows')
    if not rows:
        print('Sheet is empty. Nothing to do.')
        return

    header = rows[0]
    print(f'  Columns: {header}')

    # ── dry-run ───────────────────────────────────────────────────────────────
    if args.dry_run:
        print('\n── DRY RUN: URLs that would be downloaded ──')
        seen_urls: dict[str, set[str]] = {}
        for row_idx, row in enumerate(rows[1:], start=2):
            for col_idx, cell in enumerate(row):
                if col_idx == 0 or not cell:
                    continue
                col_name = header[col_idx] if col_idx < len(header) else f'col{col_idx}'
                project = normalize_project_name(col_name)
                if args.project and project != args.project:
                    continue
                doc_type = rows[row_idx - 2][0] if rows[row_idx - 2] else ''
                project_urls = seen_urls.setdefault(project, set())
                for url in extract_urls(cell):
                    if url.rstrip('/') in project_urls:
                        continue
                    project_urls.add(url.rstrip('/'))
                    tag = '[Drive/Docs]' if ('drive.google.com' in url
                                             or 'docs.google.com' in url) else ''
                    print(f'  [{project}] row {row_idx} ({doc_type}): {url} {tag}')
        return

    # ── filter to one project if requested ───────────────────────────────────
    if args.project:
        target_col = args.project.replace('_', '-')   # AI_READI → AI-READI
        try:
            col_idx = header.index(target_col)
        except ValueError:
            try:
                col_idx = header.index(args.project)
            except ValueError:
                print(f'ERROR: column {args.project!r} not found in {header}')
                sys.exit(1)
        rows = [[r[0] if r else '',
                 r[col_idx] if col_idx < len(r) else ''] for r in rows]
        rows[0] = ['', args.project]

    csv_content = rows_to_csv(rows)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv',
                                     delete=False, encoding='utf-8') as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    print(f'\nOutput directory: {OUTPUT_DIR}')
    try:
        if GOOGLE_API_AVAILABLE and SA_FILE.exists():
            extractor = DriveAwareExtractor(str(OUTPUT_DIR))
            results = extractor.process_spreadsheet(
                tmp_path,
                projects=[args.project] if args.project else None,
            )
        else:
            print('Google API client/credentials unavailable; using public downloads.')
            extractor = OrganizedDatasetExtractor(str(OUTPUT_DIR))
            results = extractor.process_spreadsheet(
                tmp_path,
                projects=[args.project] if args.project else None,
            )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    total  = sum(len(v) for v in results['by_column'].values())
    errors = len(results['errors'])
    print(f'\n{"="*60}')
    print(f'DONE  — {total} items processed, {errors} errors')
    print(f'Output: {OUTPUT_DIR.absolute()}')
    if errors:
        print('\nErrors:')
        for e in results['errors']:
            print(f'  [{e["column"]}] row {e["row"]}: {e["url"]}')
            print(f'    {e["error"]}')


if __name__ == '__main__':
    main()
