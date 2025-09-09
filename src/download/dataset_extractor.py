#!/usr/bin/env python3
"""
Enhanced dataset extractor that handles various dataset repositories and documentation sites.
Extracts metadata, downloadable files, and dataset information from various sources.
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


class DatasetExtractor:
    """Extract dataset information and files from various repositories."""
    
    def __init__(self, output_dir: str = "datasets"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
    def extract_from_url(self, url: str) -> Dict:
        """Extract dataset information based on URL pattern."""
        
        # Identify the type of resource
        if 'github.com' in url:
            return self.extract_github(url)
        elif 'dataverse' in url:
            return self.extract_dataverse(url)
        elif 'physionet.org' in url:
            return self.extract_physionet(url)
        elif 'healthdatanexus.ai' in url:
            return self.extract_healthnexus(url)
        elif 'fairhub.io' in url:
            return self.extract_fairhub(url)
        elif 'doi.org' in url:
            return self.extract_doi(url)
        elif url.endswith('.pdf'):
            return self.download_pdf(url)
        else:
            return self.extract_generic(url)
    
    def extract_github(self, url: str) -> Dict:
        """Extract information from GitHub repositories."""
        info = {
            'type': 'GitHub Repository',
            'url': url,
            'files': [],
            'metadata': {}
        }
        
        # Parse GitHub URL
        match = re.search(r'github\.com/([^/]+)/([^/#]+)', url)
        if match:
            owner, repo = match.groups()
            info['metadata']['owner'] = owner
            info['metadata']['repository'] = repo
            
            # Get repository information via API
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            try:
                response = self.session.get(api_url)
                if response.status_code == 200:
                    repo_data = response.json()
                    info['metadata']['description'] = repo_data.get('description', '')
                    info['metadata']['license'] = repo_data.get('license', {}).get('name', 'Unknown')
                    info['metadata']['topics'] = repo_data.get('topics', [])
                    
                    # Check for README
                    readme_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
                    readme_response = self.session.get(readme_url)
                    if readme_response.status_code == 200:
                        readme_data = readme_response.json()
                        info['files'].append({
                            'name': 'README.md',
                            'url': readme_data.get('download_url', ''),
                            'size': readme_data.get('size', 0)
                        })
                    
                    # Suggest clone command
                    info['metadata']['clone_command'] = f"git clone https://github.com/{owner}/{repo}.git"
                    
                    # Save metadata
                    self._save_metadata(info, f"github_{owner}_{repo}")
                    
                    # Download and save README content
                    if readme_response.status_code == 200:
                        readme_file = self.output_dir / f"github_{owner}_{repo}_README.md"
                        readme_content = requests.get(readme_data.get('download_url', '')).text
                        with open(readme_file, 'w', encoding='utf-8') as f:
                            f.write(readme_content)
                        info['files'].append({
                            'name': 'README.md',
                            'path': str(readme_file),
                            'size': len(readme_content)
                        })
                    
            except Exception as e:
                info['error'] = str(e)
                
        return info
    
    def extract_dataverse(self, url: str) -> Dict:
        """Extract dataset information from Dataverse."""
        info = {
            'type': 'Dataverse Dataset',
            'url': url,
            'files': [],
            'metadata': {}
        }
        
        # Extract DOI from URL
        doi_match = re.search(r'doi:([^&\s]+)', url)
        if doi_match:
            doi = doi_match.group(1)
            info['metadata']['doi'] = f"doi:{doi}"
            
            # Try to get dataset metadata
            info['metadata']['access_instructions'] = "Visit the Dataverse URL and use the 'Download' button for files"
            
            # Download the landing page
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                # Save HTML
                html_file = self.output_dir / f"dataverse_{doi.replace('/', '_')}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                    
                info['files'].append({
                    'name': html_file.name,
                    'path': str(html_file),
                    'size': len(response.text),
                    'type': 'HTML',
                    'description': 'Dataverse dataset landing page'
                })
                
                # Try to extract dataset title and description
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for dataset title
                    title_elem = soup.find('h1', class_='metadata-title') or soup.find('h1')
                    if title_elem:
                        info['metadata']['title'] = title_elem.get_text(strip=True)
                        
                    # Save text version
                    text = soup.get_text()
                    text_file = self.output_dir / f"dataverse_{doi.replace('/', '_')}.txt"
                    with open(text_file, 'w', encoding='utf-8') as f:
                        f.write(text)
                        
                    info['files'].append({
                        'name': text_file.name,
                        'path': str(text_file),
                        'size': len(text),
                        'type': 'TEXT'
                    })
                    
                except:
                    pass
                    
            except Exception as e:
                info['metadata']['download_error'] = str(e)
            
            # Save metadata
            self._save_metadata(info, f"dataverse_{doi.replace('/', '_')}")
            
        return info
    
    def extract_physionet(self, url: str) -> Dict:
        """Extract dataset information from PhysioNet."""
        info = {
            'type': 'PhysioNet Dataset',
            'url': url,
            'files': [],
            'metadata': {}
        }
        
        # Parse PhysioNet URL for dataset ID and version
        match = re.search(r'physionet\.org/content/([^/]+)/([^/]+)', url)
        if match:
            dataset_id, version = match.groups()
            info['metadata']['dataset_id'] = dataset_id
            info['metadata']['version'] = version
            
            # PhysioNet requires credentialed access for most datasets
            info['metadata']['access_requirements'] = "PhysioNet credentialed access required"
            info['metadata']['access_instructions'] = (
                "1. Create a PhysioNet account\n"
                "2. Complete required training (CITI Data or Specimens Only)\n"
                "3. Request access to this specific dataset\n"
                "4. Use wget with credentials to download files"
            )
            
            # Files page URL
            files_url = f"{url}files/"
            info['metadata']['files_url'] = files_url
            
            # Download the dataset landing page
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                # Save HTML
                html_file = self.output_dir / f"physionet_{dataset_id}_{version}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                    
                info['files'].append({
                    'name': html_file.name,
                    'path': str(html_file),
                    'size': len(response.text),
                    'type': 'HTML',
                    'description': 'PhysioNet dataset landing page'
                })
                
                # Extract and save text
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    text = soup.get_text()
                    
                    text_file = self.output_dir / f"physionet_{dataset_id}_{version}.txt"
                    with open(text_file, 'w', encoding='utf-8') as f:
                        f.write(text)
                        
                    info['files'].append({
                        'name': text_file.name,
                        'path': str(text_file),
                        'size': len(text),
                        'type': 'TEXT'
                    })
                except:
                    pass
                    
            except Exception as e:
                info['metadata']['download_error'] = str(e)
            
            # Save metadata
            self._save_metadata(info, f"physionet_{dataset_id}_{version}")
            
        return info
    
    def extract_healthnexus(self, url: str) -> Dict:
        """Extract information from Health Data Nexus."""
        info = {
            'type': 'Health Data Nexus Dataset',
            'url': url,
            'files': [],
            'metadata': {}
        }
        
        # Parse dataset ID from URL
        match = re.search(r'content/([^/]+)/([^/]+)', url)
        if match:
            dataset_id, version = match.groups()
            info['metadata']['dataset_id'] = dataset_id
            info['metadata']['version'] = version
            info['metadata']['access_instructions'] = "Visit Health Data Nexus for access requirements"
            
            # Save metadata
            self._save_metadata(info, f"healthnexus_{dataset_id}_{version}")
            
        return info
    
    def extract_fairhub(self, url: str) -> Dict:
        """Extract information from FAIRhub."""
        info = {
            'type': 'FAIRhub Dataset',
            'url': url,
            'files': [],
            'metadata': {}
        }
        
        # Extract dataset ID
        match = re.search(r'datasets/(\d+)', url)
        if match:
            dataset_id = match.group(1)
            info['metadata']['dataset_id'] = dataset_id
            info['metadata']['platform'] = 'FAIRhub'
            info['metadata']['access_instructions'] = "Use FAIRhub platform for data access"
            
            # Save metadata
            self._save_metadata(info, f"fairhub_dataset_{dataset_id}")
            
        return info
    
    def extract_doi(self, url: str) -> Dict:
        """Extract information from DOI links."""
        info = {
            'type': 'DOI',
            'url': url,
            'metadata': {}
        }
        
        # Extract DOI
        doi_match = re.search(r'doi\.org/(.+)', url)
        if doi_match:
            doi = doi_match.group(1)
            info['metadata']['doi'] = doi
            info['metadata']['resolver_url'] = url
            info['metadata']['note'] = "This is a DOI resolver link. The actual content location varies."
            
            # Save metadata
            self._save_metadata(info, f"doi_{doi.replace('/', '_')}")
            
        return info
    
    def download_pdf(self, url: str) -> Dict:
        """Download a PDF file."""
        info = {
            'type': 'PDF Document',
            'url': url,
            'files': [],
            'metadata': {}
        }
        
        try:
            # Add headers for academic sites
            headers = {}
            if 'biorxiv.org' in url or 'medrxiv.org' in url:
                headers['Referer'] = 'https://www.biorxiv.org/'
                time.sleep(2)  # Be respectful
                
            response = self.session.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            
            # Get filename
            filename = os.path.basename(urllib.parse.urlparse(url).path)
            if not filename:
                filename = f"document_{hash(url) & 0xFFFFFF:06x}.pdf"
                
            # Save file
            file_path = self.output_dir / filename
            with open(file_path, 'wb') as f:
                f.write(response.content)
                
            info['files'].append({
                'name': filename,
                'path': str(file_path),
                'size': len(response.content),
                'downloaded': True
            })
            
            info['metadata']['status'] = 'Downloaded'
            
        except Exception as e:
            info['error'] = str(e)
            info['metadata']['status'] = 'Failed'
            
        return info
    
    def extract_generic(self, url: str) -> Dict:
        """Generic extraction for unknown URL types - downloads the web page content."""
        info = {
            'type': 'Web Page',
            'url': url,
            'files': [],
            'metadata': {
                'note': 'Generic web page - content downloaded'
            }
        }
        
        try:
            # Download the web page
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Determine filename and format
            parsed_url = urllib.parse.urlparse(url)
            hostname = parsed_url.hostname or 'webpage'
            path_parts = [p for p in parsed_url.path.split('/') if p]
            
            if path_parts:
                base_name = f"{hostname}_{'-'.join(path_parts[:3])}"
            else:
                base_name = hostname
                
            # Clean filename
            base_name = re.sub(r'[^\w\-_]', '_', base_name)
            
            # Save HTML content
            html_file = self.output_dir / f"{base_name}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
                
            info['files'].append({
                'name': html_file.name,
                'path': str(html_file),
                'size': len(response.text),
                'type': 'HTML'
            })
            
            # Try to extract text content
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                    
                # Get text
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                # Save text version
                text_file = self.output_dir / f"{base_name}.txt"
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(text)
                    
                info['files'].append({
                    'name': text_file.name,
                    'path': str(text_file),
                    'size': len(text),
                    'type': 'TEXT'
                })
                
                # Extract title if possible
                title = soup.find('title')
                if title:
                    info['metadata']['title'] = title.string
                    
            except ImportError:
                info['metadata']['note'] = 'BeautifulSoup not available - saved HTML only'
            except Exception as e:
                info['metadata']['text_extraction_error'] = str(e)
                
            info['metadata']['status'] = 'Downloaded'
            
        except Exception as e:
            info['error'] = str(e)
            info['metadata']['status'] = 'Failed'
        
        # Save metadata
        self._save_metadata(info, f"webpage_{hash(url) & 0xFFFFFF:06x}")
        
        return info
    
    def _save_metadata(self, info: Dict, name: str):
        """Save metadata to JSON file."""
        metadata_file = self.output_dir / f"{name}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(info, f, indent=2)
        info['metadata_file'] = str(metadata_file)
    
    def process_csv(self, csv_path: str) -> Dict[str, List[Dict]]:
        """Process a CSV file and extract all datasets."""
        results = {
            'pdfs': [],
            'repositories': [],
            'dois': [],
            'other': [],
            'errors': []
        }
        
        # Check if input is a URL or file path
        if csv_path.startswith(('http://', 'https://')):
            # Download CSV from URL (e.g., Google Sheets export)
            try:
                response = self.session.get(csv_path, timeout=30)
                response.raise_for_status()
                content = response.text
            except Exception as e:
                print(f"Error downloading CSV from URL: {e}")
                return results
        else:
            # Read local file
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(csv_path, 'r', encoding='latin-1') as f:
                    content = f.read()
        
        # Extract all URLs from CSV
        lines = content.strip().split('\n')
        csv_reader = csv.reader(lines)
        
        all_urls = set()
        for row in csv_reader:
            for cell in row:
                # Find URLs in the cell
                url_pattern = r'https?://[^\s,<>"\']*'
                found_urls = re.findall(url_pattern, cell)
                for url in found_urls:
                    url = url.rstrip('.,;:!?)')
                    all_urls.add(url)
        
        print(f"\n📊 Found {len(all_urls)} unique URLs to process\n")
        
        # Process each URL
        for i, url in enumerate(all_urls, 1):
            print(f"[{i}/{len(all_urls)}] Processing: {url}")
            
            try:
                info = self.extract_from_url(url)
                
                # Categorize results
                if info['type'] == 'PDF Document' and not info.get('error'):
                    results['pdfs'].append(info)
                    print(f"  ✅ PDF downloaded: {info['files'][0]['name']}")
                elif info['type'] == 'DOI':
                    results['dois'].append(info)
                    print(f"  📎 DOI recorded: {info['metadata']['doi']}")
                elif 'Repository' in info['type'] or 'Dataset' in info['type']:
                    results['repositories'].append(info)
                    print(f"  📦 {info['type']} metadata saved")
                else:
                    results['other'].append(info)
                    print(f"  📄 {info['type']} processed")
                    
                if info.get('error'):
                    results['errors'].append(info)
                    print(f"  ❌ Error: {info['error']}")
                    
            except Exception as e:
                error_info = {'url': url, 'error': str(e)}
                results['errors'].append(error_info)
                print(f"  ❌ Failed: {e}")
            
            # Small delay between requests
            time.sleep(0.5)
        
        # Save summary
        self._save_summary(results)
        
        return results
    
    def _save_summary(self, results: Dict[str, List[Dict]]):
        """Save a summary of all processed resources."""
        summary_file = self.output_dir / "extraction_summary.json"
        
        summary = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'statistics': {
                'pdfs_downloaded': len(results['pdfs']),
                'repositories_found': len(results['repositories']),
                'dois_found': len(results['dois']),
                'other_resources': len(results['other']),
                'errors': len(results['errors'])
            },
            'results': results
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Also create a human-readable report
        report_file = self.output_dir / "extraction_report.md"
        with open(report_file, 'w') as f:
            f.write("# Dataset Extraction Report\n\n")
            f.write(f"Generated: {summary['timestamp']}\n\n")
            
            f.write("## Summary\n\n")
            for key, value in summary['statistics'].items():
                f.write(f"- **{key.replace('_', ' ').title()}**: {value}\n")
            
            f.write("\n## Downloaded PDFs\n\n")
            for pdf in results['pdfs']:
                f.write(f"- ✅ {pdf['files'][0]['name']} ({pdf['files'][0]['size']:,} bytes)\n")
            
            f.write("\n## Dataset Repositories\n\n")
            for repo in results['repositories']:
                f.write(f"### {repo['type']}\n")
                f.write(f"- **URL**: {repo['url']}\n")
                f.write(f"- **Metadata saved**: {repo.get('metadata_file', 'N/A')}\n")
                if 'access_instructions' in repo['metadata']:
                    f.write(f"- **Access**: {repo['metadata']['access_instructions']}\n")
                f.write("\n")
            
            if results['errors']:
                f.write("\n## Errors\n\n")
                for error in results['errors']:
                    f.write(f"- ❌ {error.get('url', 'Unknown')}: {error.get('error', 'Unknown error')}\n")
        
        print(f"\n📊 Summary saved to: {summary_file}")
        print(f"📄 Report saved to: {report_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract datasets and metadata from various sources",
        epilog="Example: python dataset_extractor.py input.csv -o datasets"
    )
    parser.add_argument("input", help="CSV file containing URLs")
    parser.add_argument("-o", "--output", default="datasets", help="Output directory")
    
    args = parser.parse_args()
    
    extractor = DatasetExtractor(args.output)
    results = extractor.process_csv(args.input)
    
    print("\n" + "="*60)
    print("EXTRACTION COMPLETE")
    print("="*60)
    print(f"✅ PDFs downloaded: {len(results['pdfs'])}")
    print(f"📦 Repositories found: {len(results['repositories'])}")
    print(f"📎 DOIs found: {len(results['dois'])}")
    print(f"📄 Other resources: {len(results['other'])}")
    print(f"❌ Errors: {len(results['errors'])}")
    print(f"\n📂 Output directory: {extractor.output_dir.absolute()}")


if __name__ == "__main__":
    main()