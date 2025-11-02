#!/usr/bin/env python3
"""
Enhanced dataset extractor with improved content downloading.
Fixes issues with DOI resolution, concatenated URLs, and platform-specific handlers.
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
from bs4 import BeautifulSoup


class EnhancedOrganizedExtractor:
    """Enhanced extractor with better content downloading for DOI, FAIRhub, etc."""

    def __init__(self, output_dir: str = "downloads_by_column_enhanced"):
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
                    # Find URLs in the cell - handle concatenated URLs
                    urls = self._split_concatenated_urls(cell_value)
                    for url in urls:
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

    def _split_concatenated_urls(self, cell_value: str) -> List[str]:
        """Split concatenated URLs that were pasted together without separators."""
        # Find all URLs in the cell
        urls = re.findall(r'https?://[^\s<>"\']+', cell_value)

        if not urls:
            return []

        # If we found multiple URLs, they might be concatenated
        # Split them properly
        cleaned_urls = []
        for url in urls:
            # Remove trailing punctuation
            url = url.rstrip('.,;:!?)')
            cleaned_urls.append(url)

        return cleaned_urls

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
        elif 'docs.google.com/document' in url:
            return self._process_google_doc(url, column_dir, row)
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

    def _process_doi(self, url: str, column_dir: Path, row: int) -> Dict:
        """Enhanced DOI processing that follows redirects and downloads actual content."""
        info = {
            'type': 'DOI',
            'url': url,
            'row': row
        }

        try:
            # Extract DOI
            doi_match = re.search(r'doi\.org/(.+)', url)
            if doi_match:
                info['doi'] = doi_match.group(1)

            # Follow DOI to actual resource
            print(f"         Following DOI redirect...")
            response = self.session.get(url, allow_redirects=True, timeout=30)
            final_url = response.url
            info['resolved_url'] = final_url
            print(f"         Resolved to: {final_url}")

            # Check if it resolved to a PDF
            content_type = response.headers.get('content-type', '')
            if 'pdf' in content_type or final_url.endswith('.pdf'):
                print(f"         Found PDF directly!")
                # Download the PDF
                return self._download_pdf_content(response.content, column_dir, row, info)

            # Check for PDF links on the landing page
            pdf_url = self._find_pdf_link(response.text, final_url)
            if pdf_url:
                print(f"         Found PDF link: {pdf_url}")
                # Download the linked PDF
                pdf_info = self._download_pdf(pdf_url, column_dir, row)
                # Merge DOI info
                pdf_info.update({
                    'doi': info.get('doi'),
                    'resolved_url': final_url
                })
                return pdf_info

            # Save the landing page content as fallback
            print(f"         No PDF found, saving landing page")
            return self._save_web_content(response, column_dir, row, info)

        except Exception as e:
            info['error'] = str(e)
            info['downloaded'] = False

            # Save metadata even on error
            metadata_file = column_dir / f"doi_row{row}.json"
            with open(metadata_file, 'w') as f:
                json.dump(info, f, indent=2)

            info['filename'] = metadata_file.name
            info['path'] = str(metadata_file)

        return info

    def _download_pdf_content(self, content: bytes, column_dir: Path, row: int, info: Dict) -> Dict:
        """Save PDF content from response."""
        filename = f"doi_resolved_row{row}.pdf"

        file_path = column_dir / filename
        with open(file_path, 'wb') as f:
            f.write(content)

        info['filename'] = filename
        info['path'] = str(file_path)
        info['size'] = len(content)
        info['downloaded'] = True
        info['type'] = 'DOI (PDF)'

        return info

    def _find_pdf_link(self, html_content: str, base_url: str) -> str:
        """Find PDF download link in HTML page."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Common patterns for PDF links
            patterns = [
                # Direct PDF link
                soup.find('a', {'href': re.compile(r'\.pdf$', re.I)}),
                # Link with 'pdf' in class
                soup.find('a', {'class': re.compile(r'pdf', re.I)}),
                # Link with 'PDF' in title
                soup.find('a', {'title': re.compile(r'PDF', re.I)}),
                # Link with PDF text
                soup.find('a', string=re.compile(r'PDF|Download PDF|Full Text PDF', re.I)),
                # Meta tag with PDF
                soup.find('meta', {'name': 'citation_pdf_url'}),
            ]

            for link in patterns:
                if link and link.name == 'meta':
                    # Meta tag
                    pdf_url = link.get('content')
                    if pdf_url:
                        return urllib.parse.urljoin(base_url, pdf_url)
                elif link and link.get('href'):
                    # Anchor tag
                    return urllib.parse.urljoin(base_url, link['href'])

        except Exception as e:
            print(f"         Error finding PDF link: {e}")

        return None

    def _save_web_content(self, response, column_dir: Path, row: int, info: Dict) -> Dict:
        """Save web page content as HTML and text."""
        # Create filename based on URL
        parsed_url = urllib.parse.urlparse(response.url)
        hostname = parsed_url.hostname or 'webpage'
        path_parts = [p for p in parsed_url.path.split('/') if p]

        if 'doi' in info:
            base_name = f"doi_{info['doi'].replace('/', '_')}_row{row}"
        elif path_parts:
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

        # Extract text
        try:
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

        except Exception as e:
            print(f"         Error extracting text: {e}")

        info['downloaded'] = True
        info['type'] = 'DOI (Landing Page)'

        return info

    def _process_fairhub(self, url: str, column_dir: Path, row: int) -> Dict:
        """Enhanced FAIRhub processing - downloads full landing page with tabs."""
        info = {
            'type': 'FAIRhub Dataset',
            'url': url,
            'row': row
        }

        # Extract dataset ID
        match = re.search(r'datasets/(\d+)', url)
        if match:
            info['dataset_id'] = match.group(1)
            dataset_id = match.group(1)
        else:
            dataset_id = 'unknown'

        try:
            # Download the FAIRhub landing page
            print(f"         Downloading FAIRhub page...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Save HTML
            html_file = column_dir / f"fairhub_dataset_{dataset_id}_row{row}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(response.text)

            info['filename'] = html_file.name
            info['path'] = str(html_file)
            info['size'] = len(response.text)

            # Extract text and metadata
            soup = None
            try:
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text()

                text_file = column_dir / f"fairhub_dataset_{dataset_id}_row{row}.txt"
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(text)

                info['text_file'] = text_file.name

                # Try to extract title
                title = soup.find('h1') or soup.find('title')
                if title:
                    info['title'] = title.get_text(strip=True)

            except Exception as e:
                print(f"         Error extracting text: {e}")

            # Download tab content
            if soup:
                info['tabs'] = self._download_fairhub_tabs(url, dataset_id, column_dir, row, soup)

            info['downloaded'] = True

        except Exception as e:
            info['error'] = str(e)
            info['downloaded'] = False

            # Save metadata as fallback
            metadata_file = column_dir / f"fairhub_row{row}.json"
            with open(metadata_file, 'w') as f:
                json.dump(info, f, indent=2)

            info['filename'] = metadata_file.name
            info['path'] = str(metadata_file)

        return info

    def _download_fairhub_tabs(self, base_url: str, dataset_id: str, column_dir: Path, row: int, soup: BeautifulSoup) -> List[Dict]:
        """Download content from FAIRhub tabs."""
        tabs_info = []

        print(f"         Scanning for FAIRhub tabs...")

        try:
            # Look for tab navigation in the page
            # FAIRhub typically uses href patterns like /datasets/{id}/files, /datasets/{id}/metadata, etc.
            tab_links = soup.find_all('a', href=re.compile(r'/datasets/\d+/'))

            # Extract unique tab paths
            tab_paths = set()
            for link in tab_links:
                href = link.get('href', '')
                # Extract path after dataset ID
                match = re.search(r'/datasets/\d+/([^/?#]+)', href)
                if match:
                    tab_paths.add(match.group(1))

            # Also check for common tab patterns
            common_tabs = ['files', 'metadata', 'versions', 'activity', 'citation']
            for tab in common_tabs:
                tab_paths.add(tab)

            # Download each tab
            for tab_path in tab_paths:
                try:
                    tab_url = f"{base_url.rstrip('/')}/{tab_path}"

                    response = self.session.get(tab_url, timeout=30)
                    if response.status_code == 200:
                        # Save tab HTML
                        tab_html_file = column_dir / f"fairhub_dataset_{dataset_id}_tab_{tab_path}_row{row}.html"
                        with open(tab_html_file, 'w', encoding='utf-8') as f:
                            f.write(response.text)

                        # Extract text
                        try:
                            tab_soup = BeautifulSoup(response.text, 'html.parser')
                            tab_text = tab_soup.get_text()

                            tab_text_file = column_dir / f"fairhub_dataset_{dataset_id}_tab_{tab_path}_row{row}.txt"
                            with open(tab_text_file, 'w', encoding='utf-8') as f:
                                f.write(tab_text)

                            tabs_info.append({
                                'tab': tab_path,
                                'html_file': tab_html_file.name,
                                'text_file': tab_text_file.name,
                                'size': len(response.text)
                            })

                            print(f"         ✅ {tab_path} tab downloaded")

                        except Exception as e:
                            print(f"         ⚠️  {tab_path} tab: error extracting text - {e}")

                    # Small delay between tabs
                    time.sleep(0.5)

                except Exception as e:
                    print(f"         ⚠️  {tab_path} tab: {e}")

        except Exception as e:
            print(f"         ⚠️  Error scanning for tabs: {e}")

        return tabs_info

    def _process_healthnexus(self, url: str, column_dir: Path, row: int) -> Dict:
        """Enhanced Health Data Nexus processing - downloads full landing page with tabs."""
        info = {
            'type': 'Health Data Nexus',
            'url': url,
            'row': row
        }

        try:
            # Download the Health Data Nexus landing page
            print(f"         Downloading Health Data Nexus page...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Save HTML
            html_file = column_dir / f"healthnexus_row{row}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(response.text)

            info['filename'] = html_file.name
            info['path'] = str(html_file)
            info['size'] = len(response.text)

            # Extract text
            soup = None
            try:
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text()

                text_file = column_dir / f"healthnexus_row{row}.txt"
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(text)

                info['text_file'] = text_file.name

            except Exception as e:
                print(f"         Error extracting text: {e}")

            # Download tab content
            if soup:
                info['tabs'] = self._download_healthnexus_tabs(url, column_dir, row, soup)

            info['downloaded'] = True

        except Exception as e:
            info['error'] = str(e)
            info['downloaded'] = False

            # Save metadata as fallback
            metadata_file = column_dir / f"healthnexus_row{row}.json"
            with open(metadata_file, 'w') as f:
                json.dump(info, f, indent=2)

            info['filename'] = metadata_file.name
            info['path'] = str(metadata_file)

        return info

    def _download_healthnexus_tabs(self, base_url: str, column_dir: Path, row: int, soup: BeautifulSoup) -> List[Dict]:
        """Download content from Health Data Nexus tabs."""
        tabs_info = []

        print(f"         Scanning for Health Data Nexus tabs...")

        try:
            # Look for tab navigation in the page
            # Health Data Nexus may use various patterns for tabs
            tab_links = soup.find_all('a', href=re.compile(r'#|tab='))

            # Extract unique tab identifiers
            tab_ids = set()
            for link in tab_links:
                href = link.get('href', '')
                # Check for hash-based tabs
                if '#' in href:
                    tab_id = href.split('#')[-1]
                    if tab_id:
                        tab_ids.add(tab_id)
                # Check for query parameter tabs
                match = re.search(r'tab=([^&]+)', href)
                if match:
                    tab_ids.add(match.group(1))

            # Also check for common tab patterns
            common_tabs = ['files', 'metadata', 'documentation', 'versions']
            for tab in common_tabs:
                tab_ids.add(tab)

            # Download each tab
            for tab_id in tab_ids:
                try:
                    # Try different URL patterns
                    tab_urls = [
                        f"{base_url}#{tab_id}",  # Hash-based
                        f"{base_url}?tab={tab_id}",  # Query parameter
                        f"{base_url}/{tab_id}"  # Path-based
                    ]

                    for tab_url in tab_urls:
                        try:
                            response = self.session.get(tab_url, timeout=30)
                            if response.status_code == 200 and len(response.text) > 1000:  # Only if substantial content
                                # Save tab HTML
                                tab_html_file = column_dir / f"healthnexus_tab_{tab_id}_row{row}.html"
                                with open(tab_html_file, 'w', encoding='utf-8') as f:
                                    f.write(response.text)

                                # Extract text
                                try:
                                    tab_soup = BeautifulSoup(response.text, 'html.parser')
                                    tab_text = tab_soup.get_text()

                                    tab_text_file = column_dir / f"healthnexus_tab_{tab_id}_row{row}.txt"
                                    with open(tab_text_file, 'w', encoding='utf-8') as f:
                                        f.write(tab_text)

                                    tabs_info.append({
                                        'tab': tab_id,
                                        'html_file': tab_html_file.name,
                                        'text_file': tab_text_file.name,
                                        'size': len(response.text)
                                    })

                                    print(f"         ✅ {tab_id} tab downloaded")
                                    break  # Found working URL pattern

                                except Exception as e:
                                    print(f"         ⚠️  {tab_id} tab: error extracting text - {e}")

                        except:
                            continue  # Try next URL pattern

                    # Small delay between tabs
                    time.sleep(0.5)

                except Exception as e:
                    print(f"         ⚠️  {tab_id} tab: {e}")

        except Exception as e:
            print(f"         ⚠️  Error scanning for tabs: {e}")

        return tabs_info

    def _process_google_doc(self, url: str, column_dir: Path, row: int) -> Dict:
        """Process Google Docs by trying to export as PDF."""
        info = {
            'type': 'Google Doc',
            'url': url,
            'row': row
        }

        # Try to convert share URL to export URL
        doc_id_match = re.search(r'/d/([^/]+)', url)
        if doc_id_match:
            doc_id = doc_id_match.group(1)
            info['doc_id'] = doc_id

            # Try PDF export
            export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=pdf"

            try:
                print(f"         Attempting PDF export...")
                response = self.session.get(export_url, timeout=30)

                if response.status_code == 200 and 'pdf' in response.headers.get('content-type', ''):
                    # Successfully exported as PDF
                    filename = f"google_doc_{doc_id}_row{row}.pdf"
                    file_path = column_dir / filename

                    with open(file_path, 'wb') as f:
                        f.write(response.content)

                    info['filename'] = filename
                    info['path'] = str(file_path)
                    info['size'] = len(response.content)
                    info['downloaded'] = True
                    info['note'] = 'Exported as PDF'

                    return info

            except Exception as e:
                print(f"         PDF export failed: {e}")

        # Fallback: download HTML version
        try:
            response = self.session.get(url, timeout=30)
            html_file = column_dir / f"google_doc_row{row}.html"

            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(response.text)

            info['filename'] = html_file.name
            info['path'] = str(html_file)
            info['size'] = len(response.text)
            info['downloaded'] = True
            info['note'] = 'HTML wrapper only - document may require authentication'

        except Exception as e:
            info['error'] = str(e)
            info['downloaded'] = False

        return info

    # Include all other methods from the original class
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
        """Process Dataverse dataset with tab content scraping."""
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

                # Save main page HTML
                html_file = column_dir / f"dataverse_{doi.replace('/', '_')}_row{row}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)

                info['filename'] = html_file.name
                info['path'] = str(html_file)
                info['size'] = len(response.text)

                # Extract text from main page
                try:
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

                # Download tab content
                info['tabs'] = self._download_dataverse_tabs(url, doi, column_dir, row)

                info['downloaded'] = True

            except Exception as e:
                info['error'] = str(e)
                info['downloaded'] = False

        return info

    def _download_dataverse_tabs(self, base_url: str, doi: str, column_dir: Path, row: int) -> List[Dict]:
        """Download content from Dataverse tabs."""
        tabs_info = []

        # Common Dataverse tabs
        tabs = [
            ('files', 'Files'),
            ('metadata', 'Metadata'),
            ('terms', 'Terms'),
            ('versions', 'Versions')
        ]

        print(f"         Downloading Dataverse tabs...")

        for tab_id, tab_name in tabs:
            try:
                # Construct tab URL
                parsed = urllib.parse.urlparse(base_url)
                params = urllib.parse.parse_qs(parsed.query)
                params['tab'] = [tab_id]
                new_query = urllib.parse.urlencode(params, doseq=True)
                tab_url = urllib.parse.urlunparse((
                    parsed.scheme, parsed.netloc, parsed.path,
                    parsed.params, new_query, parsed.fragment
                ))

                # Download tab content
                response = self.session.get(tab_url, timeout=30)
                if response.status_code == 200:
                    # Save tab HTML
                    tab_html_file = column_dir / f"dataverse_{doi.replace('/', '_')}_tab_{tab_id}_row{row}.html"
                    with open(tab_html_file, 'w', encoding='utf-8') as f:
                        f.write(response.text)

                    # Extract text from tab
                    try:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        text = soup.get_text()

                        tab_text_file = column_dir / f"dataverse_{doi.replace('/', '_')}_tab_{tab_id}_row{row}.txt"
                        with open(tab_text_file, 'w', encoding='utf-8') as f:
                            f.write(text)

                        tabs_info.append({
                            'tab': tab_name,
                            'html_file': tab_html_file.name,
                            'text_file': tab_text_file.name,
                            'size': len(response.text)
                        })

                        print(f"         ✅ {tab_name} tab downloaded")

                    except Exception as e:
                        print(f"         ⚠️  {tab_name} tab: error extracting text - {e}")

                else:
                    print(f"         ⚠️  {tab_name} tab: HTTP {response.status_code}")

                # Small delay between tabs
                time.sleep(0.5)

            except Exception as e:
                print(f"         ⚠️  {tab_name} tab: {e}")

        return tabs_info

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
            f.write("# Enhanced Organized Dataset Extraction Report\n\n")
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
                            if 'resolved_url' in item:
                                f.write(f"  - Resolved: {item['resolved_url']}\n")
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
        description="Enhanced dataset extractor with improved content downloading",
        epilog="Example: python enhanced_organized_extractor.py 'https://docs.google.com/spreadsheets/d/.../export?format=csv' -o downloads_enhanced"
    )
    parser.add_argument("input", help="Google Sheets CSV export URL or local CSV file")
    parser.add_argument("-o", "--output", default="downloads_by_column_enhanced", help="Output directory")

    args = parser.parse_args()

    extractor = EnhancedOrganizedExtractor(args.output)
    results = extractor.process_spreadsheet(args.input)

    print("\n" + "="*60)
    print("ENHANCED EXTRACTION COMPLETE")
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
