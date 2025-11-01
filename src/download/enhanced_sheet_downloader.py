#!/usr/bin/env python3
"""
Enhanced script to download all files linked in a Google Sheet with detailed reporting.
"""
import csv
import os
import re
import requests
import urllib.parse
from pathlib import Path
from typing import List, Set, Dict, Tuple
import argparse
import time


def is_downloadable_url(url: str) -> Tuple[bool, str]:
    """Check if a URL is likely to be a downloadable file and return the reason."""
    if not url or not url.startswith(('http://', 'https://')):
        return False, "Not a valid HTTP/HTTPS URL"
    
    # Common file extensions that should be downloaded
    downloadable_extensions = {
        '.pdf': 'PDF document',
        '.doc': 'Word document', '.docx': 'Word document',
        '.xls': 'Excel spreadsheet', '.xlsx': 'Excel spreadsheet',
        '.ppt': 'PowerPoint presentation', '.pptx': 'PowerPoint presentation',
        '.zip': 'Archive', '.tar': 'Archive', '.gz': 'Archive',
        '.csv': 'CSV data', '.json': 'JSON data', '.xml': 'XML data',
        '.yaml': 'YAML data', '.yml': 'YAML data',
        '.txt': 'Text file', '.md': 'Markdown', '.rtf': 'Rich text',
        '.odt': 'OpenDocument text', '.ods': 'OpenDocument spreadsheet', '.odp': 'OpenDocument presentation',
        '.png': 'Image', '.jpg': 'Image', '.jpeg': 'Image', '.gif': 'Image',
        '.bmp': 'Image', '.svg': 'Image', '.tiff': 'Image',
        '.mp3': 'Audio', '.wav': 'Audio',
        '.mp4': 'Video', '.avi': 'Video', '.mov': 'Video', '.wmv': 'Video',
        '.py': 'Python code', '.js': 'JavaScript', '.html': 'HTML',
        '.css': 'CSS', '.java': 'Java code', '.cpp': 'C++ code', '.c': 'C code'
    }
    
    # Check if URL has a downloadable extension
    parsed = urllib.parse.urlparse(url.lower())
    path = parsed.path
    
    for ext, file_type in downloadable_extensions.items():
        if path.endswith(ext):
            return True, f"{file_type} ({ext})"
    
    # Check for common download patterns
    download_patterns = {
        'download': 'Contains "download"',
        'attachment': 'Contains "attachment"',
        'export': 'Contains "export"',
        'file': 'Contains "file"'
    }
    
    for pattern, description in download_patterns.items():
        if pattern in url.lower():
            return True, description
    
    return False, "No downloadable pattern detected"


def extract_urls_from_csv_content(csv_content: str) -> Dict[str, Dict]:
    """Extract all URLs from CSV content with metadata."""
    urls = {}
    
    # Use CSV reader to properly parse the content
    lines = csv_content.strip().split('\n')
    csv_reader = csv.reader(lines)
    
    for row_idx, row in enumerate(csv_reader):
        for col_idx, cell in enumerate(row):
            # Find URLs in the cell using regex
            url_pattern = r'https?://[^\s,<>"\']*'
            found_urls = re.findall(url_pattern, cell)
            
            for url in found_urls:
                # Clean up URL (remove trailing punctuation)
                url = url.rstrip('.,;:!?)')
                is_downloadable, reason = is_downloadable_url(url)
                
                if url not in urls:
                    urls[url] = {
                        'is_downloadable': is_downloadable,
                        'reason': reason,
                        'locations': [],
                        'context': cell[:100] + ('...' if len(cell) > 100 else '')
                    }
                
                urls[url]['locations'].append((row_idx, col_idx))
    
    return urls


