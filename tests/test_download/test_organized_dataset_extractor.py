#!/usr/bin/env python3
"""Tests for canonical source discovery and specialized download handlers."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from src.download.organized_dataset_extractor import (
    OrganizedDatasetExtractor,
    extract_urls,
    normalize_project_name,
    promote_canonical_downloads,
)


class TestOrganizedDatasetExtractor(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.tempdir.name)
        self.extractor = OrganizedDatasetExtractor(str(self.output_dir))

    def tearDown(self):
        self.tempdir.cleanup()

    def test_extract_urls_splits_concatenated_urls(self):
        value = (
            "https://aireadi.org/publications"
            "https://doi.org/10.1038/s42255-024-01165-x"
            "https://doi.org/10.1136/bmjopen-2024-097449"
        )
        self.assertEqual(
            extract_urls(value),
            [
                "https://aireadi.org/publications",
                "https://doi.org/10.1038/s42255-024-01165-x",
                "https://doi.org/10.1136/bmjopen-2024-097449",
            ],
        )

    def test_project_name_normalization(self):
        self.assertEqual(normalize_project_name("AI-READI"), "AI_READI")
        self.assertEqual(normalize_project_name("VOICE"), "VOICE")

    def test_process_spreadsheet_deduplicates_urls_per_project(self):
        csv_file = self.output_dir / "sources.csv"
        csv_file.write_text(
            ",AI-READI,VOICE\n"
            "documentation,https://example.org/docs,https://example.org/voice\n"
            "duplicate,https://example.org/docs,\n",
            encoding="utf-8",
        )
        self.extractor._process_url = Mock(return_value={
            "type": "Web Page",
            "downloaded": True,
            "filename": "source.html",
        })

        results = self.extractor.process_spreadsheet(
            str(csv_file),
            projects=["AI_READI"],
        )

        self.assertEqual(self.extractor._process_url.call_count, 1)
        self.assertEqual(len(results["duplicates_skipped"]), 1)
        self.assertEqual(list(results["by_column"]), ["AI-READI"])

    def test_process_spreadsheet_reports_handler_failure(self):
        csv_file = self.output_dir / "sources.csv"
        csv_file.write_text(
            "AI-READI\nhttps://example.org/document.pdf\n",
            encoding="utf-8",
        )
        self.extractor._process_url = Mock(return_value={
            "type": "PDF",
            "downloaded": False,
            "error": "Expected a PDF payload",
        })

        results = self.extractor.process_spreadsheet(str(csv_file))

        self.assertEqual(len(results["errors"]), 1)
        self.assertEqual(results["errors"][0]["error"], "Expected a PDF payload")

    def test_download_pdf_rejects_html_payload(self):
        response = Mock()
        response.content = b"<html>download denied</html>"
        response.headers = {"content-type": "text/html"}
        response.raise_for_status.return_value = None
        self.extractor.session.get = Mock(return_value=response)

        result = self.extractor._download_pdf(
            "https://example.org/document.pdf",
            self.output_dir,
            2,
        )

        self.assertFalse(result["downloaded"])
        self.assertIn("Expected a PDF payload", result["error"])
        self.assertFalse((self.output_dir / "document_row2.pdf").exists())

    def test_manifest_promotion_uses_valid_existing_fallback(self):
        staging = self.output_dir / "staging"
        active = self.output_dir / "active"
        (staging / "AI_READI").mkdir(parents=True)
        (active / "AI_READI").mkdir(parents=True)
        (staging / "AI_READI" / "fresh.txt").write_text("fresh " * 100)
        (active / "AI_READI" / "fallback.pdf").write_bytes(
            b"%PDF-1.4\nexisting"
        )
        manifest = self.output_dir / "manifest.yaml"
        manifest.write_text(
            """
version: 1
default_minimum_characters: 100
projects:
  AI_READI:
    - id: fresh
      raw_file: fresh.txt
      processed_file: fresh.txt
    - id: fallback
      raw_file: fallback.pdf
      processed_file: fallback.txt
""".strip()
        )

        result = promote_canonical_downloads(
            staging,
            active,
            manifest,
        )

        self.assertEqual(result["promoted_sources"], 1)
        self.assertEqual(len(result["retained_fallbacks"]), 1)
        self.assertEqual(result["unresolved_sources"], [])
        self.assertEqual(
            (active / "AI_READI" / "fresh.txt").read_text(),
            "fresh " * 100,
        )

    def test_reporter_handler_writes_structured_json_and_text(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "results": [{
                "appl_id": 10471118,
                "project_num": "1OT2OD032644-01",
                "core_project_num": "OT2OD032644",
                "project_title": "Bridge2AI Test Project",
                "contact_pi_name": "TEST, PERSON",
                "organization": {"org_name": "Test University"},
                "fiscal_year": 2022,
                "award_amount": 1000,
                "abstract_text": "A" * 700,
                "phr_text": "Public health relevance",
                "pref_terms": "artificial intelligence",
            }]
        }
        self.extractor.session.post = Mock(return_value=response)

        result = self.extractor._process_reporter(
            "https://reporter.nih.gov/project-details/10471118",
            self.output_dir,
            7,
        )

        self.assertTrue(result["downloaded"])
        text_path = self.output_dir / result["text_file"]
        json_path = self.output_dir / result["filename"]
        self.assertIn("Bridge2AI Test Project", text_path.read_text())
        self.assertEqual(
            json.loads(json_path.read_text())["project"]["appl_id"],
            10471118,
        )


if __name__ == "__main__":
    unittest.main()
