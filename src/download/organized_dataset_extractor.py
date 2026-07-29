#!/usr/bin/env python3
"""
Enhanced dataset extractor that organizes downloads by spreadsheet column headings.
Maintains the original structure from the source spreadsheet.
"""
import csv
import os
import re
import requests
import shutil
import tempfile
import urllib.parse
from pathlib import Path
from typing import List, Dict
import argparse
import time
import json
from collections import defaultdict
import yaml

from data_sheets_schema.rocrate_normalize import document_corpus_exclusions


URL_PATTERN = re.compile(r'https?://(?:(?!https?://)[^\s,<>"\'])+')
USER_AGENT = "bridge2ai-data-sheets-schema/1.0"
PROJECT_ALIASES = {
    "AI-READI": "AI_READI",
    "AI_READI": "AI_READI",
    "CHORUS": "CHORUS",
    "CM4AI": "CM4AI",
    "VOICE": "VOICE",
}


def normalize_project_name(name: str) -> str:
    """Normalize spreadsheet column names to repository project names."""
    cleaned = name.strip()
    return PROJECT_ALIASES.get(cleaned, cleaned.replace("-", "_"))


def extract_urls(cell_value: str) -> List[str]:
    """Extract URLs, including URLs accidentally concatenated without whitespace."""
    urls = []
    for match in URL_PATTERN.finditer(cell_value or ""):
        url = match.group(0).rstrip(".,;:!?)")
        if url:
            urls.append(url)
    return urls


def validate_raw_artifact(path: Path, minimum_characters: int = 500) -> str:
    """Return an error message when a canonical raw artifact is unusable."""
    if not path.is_file():
        return "file is missing"
    content = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix == ".pdf" and not content.startswith(b"%PDF-"):
        return "payload does not have a PDF signature"
    if suffix in {".docx", ".xlsx"} and not content.startswith(b"PK"):
        return "payload does not have an Office ZIP signature"
    if suffix in {".txt", ".md"}:
        text = content.decode("utf-8", errors="ignore")
        if len(text.strip()) < minimum_characters:
            return (
                f"text has {len(text.strip())} characters; "
                f"minimum is {minimum_characters}"
            )
        if "doesn't work properly without javascript" in text.lower():
            return "text is a JavaScript application shell"
    if suffix == ".html":
        text = content.decode("utf-8", errors="ignore")
        if len(text.strip()) < 100:
            return "HTML payload is too short"
    if not content:
        return "file is empty"
    return ""


def promote_canonical_downloads(
    staging_dir: Path,
    output_dir: Path,
    manifest_path: Path,
    projects: List[str] = None,
) -> Dict:
    """Promote only manifest-selected files, retaining valid prior fallbacks."""
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest_projects = manifest.get("projects") if isinstance(manifest, dict) else None
    if not isinstance(manifest_projects, dict):
        raise ValueError(f"Invalid source manifest: {manifest_path}")

    selected_projects = set(projects or manifest_projects)
    unknown = selected_projects - set(manifest_projects)
    if unknown:
        raise ValueError(
            f"Projects not present in {manifest_path}: {sorted(unknown)}"
        )

    default_minimum = int(manifest.get("default_minimum_characters", 500))
    promoted_files = []
    retained_fallbacks = []
    unresolved_sources = []

    for project, entries in manifest_projects.items():
        if project not in selected_projects:
            continue
        for entry in entries:
            filename = entry["raw_file"]
            minimum = int(entry.get("minimum_characters", default_minimum))
            staged_path = staging_dir / project / filename
            active_path = output_dir / project / filename
            staged_error = validate_raw_artifact(staged_path, minimum)

            if not staged_error:
                active_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(staged_path, active_path)
                promoted_files.append(f"{project}/{filename}")
                continue

            active_error = validate_raw_artifact(active_path, minimum)
            if not active_error:
                retained_fallbacks.append({
                    "file": f"{project}/{filename}",
                    "reason": (
                        "current refresh did not produce a valid artifact: "
                        f"{staged_error}"
                    ),
                    "validation": "existing canonical artifact passed validation",
                })
                continue

            unresolved_sources.append({
                "file": f"{project}/{filename}",
                "staged_error": staged_error,
                "existing_error": active_error,
            })

    return {
        "manifest": str(manifest_path),
        "promoted_sources": len(promoted_files),
        "promoted_files": promoted_files,
        "retained_fallbacks": retained_fallbacks,
        "unresolved_sources": unresolved_sources,
    }


