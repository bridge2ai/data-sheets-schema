#!/usr/bin/env python3
"""
Enhanced dataset extractor that organizes downloads by spreadsheet column headings.
Maintains the original structure from the source spreadsheet.
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
import json
from collections import defaultdict


class OrganizedDatasetExtractor:
    """Extract datasets and organize them by spreadsheet columns."""
    
    def __init__(self, output_dir: str = "organized_datasets"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
    def process_spreadsheet(self, csv_path: str) -> Dict:
        """Process a CSV file maintaining column organization."""
        results = {
            'by_column': defaultdict(list),
            'summary': defaultdict(int),
            'errors': []
        }
        
        # Get CSV content
        if csv_path.startswith(('http://', 'https://')):
            try:
                response = self.session.get(csv_path, timeout=30)
                response.raise_for_status()
                content = response.text
            except Exception as e:
                print(f"Error downloading CSV: {e}")
                return results
        else:
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(csv_path, 'r', encoding='latin-1') as f:
                    content = f.read()
        
        # Parse CSV with headers
        lines = content.strip().split('\n')
        csv_reader = csv.DictReader(lines)
        
        # Extract URLs by column
        column_urls = defaultdict(list)
        row_count = 0
        
        for row_idx, row in enumerate(csv_reader):
            row_count += 1
            for column, cell_value in row.items():
                if cell_value:
                    # Find URLs in the cell
                    url_pattern = r'https?://[^\s,<>"\']*'
                    found_urls = re.findall(url_pattern, cell_value)
                    for url in found_urls:
                        url = url.rstrip('.,;:!?)')
                        column_urls[column].append({
                            'url': url,
                            'row': row_idx + 2,  # +2 for header and 0-index
                            'context': cell_value[:100] + ('...' if len(cell_value) > 100 else '')
                        })
        
        print(f"\n📊 Analyzed {row_count} rows from spreadsheet")
        print(f"📁 Found {len(column_urls)} columns with URLs:\n")
        
        # Process each column
        for column, url_list in column_urls.items():
            if not url_list:
                continue
                
            # Clean column name for directory
            safe_column = self._sanitize_filename(column)
            column_dir = self.output_dir / safe_column
            column_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"\n📂 Column: {column}")
            print(f"   Directory: {safe_column}/")
            print(f"   URLs found: {len(url_list)}")
            
            # Process URLs in this column
            for url_info in url_list:
                url = url_info['url']
                row = url_info['row']
                
                print(f"\n   [Row {row}] Processing: {url}")
                
                try:
                    # Determine URL type and process
                    file_info = self._process_url(url, column_dir, row)
                    
                    if file_info:
                        file_info['column'] = column
                        file_info['row'] = row
                        file_info['context'] = url_info['context']
                        
                        results['by_column'][column].append(file_info)
                        results['summary'][file_info['type']] += 1
                        
                        if file_info.get('downloaded'):
                            print(f"      ✅ Downloaded: {file_info.get('filename', 'file')}")
                        else:
                            print(f"      📄 Processed: {file_info['type']}")
                            
                except Exception as e:
                    error_info = {
                        'url': url,
                        'column': column,
                        'row': row,
                        'error': str(e)
                    }
                    results['errors'].append(error_info)
                    print(f"      ❌ Error: {e}")
                
                # Be respectful with delays
                time.sleep(0.5)
        
        # Save organized summary
        self._save_organized_summary(results)
        
        return results
    
    def _process_url(self, url: str, column_dir: Path, row: int) -> Dict:
        """Process a URL and save to the appropriate column directory."""
        
        # Identify URL type
        if url.endswith('.pdf'):
            return self._download_pdf(url, column_dir, row)
        elif 'github.com' in url:
            return self._process_github(url, column_dir, row)
        elif 'dataverse' in url:
            return self._process_dataverse(url, column_dir, row)
        elif 'physionet.org' in url:
            return self._process_physionet(url, column_dir, row)
        elif 'healthdatanexus.ai' in url:
            return self._process_healthnexus(url, column_dir, row)
        elif 'fairhub.io' in url:
            return self._process_fairhub(url, column_dir, row)
        elif 'doi.org' in url:
            return self._process_doi(url, column_dir, row)
        else:
            return self._process_generic(url, column_dir, row)
    
    def _download_pdf(self, url: str, column_dir: Path, row: int) -> Dict:
        """Download PDF to column directory."""
        info = {
            'type': 'PDF',
            'url': url,
            'row': row
        }
        
        try:
            # Add headers for academic sites
            headers = {}
            if 'biorxiv.org' in url or 'medrxiv.org' in url:
                headers['Referer'] = 'https://www.biorxiv.org/'
                time.sleep(2)
                
            response = self.session.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            
            # Get filename
            filename = os.path.basename(urllib.parse.urlparse(url).path)
            if not filename:
                filename = f"document_row{row}.pdf"
            
            # Add row number to filename for uniqueness
            base, ext = os.path.splitext(filename)
            filename = f"{base}_row{row}{ext}"
            
            # Save to column directory
            file_path = column_dir / filename
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            info['filename'] = filename
            info['path'] = str(file_path)
            info['size'] = len(response.content)
            info['downloaded'] = True
            
        except Exception as e:
            info['error'] = str(e)
            info['downloaded'] = False
            
        return info
    
    def _process_generic(self, url: str, column_dir: Path, row: int) -> Dict:
        """Process generic web page."""
        info = {
            'type': 'Web Page',
            'url': url,
            'row': row
        }
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Create filename based on URL
            parsed_url = urllib.parse.urlparse(url)
            hostname = parsed_url.hostname or 'webpage'
            path_parts = [p for p in parsed_url.path.split('/') if p]
            
            if path_parts:
                base_name = f"{hostname}_{'-'.join(path_parts[:2])}_row{row}"
            else:
                base_name = f"{hostname}_row{row}"
            
            # Clean filename
            base_name = re.sub(r'[^\w\-_]', '_', base_name)
            
            # Save HTML
            html_file = column_dir / f"{base_name}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            info['filename'] = html_file.name
            info['path'] = str(html_file)
            info['size'] = len(response.text)
            
            # Try to extract text
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove scripts and styles
                for script in soup(["script", "style"]):
                    script.decompose()
                
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                # Save text
                text_file = column_dir / f"{base_name}.txt"
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                info['text_file'] = text_file.name
                info['text_size'] = len(text)
                
                # Get title
                title = soup.find('title')
                if title:
                    info['title'] = title.string
                    
            except:
                pass
            
            info['downloaded'] = True
            
        except Exception as e:
            info['error'] = str(e)
            info['downloaded'] = False
            
        return info
    
    def _process_github(self, url: str, column_dir: Path, row: int) -> Dict:
        """Process GitHub repository."""
        info = {
            'type': 'GitHub Repository',
            'url': url,
            'row': row
        }
        
        # Parse GitHub URL
        match = re.search(r'github\.com/([^/]+)/([^/#]+)', url)
        if match:
            owner, repo = match.groups()
            info['owner'] = owner
            info['repo'] = repo
            
            # Save repository info
            repo_file = column_dir / f"github_{owner}_{repo}_row{row}.json"
            
            try:
                # Get repo data via API
                api_url = f"https://api.github.com/repos/{owner}/{repo}"
                response = self.session.get(api_url)
                
                if response.status_code == 200:
                    repo_data = response.json()
                    
                    # Save repo metadata
                    with open(repo_file, 'w') as f:
                        json.dump({
                            'url': url,
                            'name': repo_data.get('name'),
                            'description': repo_data.get('description'),
                            'license': repo_data.get('license', {}).get('name'),
                            'topics': repo_data.get('topics', []),
                            'clone_url': repo_data.get('clone_url'),
                            'row': row
                        }, f, indent=2)
                    
                    info['filename'] = repo_file.name
                    info['path'] = str(repo_file)
                    info['downloaded'] = True
                    
                    # Try to get README
                    readme_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
                    readme_response = self.session.get(readme_url)
                    
                    if readme_response.status_code == 200:
                        readme_data = readme_response.json()
                        readme_content = requests.get(readme_data['download_url']).text
                        
                        readme_file = column_dir / f"github_{owner}_{repo}_README_row{row}.md"
                        with open(readme_file, 'w') as f:
                            f.write(readme_content)
                        
                        info['readme'] = readme_file.name
                        
            except Exception as e:
                info['error'] = str(e)
                info['downloaded'] = False
                
        return info
    
    def _process_dataverse(self, url: str, column_dir: Path, row: int) -> Dict:
        """Process Dataverse dataset."""
        info = {
            'type': 'Dataverse Dataset',
            'url': url,
            'row': row
        }
        
        # Extract DOI
        doi_match = re.search(r'doi:([^&\s]+)', url)
        if doi_match:
            doi = doi_match.group(1)
            info['doi'] = f"doi:{doi}"
            
            # Download landing page
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                # Save HTML
                html_file = column_dir / f"dataverse_{doi.replace('/', '_')}_row{row}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                info['filename'] = html_file.name
                info['path'] = str(html_file)
                info['size'] = len(response.text)
                
                # Extract text
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    text = soup.get_text()
                    
                    text_file = column_dir / f"dataverse_{doi.replace('/', '_')}_row{row}.txt"
                    with open(text_file, 'w', encoding='utf-8') as f:
                        f.write(text)
                    
                    info['text_file'] = text_file.name
                    
                    # Get title
                    title_elem = soup.find('h1', class_='metadata-title') or soup.find('h1')
                    if title_elem:
                        info['title'] = title_elem.get_text(strip=True)
                        
                except:
                    pass
                
                info['downloaded'] = True
                
            except Exception as e:
                info['error'] = str(e)
                info['downloaded'] = False
                
        return info
    
    def _process_physionet(self, url: str, column_dir: Path, row: int) -> Dict:
        """Process PhysioNet dataset."""
        info = {
            'type': 'PhysioNet Dataset',
            'url': url,
            'row': row
        }
        
        # Parse URL
        match = re.search(r'physionet\.org/content/([^/]+)/([^/]+)', url)
        if match:
            dataset_id, version = match.groups()
            info['dataset_id'] = dataset_id
            info['version'] = version
            
            # Download landing page
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                # Save HTML
                html_file = column_dir / f"physionet_{dataset_id}_{version}_row{row}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                info['filename'] = html_file.name
                info['path'] = str(html_file)
                info['size'] = len(response.text)
                
                # Extract text
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    text = soup.get_text()
                    
                    text_file = column_dir / f"physionet_{dataset_id}_{version}_row{row}.txt"
                    with open(text_file, 'w', encoding='utf-8') as f:
                        f.write(text)
                    
                    info['text_file'] = text_file.name
                    
                except:
                    pass
                
                # Add access info
                info['access_note'] = "PhysioNet credentialed access required"
                info['downloaded'] = True
                
            except Exception as e:
                info['error'] = str(e)
                info['downloaded'] = False
                
        return info
    
    def _process_healthnexus(self, url: str, column_dir: Path, row: int) -> Dict:
        """Process Health Data Nexus dataset."""
        info = {
            'type': 'Health Data Nexus',
            'url': url,
            'row': row
        }
        
        # Save metadata
        metadata_file = column_dir / f"healthnexus_row{row}.json"
        with open(metadata_file, 'w') as f:
            json.dump(info, f, indent=2)
        
        info['filename'] = metadata_file.name
        info['path'] = str(metadata_file)
        info['downloaded'] = True
        
        return info
    
    def _process_fairhub(self, url: str, column_dir: Path, row: int) -> Dict:
        """Process FAIRhub dataset."""
        info = {
            'type': 'FAIRhub Dataset',
            'url': url,
            'row': row
        }
        
        # Extract dataset ID
        match = re.search(r'datasets/(\d+)', url)
        if match:
            info['dataset_id'] = match.group(1)
        
        # Save metadata
        metadata_file = column_dir / f"fairhub_row{row}.json"
        with open(metadata_file, 'w') as f:
            json.dump(info, f, indent=2)
        
        info['filename'] = metadata_file.name
        info['path'] = str(metadata_file)
        info['downloaded'] = True
        
        return info
    
    def _process_doi(self, url: str, column_dir: Path, row: int) -> Dict:
        """Process DOI link."""
        info = {
            'type': 'DOI',
            'url': url,
            'row': row
        }
        
        # Extract DOI
        doi_match = re.search(r'doi\.org/(.+)', url)
        if doi_match:
            info['doi'] = doi_match.group(1)
        
        # Save metadata
        metadata_file = column_dir / f"doi_row{row}.json"
        with open(metadata_file, 'w') as f:
            json.dump(info, f, indent=2)
        
        info['filename'] = metadata_file.name
        info['path'] = str(metadata_file)
        info['downloaded'] = True
        
        return info
    
    def _sanitize_filename(self, name: str) -> str:
        """Create safe directory name from column header."""
        # Remove special characters and replace spaces
        safe_name = re.sub(r'[^\w\s-]', '', name)
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        return safe_name.strip('_')
    
    def _save_organized_summary(self, results: Dict):
        """Save summary of organized downloads."""
        # Create summary report
        report_file = self.output_dir / "organized_extraction_report.md"
        
        with open(report_file, 'w') as f:
            f.write("# Organized Dataset Extraction Report\n\n")
            f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Summary statistics
            f.write("## Summary by Type\n\n")
            for type_name, count in results['summary'].items():
                f.write(f"- **{type_name}**: {count}\n")
            
            # Details by column
            f.write("\n## Downloads by Column\n\n")
            
            for column, items in results['by_column'].items():
                safe_column = self._sanitize_filename(column)
                f.write(f"### {column}\n")
                f.write(f"Directory: `{safe_column}/`\n\n")
                
                # Group by type
                by_type = defaultdict(list)
                for item in items:
                    by_type[item['type']].append(item)
                
                for type_name, type_items in by_type.items():
                    f.write(f"#### {type_name} ({len(type_items)})\n\n")
                    
                    for item in type_items:
                        if item.get('downloaded'):
                            status = "✅"
                            filename = item.get('filename', 'file')
                            f.write(f"- {status} Row {item['row']}: `{filename}`\n")
                            if 'title' in item:
                                f.write(f"  - Title: {item['title']}\n")
                            if 'doi' in item:
                                f.write(f"  - DOI: {item['doi']}\n")
                        else:
                            status = "❌"
                            f.write(f"- {status} Row {item['row']}: Failed - {item.get('error', 'Unknown error')}\n")
                    
                    f.write("\n")
            
            # Errors section
            if results['errors']:
                f.write("\n## Errors\n\n")
                for error in results['errors']:
                    f.write(f"- Column: {error['column']}, Row: {error['row']}\n")
                    f.write(f"  - URL: {error['url']}\n")
                    f.write(f"  - Error: {error['error']}\n\n")
        
        # Save JSON summary
        summary_file = self.output_dir / "organized_extraction_summary.json"
        with open(summary_file, 'w') as f:
            json.dump({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'statistics': results['summary'],
                'by_column': results['by_column'],
                'errors': results['errors']
            }, f, indent=2)
        
        print(f"\n📄 Report saved: {report_file}")
        print(f"📊 Summary saved: {summary_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract and organize datasets by spreadsheet columns",
        epilog="Example: python organized_dataset_extractor.py 'https://docs.google.com/spreadsheets/d/.../export?format=csv' -o organized_data"
    )
    parser.add_argument("input", help="Google Sheets CSV export URL or local CSV file")
    parser.add_argument("-o", "--output", default="organized_datasets", help="Output directory")
    
    args = parser.parse_args()
    
    extractor = OrganizedDatasetExtractor(args.output)
    results = extractor.process_spreadsheet(args.input)
    
    print("\n" + "="*60)
    print("ORGANIZED EXTRACTION COMPLETE")
    print("="*60)
    
    # Print summary
    total_downloads = sum(len(items) for items in results['by_column'].values())
    print(f"📂 Columns processed: {len(results['by_column'])}")
    print(f"📥 Total items processed: {total_downloads}")
    print(f"❌ Errors: {len(results['errors'])}")
    print(f"\n📁 Output directory: {extractor.output_dir.absolute()}")
    
    # Show directory structure
    print("\n📂 Directory structure created:")
    for column in results['by_column'].keys():
        safe_column = extractor._sanitize_filename(column)
        print(f"   └── {safe_column}/")


if __name__ == "__main__":
    main()