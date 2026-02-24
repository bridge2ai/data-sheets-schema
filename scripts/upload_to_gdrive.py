#!/usr/bin/env python3
"""
Upload D4D schema statistics TSV files to Google Drive.

Usage:
    python scripts/upload_to_gdrive.py
"""

import os
import sys
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configuration
SERVICE_ACCOUNT_FILE = '/Users/marcin/Documents/VIMSS/ontology/KG-Hub/KG-Microbe/CultureBotHT/CultureBotHT/credentials/service_account.json'
PARENT_FOLDER_ID = '15QywFl6JKOXqk6gdDFCv1F_eHLYTOzO5'  # From Drive URL
SUBFOLDER_NAME = 'D4D_stats'
TSV_DIR = Path('data/schema_stats')

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive']


def get_drive_service():
    """Authenticate and return Google Drive service."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build('drive', 'v3', credentials=credentials)
    return service


def create_folder(service, folder_name, parent_id):
    """Create a folder in Google Drive and return its ID."""
    # Check if folder already exists
    query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])

    if items:
        print(f"Folder '{folder_name}' already exists (ID: {items[0]['id']})")
        return items[0]['id']

    # Create new folder
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=file_metadata, fields='id').execute()
    folder_id = folder.get('id')
    print(f"Created folder '{folder_name}' (ID: {folder_id})")
    return folder_id


def upload_file(service, file_path, folder_id):
    """Upload a file to Google Drive folder."""
    file_name = file_path.name

    # Check if file already exists in folder
    query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])

    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }

    media = MediaFileUpload(
        str(file_path),
        mimetype='text/tab-separated-values',
        resumable=True
    )

    if items:
        # Update existing file
        file_id = items[0]['id']
        file = service.files().update(
            fileId=file_id,
            media_body=media
        ).execute()
        print(f"  ✓ Updated: {file_name} (ID: {file.get('id')})")
    else:
        # Create new file
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        print(f"  ✓ Uploaded: {file_name} (ID: {file.get('id')})")

    return file.get('id')


def main():
    """Main upload workflow."""
    print("D4D Schema Statistics → Google Drive Upload")
    print("=" * 60)

    # Check service account file exists
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"ERROR: Service account file not found: {SERVICE_ACCOUNT_FILE}")
        return 1

    # Check TSV directory exists
    if not TSV_DIR.exists():
        print(f"ERROR: TSV directory not found: {TSV_DIR}")
        return 1

    # Get all TSV files
    tsv_files = sorted(TSV_DIR.glob('*.tsv'))
    readme_file = TSV_DIR / 'README.md'

    if not tsv_files:
        print(f"ERROR: No TSV files found in {TSV_DIR}")
        return 1

    print(f"\nFound {len(tsv_files)} TSV files to upload")
    if readme_file.exists():
        print(f"Found README.md to upload")

    try:
        # Authenticate
        print("\nAuthenticating with Google Drive...")
        service = get_drive_service()
        print("✓ Authentication successful")

        # Create subfolder
        print(f"\nCreating/checking subfolder '{SUBFOLDER_NAME}'...")
        subfolder_id = create_folder(service, SUBFOLDER_NAME, PARENT_FOLDER_ID)

        # Upload TSV files
        print(f"\nUploading {len(tsv_files)} TSV files...")
        for tsv_file in tsv_files:
            upload_file(service, tsv_file, subfolder_id)

        # Upload README
        if readme_file.exists():
            print(f"\nUploading README.md...")
            upload_file(service, readme_file, subfolder_id)

        # Generate shareable link
        folder_url = f"https://drive.google.com/drive/folders/{subfolder_id}"
        print(f"\n{'=' * 60}")
        print(f"✓ Upload complete!")
        print(f"\nGoogle Drive folder: {folder_url}")
        print(f"{'=' * 60}")

        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