def rewrite_paths(value, source_dir: Path, destination_dir: Path):
    """Rewrite staging paths in nested extraction results."""
    if isinstance(value, dict):
        return {
            key: rewrite_paths(item, source_dir, destination_dir)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            rewrite_paths(item, source_dir, destination_dir)
            for item in value
        ]
    if isinstance(value, str):
        return value.replace(
            str(source_dir.resolve()),
            str(destination_dir.resolve()),
        )
    return value


class OrganizedDatasetExtractor:
    """Extract datasets and organize them by spreadsheet columns."""
    
    def __init__(self, output_dir: str = "organized_datasets"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
        })
        
    def process_spreadsheet(
        self,
        csv_path: str,
        projects: List[str] = None,
    ) -> Dict:
        """Process a CSV file maintaining column organization."""
        results = {
            'by_column': defaultdict(list),
            'summary': defaultdict(int),
            'errors': [],
            'duplicates_skipped': [],
            'crate_corpus_skipped': [],
        }
        selected_projects = {
            normalize_project_name(project) for project in (projects or [])
        }

        # Records claimed by the RO-Crate corpus are skipped here so the
        # with-crate and without-crate generation arms stay separable. See
        # data/ro-crate_packages/crate_manifest.yaml.
        exclusions = document_corpus_exclusions()
        if exclusions.dois or exclusions.urls:
            print(f"🔒 Crate-corpus exclusions active for: "
                  f"{sorted(set(exclusions.dois.values()) | set(exclusions.urls.values()))}")
        for project in exclusions.undecided:
            print(f"⚠️  {project} crate has no document_corpus decision yet; "
                  f"treating as allow. Set it in crate_manifest.yaml.")
        
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
                if not column:
                    continue
                project = normalize_project_name(column)
                if selected_projects and project not in selected_projects:
                    continue
                if cell_value:
                    for url in extract_urls(cell_value):
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
            safe_column = normalize_project_name(column)
            column_dir = self.output_dir / safe_column
            column_dir.mkdir(parents=True, exist_ok=True)
            seen_urls = set()
            
            print(f"\n📂 Column: {column}")
            print(f"   Directory: {safe_column}/")
            print(f"   URLs found: {len(url_list)}")
            
            # Process URLs in this column
            for url_info in url_list:
                url = url_info['url']
                row = url_info['row']
                url_key = url.rstrip("/")

                if url_key in seen_urls:
                    results['duplicates_skipped'].append({
                        'url': url,
                        'column': column,
                        'row': row,
                    })
                    print(f"\n   [Row {row}] Skipping duplicate: {url}")
                    continue
                seen_urls.add(url_key)

                claimed = exclusions.match(url)
                if claimed:
                    owner, reason = claimed
                    results['crate_corpus_skipped'].append({
                        'url': url,
                        'column': column,
                        'row': row,
                        'claimed_by': owner,
                        'reason': reason,
                    })
                    print(f"\n   [Row {row}] Skipping — claimed by the {owner} "
                          f"crate corpus: {url}")
                    continue

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
                            error_info = {
                                'url': url,
                                'column': column,
                                'row': row,
                                'error': file_info.get(
                                    'error',
                                    f"{file_info['type']} was not downloaded",
                                ),
                            }
                            results['errors'].append(error_info)
                            print(f"      ❌ Failed: {error_info['error']}")
                            
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

        parsed_path = urllib.parse.urlparse(url).path.lower()

        # Identify URL type
        if 'drive.google.com' in url or re.search(
            r'docs\.google\.com/(?:document|spreadsheets|presentation)/d/', url
        ):
            return self._download_google_drive(url, column_dir, row)
        elif 'reporter.nih.gov/project-details/' in url:
            return self._process_reporter(url, column_dir, row)
        elif 'biorxiv.org/content/' in url or 'medrxiv.org/content/' in url:
            return self._process_preprint(url, column_dir, row)
        elif parsed_path.endswith('.pdf'):
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

    def _download_google_drive(self, url: str, column_dir: Path, row: int) -> Dict:
        """Download a public Google Drive file or export a Workspace document."""
        info = {
            'type': 'Google Drive',
            'url': url,
            'row': row,
        }
        match = re.search(
            r'(?:drive\.google\.com/file/d/|'
            r'docs\.google\.com/(?:document|spreadsheets|presentation)/d/)'
            r'([a-zA-Z0-9_-]+)',
            url,
        )
        if not match:
            info['downloaded'] = False
            info['error'] = 'Could not extract Google Drive file ID'
            return info

        file_id = match.group(1)
        if 'docs.google.com/document' in url:
            download_url = (
                f'https://docs.google.com/document/d/{file_id}/export?format=docx'
            )
            extension = '.docx'
        elif 'docs.google.com/spreadsheets' in url:
            download_url = (
                f'https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx'
            )
            extension = '.xlsx'
        elif 'docs.google.com/presentation' in url:
            download_url = (
                f'https://docs.google.com/presentation/d/{file_id}/export/pdf'
            )
            extension = '.pdf'
        else:
            download_url = (
                f'https://drive.google.com/uc?export=download&id={file_id}'
            )
            extension = ''

        try:
            response = self.session.get(
                download_url,
                timeout=60,
                allow_redirects=True,
            )
            response.raise_for_status()
            content = response.content
            content_type = response.headers.get('content-type', '').lower()

            if b'<html' in content[:500].lower():
                raise ValueError(
                    'Google returned an HTML login or warning page instead of a file'
                )

            if not extension:
                if content.startswith(b'%PDF'):
                    extension = '.pdf'
                elif 'wordprocessingml' in content_type:
                    extension = '.docx'
                elif 'spreadsheetml' in content_type:
                    extension = '.xlsx'
                else:
                    extension = '.bin'

            filename = f'gdrive_{file_id}_row{row}{extension}'
            file_path = column_dir / filename
            with open(file_path, 'wb') as f:
                f.write(content)

            info.update({
                'filename': filename,
                'path': str(file_path),
                'size': len(content),
                'content_type': content_type,
                'downloaded': True,
            })
        except Exception as e:
            info['downloaded'] = False
            info['error'] = str(e)

        return info

    def _process_preprint(self, url: str, column_dir: Path, row: int) -> Dict:
        """Resolve a bioRxiv/medRxiv landing page to its full PDF."""
        info = {
            'type': 'PDF',
            'url': url,
            'row': row,
        }
        parsed = urllib.parse.urlparse(url)
        identifier = parsed.path.rstrip('/').split('/')[-1]
        if identifier.endswith('.full.pdf'):
            pdf_url = url
            identifier = identifier[:-len('.full.pdf')]
        else:
            pdf_url = url.rstrip('/') + '.full.pdf'

        try:
            response = self.session.get(
                pdf_url,
                headers={'Referer': f'{parsed.scheme}://{parsed.netloc}/'},
                timeout=60,
            )
            response.raise_for_status()
            if not response.content.startswith(b'%PDF'):
                raise ValueError('Preprint endpoint did not return a PDF')

            host_prefix = 'medrxiv' if 'medrxiv.org' in url else 'biorxiv'
            filename = f'{host_prefix}_{identifier}_row{row}.pdf'
            file_path = column_dir / filename
            with open(file_path, 'wb') as f:
                f.write(response.content)

            info.update({
                'resolved_url': pdf_url,
                'filename': filename,
                'path': str(file_path),
                'size': len(response.content),
                'downloaded': True,
            })
        except Exception as e:
            info['downloaded'] = False
            info['error'] = str(e)

        return info

    def _process_reporter(self, url: str, column_dir: Path, row: int) -> Dict:
        """Retrieve NIH project details through the RePORTER API."""
        info = {
            'type': 'NIH RePORTER Project',
            'url': url,
            'row': row,
        }
        match = re.search(r'project-details/(\d+)', url)
        if not match:
            info['downloaded'] = False
            info['error'] = 'Could not extract NIH RePORTER application ID'
            return info

        application_id = int(match.group(1))
        payload = {
            'criteria': {'appl_ids': [application_id]},
            'offset': 0,
            'limit': 1,
        }
        try:
            response = self.session.post(
                'https://api.reporter.nih.gov/v2/projects/search',
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            body = response.json()
            projects = body.get('results') or []
            if not projects:
                raise ValueError(
                    f'NIH RePORTER returned no project for application {application_id}'
                )

            project = projects[0]
            stem = (
                f'reporter_nih_gov_project-details-{application_id}_row{row}'
            )
            json_file = column_dir / f'{stem}.json'
            text_file = column_dir / f'{stem}.txt'
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'source_url': url,
                    'api_url': (
                        'https://api.reporter.nih.gov/v2/projects/search'
                    ),
                    'project': project,
                }, f, indent=2, ensure_ascii=False)

            organization = project.get('organization') or {}
            text_lines = [
                'NIH RePORTER Project',
                f'Source: {url}',
                f'Application ID: {project.get("appl_id", application_id)}',
                f'Project number: {project.get("project_num", "")}',
                f'Core project number: {project.get("core_project_num", "")}',
                f'Title: {project.get("project_title", "")}',
                f'Principal investigator: {project.get("contact_pi_name", "")}',
                f'Organization: {organization.get("org_name", "")}',
                f'Fiscal year: {project.get("fiscal_year", "")}',
                f'Award amount: {project.get("award_amount", "")}',
                f'Project start: {project.get("project_start_date", "")}',
                f'Project end: {project.get("project_end_date", "")}',
                '',
                project.get('abstract_text') or '',
                '',
                project.get('phr_text') or '',
                '',
                'Preferred terms:',
                project.get('pref_terms') or '',
            ]
            text = '\n'.join(text_lines).strip() + '\n'
            text_file.write_text(text, encoding='utf-8')

            info.update({
                'application_id': application_id,
                'filename': json_file.name,
                'text_file': text_file.name,
                'path': str(json_file),
                'text_size': len(text),
                'downloaded': True,
            })
        except Exception as e:
            info['downloaded'] = False
            info['error'] = str(e)

        return info
    
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
            if not response.content.startswith(b'%PDF-'):
                content_type = response.headers.get('content-type', 'unknown')
                raise ValueError(
                    "Expected a PDF payload, got "
                    f"{content_type} ({len(response.content)} bytes)"
                )
            
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
                    
            except Exception:
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
                        
                except Exception:
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
                    
                except Exception:
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

        dataset_id = info.get('dataset_id', 'unknown')

        # fairhub.io is a JavaScript application: the page is a ~1.3 KB shell and
        # the actual record lives behind /api/datasets/{id}, which returns ~133 KB
        # of structured metadata including the 84-question healthsheet. Saving an
        # API response through the HTML path would write the JSON body to a .html
        # file and leave the real artifact unreachable, so branch on it.
        if '/api/' in url:
            try:
                response = self.session.get(
                    url, timeout=30, headers={'Accept': 'application/json'})
                response.raise_for_status()
                json_file = column_dir / f'fairhub_api_dataset_{dataset_id}_row{row}.json'
                try:                       # re-dump so the artifact is canonical
                    payload = json.dumps(response.json(), indent=2, sort_keys=True)
                except ValueError:
                    payload = response.text
                json_file.write_text(payload, encoding='utf-8')
                info.update({
                    'type': 'FAIRhub API record',
                    'filename': json_file.name,
                    'path': str(json_file),
                    'size': len(payload),
                    'downloaded': True,
                })
            except Exception as e:
                info['error'] = str(e)
                info['downloaded'] = False
            return info

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            html_file = column_dir / (
                f'fairhub_dataset_{dataset_id}_row{row}.html'
            )
            html_file.write_text(response.text, encoding='utf-8')

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            for element in soup(['script', 'style', 'noscript']):
                element.decompose()
            text = '\n'.join(
                line.strip()
                for line in soup.get_text('\n').splitlines()
                if line.strip()
            )
            text_file = column_dir / (
                f'fairhub_dataset_{dataset_id}_row{row}.txt'
            )
            text_file.write_text(text, encoding='utf-8')

            metadata_file = column_dir / f"fairhub_row{row}.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2)

            info.update({
                'filename': html_file.name,
                'text_file': text_file.name,
                'path': str(html_file),
                'size': len(response.content),
                'text_size': len(text),
                'downloaded': True,
            })
        except Exception as e:
            info['downloaded'] = False
            info['error'] = str(e)
        
        return info
    
    def _process_doi(self, url: str, column_dir: Path, row: int) -> Dict:
        """Process DOI link."""
        info = {
            'type': 'DOI',
            'url': url,
            'row': row
        }
        
        # Extract DOI
        doi_match = re.search(r'doi\.org/(10\.\d{4,9}/.+)', url)
        if doi_match:
            info['doi'] = urllib.parse.unquote(doi_match.group(1))
        
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
                safe_column = normalize_project_name(column)
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

            if results.get('duplicates_skipped'):
                f.write("\n## Duplicate URLs Skipped\n\n")
                for duplicate in results['duplicates_skipped']:
                    f.write(
                        f"- {duplicate['column']} row {duplicate['row']}: "
                        f"{duplicate['url']}\n"
                    )
            
            # Errors section
            if results['errors']:
                f.write("\n## Errors\n\n")
                for error in results['errors']:
                    f.write(f"- Column: {error['column']}, Row: {error['row']}\n")
                    f.write(f"  - URL: {error['url']}\n")
                    f.write(f"  - Error: {error['error']}\n\n")

            promotion = results.get('canonical_promotion')
            if promotion:
                f.write("\n## Canonical Promotion\n\n")
                f.write(f"- Selection manifest: `{promotion['manifest']}`\n")
                f.write(
                    f"- Freshly promoted sources: "
                    f"{promotion['promoted_sources']}\n"
                )
                f.write(
                    f"- Retained validated fallbacks: "
                    f"{len(promotion['retained_fallbacks'])}\n"
                )
                f.write(
                    f"- Unresolved canonical sources: "
                    f"{len(promotion['unresolved_sources'])}\n"
                )
                for fallback in promotion['retained_fallbacks']:
                    f.write(
                        f"  - `{fallback['file']}` retained: "
                        f"{fallback['reason']}\n"
                    )

            anomalies = results.get('upstream_anomalies', [])
            if anomalies:
                f.write("\n## Upstream Anomalies\n\n")
                for anomaly in anomalies:
                    f.write(
                        f"- {anomaly.get('project', 'Unknown project')}: "
                        f"{anomaly.get('summary', anomaly.get('type', 'anomaly'))}\n"
                    )
        
        # Save JSON summary
        summary_file = self.output_dir / "organized_extraction_summary.json"
        summary = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'statistics': results['summary'],
                'by_column': results['by_column'],
                'errors': results['errors'],
                'duplicates_skipped': results.get('duplicates_skipped', []),
        }
        for key in ('canonical_promotion', 'upstream_anomalies'):
            if key in results:
                summary[key] = results[key]
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📄 Report saved: {report_file}")
        print(f"📊 Summary saved: {summary_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract and organize datasets by spreadsheet columns",
        epilog="Example: python organized_dataset_extractor.py 'https://docs.google.com/spreadsheets/d/.../export?format=csv' -o organized_data"
    )
    parser.add_argument("input", help="Google Sheets CSV export URL or local CSV file")
    parser.add_argument("-o", "--output", default="organized_datasets", help="Output directory")
    parser.add_argument(
        "--projects",
        nargs="+",
        choices=["AI_READI", "CHORUS", "CM4AI", "VOICE"],
        help="Only process the selected project columns",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help=(
            "Canonical source manifest. Downloads are staged and only selected "
            "artifacts are promoted to --output"
        ),
    )
    
    args = parser.parse_args()
    output_dir = Path(args.output)
    unresolved_sources = []

    if args.manifest:
        existing_anomalies = []
        existing_summary = output_dir / "organized_extraction_summary.json"
        if existing_summary.is_file():
            try:
                existing_anomalies = json.loads(
                    existing_summary.read_text(encoding="utf-8")
                ).get("upstream_anomalies", [])
            except (OSError, json.JSONDecodeError):
                pass

        with tempfile.TemporaryDirectory(
            prefix="b2ai-canonical-download-"
        ) as temporary_dir:
            staging_dir = Path(temporary_dir)
            staging_extractor = OrganizedDatasetExtractor(str(staging_dir))
            results = staging_extractor.process_spreadsheet(
                args.input,
                projects=args.projects,
            )
            promotion = promote_canonical_downloads(
                staging_dir,
                output_dir,
                args.manifest,
                projects=args.projects,
            )
            results = rewrite_paths(results, staging_dir, output_dir)
            results["canonical_promotion"] = promotion
            if existing_anomalies:
                results["upstream_anomalies"] = existing_anomalies
            unresolved_sources = promotion["unresolved_sources"]

        extractor = OrganizedDatasetExtractor(str(output_dir))
        extractor._save_organized_summary(results)
    else:
        extractor = OrganizedDatasetExtractor(str(output_dir))
        results = extractor.process_spreadsheet(
            args.input,
            projects=args.projects,
        )
    
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
        safe_column = normalize_project_name(column)
        print(f"   └── {safe_column}/")

    if unresolved_sources:
        print("\n❌ Canonical sources remain unresolved:")
        for source in unresolved_sources:
            print(f"   - {source['file']}: {source['staged_error']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
