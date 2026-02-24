#!/usr/bin/env python3
"""
Create a Google Sheet with D4D schema statistics from TSV files.

Creates a single spreadsheet with multiple tabs (one per TSV file).

Usage:
    python scripts/create_gsheet.py
"""

import os
import sys
import csv
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configuration
SERVICE_ACCOUNT_FILE = os.environ.get(
    'GOOGLE_SERVICE_ACCOUNT_FILE',
    str(Path(__file__).resolve().parent.parent / 'credentials' / 'service_account.json'),
)
SPREADSHEET_TITLE = 'D4D Schema Statistics'
TSV_DIR = Path('data/schema_stats')

# Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]


def get_services():
    """Authenticate and return Google Sheets and Drive services."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    sheets_service = build('sheets', 'v4', credentials=credentials)
    drive_service = build('drive', 'v3', credentials=credentials)
    return sheets_service, drive_service


def read_tsv(file_path):
    """Read TSV file and return data as list of lists."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            data.append(row)
    return data


def create_spreadsheet(sheets_service, title):
    """Create a new Google Spreadsheet and return its ID."""
    spreadsheet = {
        'properties': {
            'title': title
        }
    }
    spreadsheet = sheets_service.spreadsheets().create(
        body=spreadsheet,
        fields='spreadsheetId'
    ).execute()
    spreadsheet_id = spreadsheet.get('spreadsheetId')
    return spreadsheet_id


def create_sheet_tab(sheets_service, spreadsheet_id, sheet_name, data):
    """Add a new sheet tab and populate it with data."""
    # Add new sheet
    requests = [{
        'addSheet': {
            'properties': {
                'title': sheet_name
            }
        }
    }]

    body = {'requests': requests}
    response = sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=body
    ).execute()

    sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']

    # Write data to sheet
    range_name = f"'{sheet_name}'!A1"
    body = {
        'values': data
    }
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption='RAW',
        body=body
    ).execute()

    # Format header row (bold)
    if data:
        format_requests = [{
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'textFormat': {
                            'bold': True
                        }
                    }
                },
                'fields': 'userEnteredFormat.textFormat.bold'
            }
        }]

        body = {'requests': format_requests}
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()

    return sheet_id


def delete_default_sheet(sheets_service, spreadsheet_id):
    """Delete the default 'Sheet1' that Google creates."""
    # Get all sheets
    spreadsheet = sheets_service.spreadsheets().get(
        spreadsheetId=spreadsheet_id
    ).execute()

    sheets = spreadsheet.get('sheets', [])

    # Find and delete Sheet1
    for sheet in sheets:
        if sheet['properties']['title'] == 'Sheet1':
            sheet_id = sheet['properties']['sheetId']
            requests = [{
                'deleteSheet': {
                    'sheetId': sheet_id
                }
            }]
            body = {'requests': requests}
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            break


def make_public(drive_service, file_id):
    """Make the spreadsheet publicly viewable."""
    try:
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        drive_service.permissions().create(
            fileId=file_id,
            body=permission
        ).execute()
        return True
    except Exception as e:
        print(f"Warning: Could not make spreadsheet public: {e}")
        return False


def main():
    """Main workflow."""
    print("D4D Schema Statistics → Google Sheets")
    print("=" * 60)

    # Check service account file exists
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"ERROR: Service account file not found: {SERVICE_ACCOUNT_FILE}")
        return 1

    # Check TSV directory exists
    if not TSV_DIR.exists():
        print(f"ERROR: TSV directory not found: {TSV_DIR}")
        return 1

    # Get all TSV files in order
    tsv_files = [
        ('Level 1: Summary', 'level1_summary.tsv'),
        ('Level 2: Class Categories', 'level2_class_categories.tsv'),
        ('Level 2: Classes by Module', 'level2_classes_by_module.tsv'),
        ('Level 2: Slot Categories', 'level2_slot_categories.tsv'),
        ('Level 2: Slots by Range', 'level2_slots_by_range_type.tsv'),
        ('Level 3: Inheritance', 'level3_inheritance_depth.tsv'),
        ('Level 3: Top Slots', 'level3_top_reused_slots.tsv'),
        ('Level 4: Quality Metrics', 'level4_quality_metrics.tsv'),
        ('Level 4: Recommendations', 'level4_recommendations.tsv'),
    ]

    print(f"\nFound {len(tsv_files)} TSV files to import")

    try:
        # Authenticate
        print("\nAuthenticating with Google...")
        sheets_service, drive_service = get_services()
        print("✓ Authentication successful")

        # Create spreadsheet
        print(f"\nCreating spreadsheet '{SPREADSHEET_TITLE}'...")
        spreadsheet_id = create_spreadsheet(sheets_service, SPREADSHEET_TITLE)
        print(f"✓ Created spreadsheet (ID: {spreadsheet_id})")

        # Add data sheets
        print(f"\nImporting {len(tsv_files)} data sheets...")
        for sheet_name, filename in tsv_files:
            file_path = TSV_DIR / filename
            if not file_path.exists():
                print(f"  ⚠ Skipping {filename} (not found)")
                continue

            data = read_tsv(file_path)
            create_sheet_tab(sheets_service, spreadsheet_id, sheet_name, data)
            print(f"  ✓ Imported: {sheet_name} ({len(data)} rows)")

        # Delete default Sheet1
        print("\nCleaning up...")
        delete_default_sheet(sheets_service, spreadsheet_id)
        print("✓ Removed default sheet")

        # Make public
        print("\nMaking spreadsheet publicly viewable...")
        if make_public(drive_service, spreadsheet_id):
            print("✓ Spreadsheet is now public")
        else:
            print("⚠ Spreadsheet is private (only accessible to service account)")

        # Generate shareable link
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        print(f"\n{'=' * 60}")
        print(f"✓ Import complete!")
        print(f"\nGoogle Sheets URL:")
        print(f"{spreadsheet_url}")
        print(f"\nSpreadsheet ID: {spreadsheet_id}")
        print(f"{'=' * 60}")

        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
