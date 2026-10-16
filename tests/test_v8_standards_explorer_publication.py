"""Preserve historical v8 facts and publication identity (#5055, #5056)."""

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.adhoc.render_v8_standards_explorer import (
    CSS,
    PublicationRenderer,
    verify_values,
)


def test_recursive_display_preserves_mixed_lists_false_null_and_markup():
    renderer = object.__new__(PublicationRenderer)
    data = {
        "funders": [{"grantor": "NIH", "grants": [{"grant_number": "OT2-123"}], "source_caveats": "Keep <id> & caveats"}],
        "creators": [{"name": "Consortium", "notes": "All fields stay"}],
        "mixed": [{"id": "first"}, {"id": "second"}, {"id": "third"}, "fourth"],
        "values": [False, True, None, 0, "", "false", "null"],
        "<script>": '<img src=x onerror="alert(1)">',
    }
    output = renderer.format_value(data)
    verify_values(data, output)
    assert "<script>" not in output
    assert "<img" not in output
    assert "Keep &lt;id&gt; &amp; caveats" in output
    assert "Grant Number" in output
    assert "Source Caveats" in output
    with pytest.raises(ValueError, match="HTML changed source values"):
        verify_values(data, output.replace("OT2-123", "OT2-999"))


def test_url_attribute_is_escaped():
    renderer = object.__new__(PublicationRenderer)
    value = 'https://example.org/"onmouseover="alert(1)'
    output = renderer.format_value(value)
    assert 'href="https://example.org/&quot;onmouseover=&quot;alert(1)"' in output
    verify_values(value, output)


@pytest.mark.corpus
def test_published_bundle_matches_historical_sources_and_all_scalar_values():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "src/html/output/v8-publication.json").read_text())
    expected = {"AI_READI": "04g", "CM4AI": "04g", "CHORUS": "04f", "VOICE": "04f"}
    assert len(manifest["records"]) == 4
    assert {r["project"] for r in manifest["records"]} == set(expected)
    for record in manifest["records"]:
        source = (root / record["source"]).read_bytes()
        provenance = (root / record["provenance"]).read_bytes()
        output = (root / record["html"]).read_bytes()
        assert hashlib.sha256(source).hexdigest() == record["source_sha256"]
        assert hashlib.sha256(provenance).hexdigest() == record["provenance_sha256"]
        assert hashlib.sha256(output).hexdigest() == record["html_sha256"]
        assert record["run_label"] == f'2026-09-{expected[record["project"]]}_claude-opus-5-api-generic-v8_rep1'
        assert record["replicate"] == 1
        html = output.decode("utf-8")
        assert verify_values(yaml.safe_load(source), html) == record["source_scalar_count"]
        assert "Historical v8 datasheet · Replicate 1 · Generation schema 2.0.0" in html
        assert "HTML rendered on 2026-10-16" in html
        assert "<style>\n" + CSS + "</style>" in html
        assert '<div class="d4d-v8">' in html
        assert 'rel="stylesheet"' not in html  # Embedded portal has no relative CSS asset.
        assert f'/blob/{manifest["source_commit"]}/{record["source"]}' in html
    css = (root / manifest["css"]["path"]).read_bytes()
    assert hashlib.sha256(css).hexdigest() == manifest["css"]["sha256"]
    assert css.decode() == CSS


@pytest.mark.corpus
def test_voice_placeholders_and_aireadi_grants_survive_publication():
    output = Path(__file__).resolve().parents[1] / "src/html/output"
    voice = (output / "D4D_-_VOICE_v8_human_readable.html").read_text()
    assert "sub-&lt;id&gt;/ses-&lt;id&gt;/audio" in voice
    ai_readi = (output / "D4D_-_AI-READI_v8_human_readable.html").read_text()
    assert "OT2OD032644" in ai_readi
    assert "Source Caveats" in ai_readi