def get_file_info(url: str, session: requests.Session) -> Dict:
    """Get information about a file without downloading it."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = session.head(url, headers=headers, allow_redirects=True, timeout=30)
        
        info = {
            'status_code': response.status_code,
            'content_type': response.headers.get('content-type', 'unknown'),
            'content_length': response.headers.get('content-length', 'unknown'),
            'filename': None
        }
        
        # Try to get filename from Content-Disposition header
        if 'content-disposition' in response.headers:
            cd = response.headers['content-disposition']
            filename_match = re.search(r'filename="([^"]+)"', cd)
            if filename_match:
                info['filename'] = filename_match.group(1)
        
        # If no filename from header, extract from URL
        if not info['filename']:
            parsed_url = urllib.parse.urlparse(url)
            info['filename'] = os.path.basename(parsed_url.path) or 'unknown'
            
        return info
        
    except Exception as e:
        return {'error': str(e)}


def download_file(url: str, output_dir: Path, session: requests.Session, file_info: Dict = None) -> Tuple[bool, str]:
    """Download a single file from URL."""
    try:
        print(f"  Downloading: {url}")
        
        filename = None
        if file_info and 'filename' in file_info:
            filename = file_info['filename']
        
        if not filename:
            # Get filename from URL or use a default
            parsed_url = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed_url.path)
        
        if not filename or '.' not in filename:
            filename = f"download_{hash(url) & 0xFFFFFF:06x}"
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set browser-like headers to avoid bot detection
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Special handling for bioRxiv and similar academic sites
        if 'biorxiv.org' in url or 'medrxiv.org' in url:
            # Add a referer header for academic sites
            headers['Referer'] = 'https://www.biorxiv.org/'
            # Small delay to be respectful
            time.sleep(2)
        
        # Download the file
        response = session.get(url, headers=headers, allow_redirects=True, timeout=60)
        response.raise_for_status()
        
        output_path = output_dir / filename
        
        # Handle filename conflicts
        counter = 1
        original_path = output_path
        while output_path.exists():
            name, ext = os.path.splitext(original_path.name)
            output_path = output_dir / f"{name}_{counter}{ext}"
            counter += 1
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        file_size = len(response.content)
        print(f"    ✅ Downloaded: {output_path} ({file_size:,} bytes)")
        return True, str(output_path)
        
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        return False, str(e)


def analyze_and_download(input_source: str, output_dir: str, dry_run: bool = False):
    """Analyze and optionally download files from input source."""
    
    # Determine if input is URL or file
    if input_source.startswith(('http://', 'https://')):
        print(f"📊 Analyzing Google Sheet: {input_source}")
        
        # Convert Google Sheets URL to CSV export URL
        if '/edit' in input_source:
            sheet_id_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', input_source)
            if not sheet_id_match:
                print("❌ Could not extract sheet ID from URL")
                return
            
            sheet_id = sheet_id_match.group(1)
            gid_match = re.search(r'[#&]gid=(\d+)', input_source)
            gid = gid_match.group(1) if gid_match else '0'
            
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            print(f"📥 CSV export URL: {csv_url}")
        else:
            csv_url = input_source
        
        try:
            session = requests.Session()
            response = session.get(csv_url, timeout=30)
            response.raise_for_status()
            csv_content = response.text
        except Exception as e:
            print(f"❌ Error accessing sheet: {e}")
            return
    else:
        print(f"📊 Analyzing CSV file: {input_source}")
        try:
            with open(input_source, 'r', encoding='utf-8') as f:
                csv_content = f.read()
        except UnicodeDecodeError:
            with open(input_source, 'r', encoding='latin-1') as f:
                csv_content = f.read()
        session = requests.Session()
    
    # Extract all URLs
    all_urls = extract_urls_from_csv_content(csv_content)
    
    if not all_urls:
        print("❌ No URLs found in the data source")
        return
    
    print(f"\n🔍 Found {len(all_urls)} unique URLs:")
    
    downloadable_urls = []
    non_downloadable_urls = []
    
    for url, metadata in all_urls.items():
        print(f"\n  URL: {url}")
        print(f"       Context: {metadata['context']}")
        print(f"       Locations: Row(s) {[loc[0]+1 for loc in metadata['locations']]}")
        
        if metadata['is_downloadable']:
            print(f"       ✅ Downloadable: {metadata['reason']}")
            downloadable_urls.append(url)
        else:
            print(f"       ❌ Not downloadable: {metadata['reason']}")
            non_downloadable_urls.append(url)
    
    if not downloadable_urls:
        print(f"\n❌ No downloadable files found")
        return
    
    print(f"\n📁 {len(downloadable_urls)} downloadable files found")
    print(f"🚫 {len(non_downloadable_urls)} non-downloadable URLs skipped")
    
    if dry_run:
        print(f"\n🔍 DRY RUN - Would download to: {output_dir}")
        
        # Get file info for downloadable URLs
        for url in downloadable_urls:
            print(f"\n  Checking: {url}")
            file_info = get_file_info(url, session)
            
            if 'error' in file_info:
                print(f"    ❌ Error: {file_info['error']}")
            else:
                size_str = f"{int(file_info['content_length']):,} bytes" if file_info['content_length'].isdigit() else file_info['content_length']
                print(f"    📄 Filename: {file_info['filename']}")
                print(f"    📊 Type: {file_info['content_type']}")
                print(f"    📏 Size: {size_str}")
        return
    
    # Download files
    print(f"\n⬇️  Starting downloads to: {output_dir}")
    output_path = Path(output_dir)
    
    successful_downloads = []
    failed_downloads = []
    
    for i, url in enumerate(downloadable_urls, 1):
        print(f"\n[{i}/{len(downloadable_urls)}] Processing: {url}")
        
        success, result = download_file(url, output_path, session)
        
        if success:
            successful_downloads.append((url, result))
        else:
            failed_downloads.append((url, result))
        
        # Small delay to be nice to servers
        time.sleep(0.5)
    
    # Summary
    print(f"\n" + "="*50)
    print(f"📊 DOWNLOAD SUMMARY")
    print(f"="*50)
    print(f"✅ Successful: {len(successful_downloads)}")
    print(f"❌ Failed: {len(failed_downloads)}")
    print(f"📂 Output directory: {output_path.absolute()}")
    
    if successful_downloads:
        print(f"\n✅ Successfully downloaded:")
        for url, path in successful_downloads:
            print(f"  - {Path(path).name}")
    
    if failed_downloads:
        print(f"\n❌ Failed downloads:")
        for url, error in failed_downloads:
            print(f"  - {url}: {error}")


def main():
    parser = argparse.ArgumentParser(
        description="Download files from Google Sheets or CSV files",
        epilog="Example: python -m src.download.enhanced_sheet_downloader 'https://docs.google.com/spreadsheets/d/...' -o downloads"
    )
    parser.add_argument("input", help="Google Sheet URL or path to CSV file")
    parser.add_argument("-o", "--output", default="downloads", help="Output directory for downloads")
    parser.add_argument("--dry-run", action="store_true", help="Analyze files but don't download")
    
    args = parser.parse_args()
    
    analyze_and_download(args.input, args.output, args.dry_run)


if __name__ == "__main__":
    main()