#!/usr/bin/env python3
"""
Organize extracted_datasets_v2 files into column structure for D4D processing.
"""
import shutil
from pathlib import Path

def organize_files():
    """Organize files from extracted_datasets_v2 into column directories."""
    
    source_dir = Path("extracted_datasets_v2")
    target_dir = Path("downloads_by_column")
    
    # Create target directory
    target_dir.mkdir(exist_ok=True)
    
    # Define file mapping based on naming patterns
    file_mappings = {
        'AI_READI': [
            'docs_aireadi_org_docs-2-about',
            'fairhub_dataset_2',
            'doi_10.5281_zenodo.10642459',
            'webpage_eba2c6'  # This appears to be aireadi related
        ],
        'CHORUS': [
            'aim-ahead-bridge2ai-for-clinical-care-informational-webinar',
        ],
        'CM4AI': [
            'dataverse_10.18130_V3_B35XWX',
            'dataverse_10.18130_V3_F3TD5R',
            'doi_10.1101_2024.05.21.589311',
        ],
        'VOICE': [
            'physionet_b2ai-voice_1.1',
            'healthnexus_b2ai-voice_1.0',
        ],
        'MISC': [  # For files that don't clearly fit other categories
            'docs_google_com_document-d-1rJsa5kySlBRRNhsO_WY7N3bfSKtqDi-Q',
            'doi_10.1038_s42255-024-01165-xhttps',
            'webpage_cd1598'
        ]
    }
    
    print(f"Organizing files from {source_dir} to {target_dir}")
    
    # Create column directories
    for column in file_mappings.keys():
        column_dir = target_dir / column
        column_dir.mkdir(exist_ok=True)
        print(f"Created directory: {column_dir}")
    
    # Process all files in source directory
    for file_path in source_dir.glob("*"):
        if file_path.is_file():
            # Skip report files
            if any(skip in file_path.name for skip in ['extraction_report', 'extraction_summary']):
                continue
                
            # Find matching column
            matched_column = None
            for column, patterns in file_mappings.items():
                for pattern in patterns:
                    if pattern in file_path.name:
                        matched_column = column
                        break
                if matched_column:
                    break
            
            if not matched_column:
                matched_column = 'MISC'
                print(f"⚠️  No specific match for {file_path.name}, placing in MISC")
            
            # Copy file to appropriate column directory
            target_path = target_dir / matched_column / file_path.name
            shutil.copy2(file_path, target_path)
            print(f"📄 {file_path.name} → {matched_column}/")
    
    # Summary
    print("\n📊 Organization Summary:")
    for column in file_mappings.keys():
        column_dir = target_dir / column
        file_count = len(list(column_dir.glob("*")))
        print(f"   {column}: {file_count} files")
    
    print(f"\n✅ Files organized in: {target_dir.absolute()}")

if __name__ == "__main__":
    organize_files()