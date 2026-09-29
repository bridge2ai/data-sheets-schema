"""Release-level corpus inventory (#2914): what each document corpus can say
about the release, read from the manifests' bytes alone."""
import builtins
import io
import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from data_sheets_schema import release_inventory as ri
from data_sheets_schema.cli.download import release_inventory_cmd

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (ROOT / "data/preprocessed/source_manifest.yaml").read_bytes()
CRATES = (ROOT / "data/ro-crate_packages/crate_manifest.yaml").read_bytes()

NEUTRAL = b"""version: 1
projects:
  EXTERNAL:
    - id: landing
      source_type: documentation
      processed_file: landing.txt
    - id: terms
      source_type: License
      processed_file: terms.txt
    - id: promoted
      source_type: documentation
      processed_file: promoted.txt
      priority: 1
  BARE:
    sources:
      - id: page
        source_type: tutorial
        processed_file: page.txt
  AGREEMENT:
    - id: dua
      source_type: dua
      processed_file: dua.txt
  ETHICS:
    - id: irb
      source_type: irb
      processed_file: irb.txt
"""


def committed(project):
    return ri.inventory(MANIFEST, CRATES, project)


def test_chorus_has_no_release_level_source_and_its_crate_is_excluded():
    inv = committed("CHORUS")
    assert inv["sources"] == 4
    assert inv["tier1_count"] == 0 and inv["tier1"] == []
    assert inv["governance"] == {"license": [], "DUA": [], "IRB": []}
    assert inv["release_record_in_document_corpus"] is False
    assert inv["crate_in_document_corpus"] is False
    assert inv["crate_policy"]["status"] == "declared"
    assert inv["crate_policy"]["document_corpus"] == "exclude"


def test_ai_readi_carries_its_crate_and_licence_in_the_document_corpus():
    inv = committed("AI_READI")
    assert inv["crate_in_document_corpus"] is True
    assert [e["source_id"] for e in inv["governance"]["license"]] == ["dataset_license"]
    assert [e["source_id"] for e in inv["governance"]["IRB"]] == ["irb_protocol"]
    assert "ro_crate_metadata" in [e["source_id"] for e in inv["tier1"]]
    assert inv["crate_policy"]["document_corpus"] == "allow"


@pytest.mark.parametrize("project, current", [("CM4AI", "june_2026_dataverse_release"),
                                              ("VOICE", "physionet_3_1_0")])
def test_cm4ai_and_voice_have_a_current_tier1_data_resource(project, current):
    inv = committed(project)
    tier1 = {e["source_id"]: e for e in inv["tier1"]}
    assert tier1[current]["source_type"] == "data resource"
    assert tier1[current]["superseded"] is False
    assert inv["tier1_current_count"] < inv["tier1_count"]      # each keeps a superseded release
    assert inv["release_record_in_document_corpus"] is True
    assert inv["crate_in_document_corpus"] is False
    assert inv["crate_policy"]["document_corpus"] == "allow"


def test_voice_dua_and_the_projects_lacking_release_evidence():
    assert [e["source_id"] for e in committed("VOICE")["governance"]["DUA"]] == ["data_transfer_use_agreement"]
    invs = [committed(p) for p in ("AI_READI", "CHORUS", "CM4AI", "VOICE")]
    assert ri.lacking_release_evidence(invs) == ["CHORUS"]


def test_a_project_the_crate_manifest_does_not_name_is_reported():
    inv = committed("VOICE_PEDIATRIC")
    assert inv["crate_policy"]["status"] == "no_entry"
    assert "no crate-manifest entry" in ri.render(inv)[-1]


def test_neutral_manifest_without_a_crate_manifest():
    inv = ri.inventory(NEUTRAL, None, "EXTERNAL")
    # No source_priority table: nothing is tier 1 unless a source says so.
    assert [e["source_id"] for e in inv["tier1"]] == ["promoted"]
    # A priority override does not make a documentation page a release record.
    assert inv["release_record_in_document_corpus"] is False
    # Types match case-insensitively; the source keeps its own spelling.
    assert inv["governance"]["license"] == [{"source_id": "terms", "source_type": "License",
                                             "effective_priority": 99, "superseded": False}]
    assert inv["crate_policy"] == {"status": "not_supplied", "document_corpus": None,
                                   "crate_manifest_sha256": None}
    assert ri.inventory(NEUTRAL, None, "BARE")["sources"] == 1       # mapping-form project record


@pytest.mark.parametrize("crates, status", [
    (b"projects:\n  OTHER:\n    document_corpus: exclude\n", "no_entry"),
    (b"projects:\n  EXTERNAL:\n    doi: 10.1/x\n", "undeclared"),
    (b"projects:\n  EXTERNAL: exclude\n", "malformed_entry"),
    (b"version: 1\n", "no_projects"),
    (b"", "no_projects"),
])
def test_missing_crate_declarations_are_statuses_not_errors(crates, status):
    inv = ri.inventory(NEUTRAL, crates, "EXTERNAL")
    assert inv["crate_policy"]["status"] == status
    assert inv["crate_policy"]["document_corpus"] is None
    ri.render(inv)


def test_unreadable_crate_manifest_and_undeclared_project_raise_valueerror():
    with pytest.raises(ValueError, match="crate manifest"):
        ri.inventory(NEUTRAL, b"projects: [unclosed\n", "EXTERNAL")
    with pytest.raises(ValueError, match="not declared"):
        ri.inventory(NEUTRAL, None, "CHORUS")


def test_pure_and_byte_identical(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("release_inventory must not open files")
    # Every route to a file descriptor, not only the builtin: pathlib's
    # Path.open calls io.open directly and never looks up builtins.open
    # (#3294), and os.open is the level both sit on.
    monkeypatch.setattr(builtins, "open", refuse)
    monkeypatch.setattr(io, "open", refuse)
    monkeypatch.setattr(os, "open", refuse)
    monkeypatch.setattr(Path, "open", refuse)
    monkeypatch.setattr(Path, "read_bytes", refuse)
    monkeypatch.setattr(Path, "read_text", refuse)
    first = ri.to_json([committed(p) for p in ("AI_READI", "CHORUS", "CM4AI", "VOICE")])
    second = ri.to_json([ri.inventory(MANIFEST.decode(), CRATES.decode(), p)
                         for p in ("AI_READI", "CHORUS", "CM4AI", "VOICE")])
    assert first == second
    assert json.loads(first)[1]["source_manifest_sha256"] == json.loads(first)[0]["source_manifest_sha256"]


def test_cli_on_the_study_manifests(monkeypatch):
    monkeypatch.chdir(ROOT)
    r = CliRunner().invoke(release_inventory_cmd, [])
    assert r.exit_code == 0, r.output
    assert "(study default)" in r.output
    assert "crate policy: document_corpus: exclude" in r.output
    assert "no licence/DUA source in the document corpus: CHORUS " in r.output
    j = CliRunner().invoke(release_inventory_cmd, ["--json", "--project", "CHORUS"])
    assert j.exit_code == 0, j.output
    assert j.output == ri.to_json([committed("CHORUS")])


def test_cli_does_not_apply_the_study_crate_manifest_to_another_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    m = tmp_path / "manifest.yaml"
    m.write_bytes(NEUTRAL)
    r = CliRunner().invoke(release_inventory_cmd, ["--manifest", str(m)])
    assert r.exit_code == 0, r.output
    assert "not the study default" in r.output
    assert "no crate manifest supplied" in r.output
    assert "EXTERNAL" in r.output and "BARE" in r.output


def test_a_licence_source_alone_is_release_level_evidence():
    # EXTERNAL has no release record but a licence source; BARE has neither.
    invs = [ri.inventory(NEUTRAL, None, p) for p in ("EXTERNAL", "BARE")]
    assert ri.lacking_release_evidence(invs) == ["BARE"]


def test_a_dua_source_alone_is_release_level_evidence_and_an_irb_alone_is_not():
    # A DUA states the terms a dataset is released under; an IRB protocol
    # does not (#3295). Neither project has a release record or a licence.
    invs = [ri.inventory(NEUTRAL, None, p) for p in ("AGREEMENT", "ETHICS")]
    assert [e["source_id"] for e in invs[0]["governance"]["DUA"]] == ["dua"]
    assert [e["source_id"] for e in invs[1]["governance"]["IRB"]] == ["irb"]
    assert ri.lacking_release_evidence(invs) == ["ETHICS"]


@pytest.mark.parametrize("declared", ["Exclude", " EXCLUDE ", "exclude"])
def test_the_crate_policy_is_case_folded_as_rocrate_normalize_folds_it(declared):
    # rocrate_normalize lower-cases document_corpus before deciding (#3297).
    crates = f"projects:\n  EXTERNAL:\n    document_corpus: '{declared}'\n".encode()
    assert ri.inventory(NEUTRAL, crates, "EXTERNAL")["crate_policy"]["document_corpus"] == "exclude"


@pytest.mark.parametrize("spelling", ["absolute", "dotdot", "symlink"])
def test_cli_treats_any_spelling_of_the_study_manifest_as_the_study_default(spelling, tmp_path, monkeypatch):
    # The study default is a file, not a spelling (#3293/#3296).
    monkeypatch.chdir(ROOT)
    default = ROOT / "data/preprocessed/source_manifest.yaml"
    if spelling == "absolute":
        m = str(default)
    elif spelling == "dotdot":
        m = "data/preprocessed/../preprocessed/source_manifest.yaml"
    else:
        link = tmp_path / "linked_manifest.yaml"
        link.symlink_to(default)
        m = str(link)
    r = CliRunner().invoke(release_inventory_cmd, ["--manifest", m, "--project", "CHORUS"])
    assert r.exit_code == 0, r.output
    assert "(study default)" in r.output
    assert "crate policy: document_corpus: exclude" in r.output
    assert "not the study default" not in r.output
