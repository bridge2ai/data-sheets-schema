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


# A companion dataset's release in the corpus (#3283). OWN's only release
# record belongs to COMPANION by the scope declaration, as does one licence;
# the list form of in_bundle, an id the project lists no source for, and a
# second declaration naming the same source are all exercised.
SCOPED = b"""version: 1
projects:
  OWN:
    - id: landing
      source_type: documentation
      processed_file: landing.txt
    - id: companion_release
      source_type: data resource
      processed_file: companion_release.txt
      priority: 1
    - id: companion_terms
      source_type: license
      processed_file: companion_terms.txt
    - id: own_irb
      source_type: IRB
      processed_file: own_irb.txt
  COMPANION:
    - id: companion_release
      source_type: data resource
      processed_file: companion_release.txt
scope:
  OWN:
    referent_id: https://example.org/own
    related_but_distinct:
      - id: https://example.org/companion
        name: Companion dataset
        manifest_key: COMPANION
        in_bundle: [companion_release, companion_terms, not_a_source]
      - id: https://example.org/umbrella
        in_bundle: companion_release
  COMPANION:
    referent_id: https://example.org/companion
    related_but_distinct: []
"""


def test_voice_counts_only_its_own_releases_and_names_the_pediatric_one():
    inv = committed("VOICE")
    assert inv["instrument"] == ri.INSTRUMENT and "v2" in ri.INSTRUMENT
    assert inv["scope"] == {"status": "declared", "in_bundle_unmatched": [], "in_bundle_not_ids": [],
                            "skipped_entries": [], "self_referential_entries": []}
    own = [e["source_id"] for e in inv["release_records"]]
    assert "physionet_pediatric_1_1_0" not in own and "physionet_3_1_0" in own
    assert "physionet_pediatric_1_1_0" not in [e["source_id"] for e in inv["tier1"]]
    assert (inv["tier1_count"], inv["tier1_current_count"]) == (3, 2)   # was 4 (3 current) under v1
    [related] = inv["related_sources"]
    assert related["source_id"] == "physionet_pediatric_1_1_0"
    assert [d["manifest_key"] for d in related["related_datasets"]] == ["VOICE_PEDIATRIC"]
    # The pediatric project's own record of the same release stays its own.
    ped = committed("VOICE_PEDIATRIC")
    assert [e["source_id"] for e in ped["release_records"]] == ["physionet_pediatric_1_1_0"]
    assert ped["related_sources"] == []


def test_a_related_release_is_not_this_datasets_release_evidence():
    inv = ri.inventory(SCOPED, None, "OWN")
    assert inv["release_records"] == [] and inv["tier1"] == []
    assert inv["release_record_in_document_corpus"] is False
    assert inv["governance"]["license"] == []                      # the companion's licence too
    assert [e["source_id"] for e in inv["governance"]["IRB"]] == ["own_irb"]
    assert inv["sources"] == 4                                     # the corpus is unchanged
    moved = {e["source_id"]: e["related_datasets"] for e in inv["related_sources"]}
    assert set(moved) == {"companion_release", "companion_terms"}
    assert [d["id"] for d in moved["companion_release"]] == ["https://example.org/companion",
                                                            "https://example.org/umbrella"]
    assert inv["scope"] == {"status": "declared", "in_bundle_unmatched": ["not_a_source"],
                            "in_bundle_not_ids": [], "skipped_entries": [],
                            "self_referential_entries": []}
    assert ri.lacking_release_evidence([inv]) == ["OWN"]
    # The companion's own inventory counts the same source as its release.
    assert ri.inventory(SCOPED, None, "COMPANION")["release_record_in_document_corpus"] is True
    text = "\n".join(ri.render(inv))
    assert "companion_release (data resource): declared in_bundle for COMPANION, " \
           "https://example.org/umbrella, not counted above" in text
    assert "in_bundle names no source of this project: not_a_source" in text
    assert ri.render(inv)[-1].startswith("   crate in corpus")


# Every malformed shape that carries an ``in_bundle`` names ``promoted``, so
# "moves nothing" is tested against a declaration that would move it if it
# were read (#3449); the last case is the control that it does move when the
# declaration is usable.
@pytest.mark.parametrize("scope_yaml, status, moved", [
    (b"", "undeclared", False),
    (b"scope:\n  OTHER:\n    related_but_distinct: [{in_bundle: promoted}]\n",
     "undeclared", False),
    (b"scope:\n  EXTERNAL: [a, b]\n", "malformed", False),
    (b"scope:\n  EXTERNAL: [{related_but_distinct: [{in_bundle: promoted}]}]\n",
     "malformed", False),
    (b"scope:\n  EXTERNAL:\n    related_but_distinct: promoted\n", "malformed", False),
    (b"scope:\n  EXTERNAL:\n    related_but_distinct: {in_bundle: promoted}\n",
     "malformed", False),
    (b"scope:\n  EXTERNAL:\n    related_but_distinct: {x: {in_bundle: promoted}}\n",
     "malformed", False),
    (b"scope: [EXTERNAL]\n", "malformed", False),
    (b"scope:\n  EXTERNAL:\n    related_but_distinct:\n      - just-a-string\n",
     "declared", False),
    (b"scope:\n  EXTERNAL:\n    related_but_distinct:\n      - {id: x, in_bundle: promoted}\n",
     "declared", True),
])
def test_scope_shapes_are_statuses_and_move_nothing_unless_declared(scope_yaml, status, moved):
    inv = ri.inventory(NEUTRAL + scope_yaml, None, "EXTERNAL")
    assert inv["scope"]["status"] == status
    assert [e["source_id"] for e in inv["related_sources"]] == (["promoted"] if moved else [])
    assert [e["source_id"] for e in inv["tier1"]] == ([] if moved else ["promoted"])
    text = "\n".join(ri.render(inv))
    assert ("declaration is malformed; no source moved" in text) == (status == "malformed")


def test_scope_is_read_from_the_bytes_given():
    from data_sheets_schema import scope
    assert scope.scope_in(SCOPED, "OWN")["referent_id"] == "https://example.org/own"
    assert scope.scope_in(SCOPED.decode(), "MISSING") is None
    # As written: no strip, no cast to text (#3447); bools and None dropped;
    # nothing merged, so a repeat and 7.0 beside 7 are kept (#3507).
    assert scope.in_bundle_of({"in_bundle": ["a", " a ", True, None, 7, "a", 7.0]}) \
        == ["a", " a ", 7, "a", 7.0]
    assert [type(v) for v in scope.in_bundle_of({"in_bundle": [7, 7.0]})] == [int, float]
    assert scope.in_bundle_of({"in_bundle": "a"}) == ["a"] and scope.in_bundle_of("a") == []
    assert scope.in_bundle_of({"in_bundle": ""}) == [] and scope.in_bundle_of({"in_bundle": 0}) == []
    with pytest.raises(ValueError, match="not readable YAML"):
        scope.scope_in(b"scope: [unclosed\n", "OWN")


def test_cli_names_the_related_source(monkeypatch):
    monkeypatch.chdir(ROOT)
    r = CliRunner().invoke(release_inventory_cmd, ["--project", "VOICE"])
    assert r.exit_code == 0, r.output
    assert ("related source     physionet_pediatric_1_1_0 (data resource): "
            "declared in_bundle for VOICE_PEDIATRIC, not counted above") in r.output


# An in_bundle value check_manifest calls unmatched moves nothing here and is
# reported as unmatched (#3447): a padded string and a number that would
# match a source id only after normalising.
PADDED = NEUTRAL.replace(b"    - id: promoted", b"    - id: '7'\n      source_type: License\n"
                                                 b"      processed_file: seven.txt\n"
                                                 b"    - id: promoted") + b"""scope:
  EXTERNAL:
    referent_id: https://example.org/external
    related_but_distinct:
      - id: https://example.org/other
        in_bundle: [' promoted ', 7, promoted2]
"""


def test_in_bundle_matches_sources_exactly_as_check_manifest_does(tmp_path):
    from data_sheets_schema import scope
    inv = ri.inventory(PADDED, None, "EXTERNAL")
    assert inv["related_sources"] == []
    assert [e["source_id"] for e in inv["tier1"]] == ["promoted"]
    assert [e["source_id"] for e in inv["governance"]["license"]] == ["terms", "7"]
    assert inv["scope"] == {"status": "declared", "in_bundle_unmatched": [" promoted ", 7, "promoted2"],
                            "in_bundle_not_ids": [], "skipped_entries": [],
                            "self_referential_entries": []}
    assert "in_bundle names no source of this project: ' promoted ', 7, promoted2" \
        in "\n".join(ri.render(inv))
    manifest = tmp_path / "manifest_3423.yaml"
    manifest.write_bytes(PADDED)
    claimed = sorted(p["problem"] for p in scope.check_manifest(manifest)
                     if p["project"] == "EXTERNAL" and "claims source" in p["problem"])
    assert claimed == sorted(f"related dataset claims source {v!r} is in this bundle; the "
                             f"manifest lists no such source for EXTERNAL"
                             for v in inv["scope"]["in_bundle_unmatched"])


# A related dataset's id or manifest_key written as a number is kept (the
# scope reader admits bare accessions) and must render, not raise (#3446).
@pytest.mark.parametrize("entry, owner", [
    (b"{id: 12345, in_bundle: promoted}", "12345"),
    (b"{id: x2, manifest_key: 7, in_bundle: promoted}", "7"),
    # The number 0 is an identifier like any other, not an absent one (#3506).
    (b"{id: 0, in_bundle: promoted}", "0"),
    (b"{id: x2, manifest_key: 0, in_bundle: promoted}", "0"),
    (b"{id: 0, name: '', in_bundle: promoted}", "0"),
])
def test_a_numeric_related_dataset_id_renders(entry, owner):
    inv = ri.inventory(NEUTRAL + b"scope:\n  EXTERNAL:\n    related_but_distinct:\n      - "
                       + entry + b"\n", None, "EXTERNAL")
    assert inv["scope"]["skipped_entries"] == []
    [related] = inv["related_sources"]
    assert related["source_id"] == "promoted"
    text = "\n".join(ri.render(inv))
    assert f"declared in_bundle for {owner}, not counted above" in text
    assert "an unnamed dataset" not in text


# An entry scope.malformed_in skips -- no identifier at all, or one that is a
# list or a bool -- is skipped by every other reader and left out of the
# generation scope block, so its in_bundle must move nothing here either
# (#3477). The usable control beside it in the same declaration still moves
# its own source, and the skipped entry's unmatched id is still named, as
# check_manifest names it.
@pytest.mark.parametrize("entry", [
    b"{in_bundle: promoted}",
    b"{id: [a, b], in_bundle: promoted}",
    b"{id: true, in_bundle: promoted}",
    b"{name: Unnamed, in_bundle: [promoted, not_a_source_3477]}",
])
def test_an_entry_malformed_in_skips_moves_nothing(entry, tmp_path):
    from data_sheets_schema import scope
    raw = (NEUTRAL + b"scope:\n  EXTERNAL:\n    related_but_distinct:\n      - " + entry
           + b"\n      - {id: https://example.org/control, in_bundle: terms}\n")
    [row] = [r for r in scope.malformed_in(scope.scope_in(raw, "EXTERNAL")) if r["skipped"]]
    inv = ri.inventory(raw, None, "EXTERNAL")
    assert [e["source_id"] for e in inv["tier1"]] == ["promoted"]
    assert [e["source_id"] for e in inv["related_sources"]] == ["terms"]
    assert inv["scope"]["status"] == "declared"
    [skipped] = inv["scope"]["skipped_entries"]
    assert skipped["index"] == 0 and skipped["problem"] == row["problem"]
    assert "promoted" in skipped["in_bundle"]
    text = "\n".join(ri.render(inv))
    assert f"related_but_distinct[0]: {row['problem']}; its in_bundle moves nothing: promoted" in text
    assert "declared in_bundle for https://example.org/control, not counted above" in text
    assert "an unnamed dataset" not in text
    manifest = tmp_path / "manifest_3423_3477.yaml"
    manifest.write_bytes(raw)
    claimed = sorted(p["problem"] for p in scope.check_manifest(manifest)
                     if p["project"] == "EXTERNAL" and "claims source" in p["problem"])
    assert claimed == sorted(f"related dataset claims source {v!r} is in this bundle; the "
                             f"manifest lists no such source for EXTERNAL"
                             for v in inv["scope"]["in_bundle_unmatched"])


# An entry identified only by also_known_as is usable to every scope reader
# (scope.aliases_of gives its alias, so malformed_in does not skip it) and
# moves its source; its aliases are then the only identifier that says which
# dataset took the source, so the inventory records and renders them (#3494).
@pytest.mark.parametrize("entry, aliases, owner", [
    (b"{also_known_as: 'doi:10.1/x', in_bundle: promoted}", ["doi:10.1/x"],
     "a dataset also known as doi:10.1/x"),
    (b"{also_known_as: ['doi:10.1/x', ' ark:/1/y '], in_bundle: promoted}", ["doi:10.1/x", "ark:/1/y"],
     "a dataset also known as doi:10.1/x / ark:/1/y"),
    (b"{id: https://example.org/z, also_known_as: 'doi:10.1/z', in_bundle: promoted}", ["doi:10.1/z"],
     "https://example.org/z"),
])
def test_an_entry_named_only_by_its_aliases_records_them(entry, aliases, owner):
    from data_sheets_schema import scope
    raw = NEUTRAL + b"scope:\n  EXTERNAL:\n    related_but_distinct:\n      - " + entry + b"\n"
    assert not [r for r in scope.malformed_in(scope.scope_in(raw, "EXTERNAL")) if r["skipped"]]
    inv = ri.inventory(raw, None, "EXTERNAL")
    assert inv["scope"]["skipped_entries"] == []
    [related] = inv["related_sources"]
    [dataset] = related["related_datasets"]
    assert related["source_id"] == "promoted" and dataset["also_known_as"] == aliases
    text = "\n".join(ri.render(inv))
    assert f"declared in_bundle for {owner}, not counted above" in text
    assert "an unnamed dataset" not in text


# check_manifest reports every in_bundle value it cannot match, one problem
# each: a repeat, within an entry or across entries, and 7.0 beside 7 (equal
# to Python, written differently). The inventory's unmatched list is that
# finding item for item, and the render shows 7.0 as written (#3507). A
# matched source an entry names twice moves once for that entry.
REPEATED = NEUTRAL + b"""scope:
  EXTERNAL:
    related_but_distinct:
      - {id: a, in_bundle: [nope, 7, 7.0, promoted, promoted]}
      - {id: b, in_bundle: nope}
"""


def test_the_unmatched_list_is_check_manifests_finding_item_for_item(tmp_path):
    from data_sheets_schema import scope
    inv = ri.inventory(REPEATED, None, "EXTERNAL")
    unmatched = inv["scope"]["in_bundle_unmatched"]
    assert unmatched == ["nope", 7, 7.0, "nope"]
    assert [type(v) for v in unmatched] == [str, int, float, str]
    [related] = inv["related_sources"]
    assert related["source_id"] == "promoted"
    assert [d["id"] for d in related["related_datasets"]] == ["a"]
    assert "in_bundle names no source of this project: nope, 7, 7.0, nope" in "\n".join(ri.render(inv))
    manifest = tmp_path / "manifest_3423_3507.yaml"
    manifest.write_bytes(REPEATED)
    claimed = sorted(p["problem"] for p in scope.check_manifest(manifest)
                     if p["project"] == "EXTERNAL" and "claims source" in p["problem"])
    assert len(claimed) == 4
    assert claimed == sorted(f"related dataset claims source {v!r} is in this bundle; the "
                             f"manifest lists no such source for EXTERNAL" for v in unmatched)


# An in_bundle value that is not an identifier -- a bool, a nested list, a
# mapping -- names no source and moves nothing, but is not dropped silently:
# the inventory lists it, as written and with its entry's index, one item per
# "not a source id" problem check_manifest reports on the same bytes, on a
# usable entry and a skipped one alike, and the render names it (#3543). A
# falsy in_bundle is skipped by both.
@pytest.mark.parametrize("entries, not_ids, unmatched", [
    (b"      - {id: x, in_bundle: true}\n", [(0, True)], []),
    (b"      - {id: x, in_bundle: [[promoted], nope]}\n", [(0, ["promoted"])], ["nope"]),
    (b"      - {id: x, in_bundle: {promoted: 1}}\n", [(0, {"promoted": 1})], []),
    (b"      - {id: x, in_bundle: [terms, null, false]}\n      - {name: N, in_bundle: [true]}\n",
     [(0, None), (0, False), (1, True)], []),
    # A falsy in_bundle names nothing and check_manifest skips it: not listed.
    (b"      - {id: x, in_bundle: false}\n      - {id: y, in_bundle: []}\n", [], []),
])
def test_an_in_bundle_value_that_is_not_an_id_is_listed(entries, not_ids, unmatched, tmp_path):
    from data_sheets_schema import scope
    raw = NEUTRAL + b"scope:\n  EXTERNAL:\n    related_but_distinct:\n" + entries
    inv = ri.inventory(raw, None, "EXTERNAL")
    assert inv["scope"]["status"] == "declared"
    assert [e["source_id"] for e in inv["tier1"]] == ["promoted"]
    assert [(r["index"], r["value"]) for r in inv["scope"]["in_bundle_not_ids"]] == not_ids
    assert inv["scope"]["in_bundle_unmatched"] == unmatched
    text = "\n".join(ri.render(inv))
    for index, value in not_ids:
        assert (f"related_but_distinct[{index}]: in_bundle carries {value!r}, "
                f"not a source id; it moves nothing") in text
    manifest = tmp_path / "manifest_3423_3543.yaml"
    manifest.write_bytes(raw)
    carried = sorted(p["problem"] for p in scope.check_manifest(manifest)
                     if p["project"] == "EXTERNAL" and "not a source id" in p["problem"])
    assert carried == sorted(f"related dataset's in_bundle carries a {type(v).__name__}, "
                             f"not a source id" for _, v in not_ids)


# YAML can write values in in_bundle that JSON cannot carry -- a date, bytes
# (!!binary), a set, a mapping with a key that is not a string. Each is still
# "not a source id" to check_manifest and moves nothing; the inventory keeps
# it in a JSON-safe form with the loaded type, so to_json and the CLI's --json
# write it instead of raising (#3580), and the same bytes give the same text.
@pytest.mark.parametrize("value, kind, safe", [
    (b"2026-09-01", "date", {"!!timestamp": "2026-09-01"}),
    (b"2026-09-01 10:20:30", "datetime", {"!!timestamp": "2026-09-01T10:20:30"}),
    (b"!!binary aGk=", "bytes", {"!!binary": "aGk="}),
    (b"!!set {zeta: null, alpha: null, mid: null}", "set", {"!!set": ["alpha", "mid", "zeta"]}),
    (b"{1: a, b: 2026-09-01}", "dict", {"!!map": [[1, "a"], ["b", {"!!timestamp": "2026-09-01"}]]}),
    (b"[promoted, !!binary aGk=]", "list", ["promoted", {"!!binary": "aGk="}]),
])
def test_a_rejected_yaml_value_is_written_as_json(value, kind, safe, tmp_path, monkeypatch):
    from data_sheets_schema import scope
    raw = (NEUTRAL + b"scope:\n  EXTERNAL:\n    related_but_distinct:\n"
           b"      - id: x\n        in_bundle: [release, " + value + b"]\n")
    inv = ri.inventory(raw, None, "EXTERNAL")
    assert [e["source_id"] for e in inv["tier1"]] == ["promoted"]
    assert inv["related_sources"] == []
    [row] = inv["scope"]["in_bundle_not_ids"]
    assert row == {"index": 0, "type": kind, "value": safe}
    assert inv["scope"]["in_bundle_unmatched"] == ["release"]
    written = ri.to_json([inv])
    assert json.loads(written)[0]["scope"]["in_bundle_not_ids"] == [row]
    assert written == ri.to_json([ri.inventory(raw.decode(), None, "EXTERNAL")])
    text = "\n".join(ri.render(inv))
    shown = repr(safe) if kind in ("list", "dict") else f"a {kind} {json.dumps(safe, sort_keys=True)}"
    assert f"related_but_distinct[0]: in_bundle carries {shown}, not a source id" in text
    manifest = tmp_path / "manifest_3423_3580.yaml"
    manifest.write_bytes(raw)
    carried = [p["problem"] for p in scope.check_manifest(manifest)
               if p["project"] == "EXTERNAL" and "not a source id" in p["problem"]]
    assert carried == [f"related dataset's in_bundle carries a {kind}, not a source id"]
    monkeypatch.chdir(ROOT)
    r = CliRunner().invoke(release_inventory_cmd, ["--manifest", str(manifest), "--project",
                                                   "EXTERNAL", "--json"])
    assert r.exit_code == 0, r.output
    assert r.output == written


def test_a_set_is_written_in_one_order_whatever_the_hash_seed():
    import subprocess
    import sys
    code = ("from data_sheets_schema import release_inventory as ri; import sys; "
            "raw = sys.stdin.buffer.read(); "
            "print(ri.to_json([ri.inventory(raw, None, 'EXTERNAL')]), end=''); "
            "print('\\n'.join(ri.render(ri.inventory(raw, None, 'EXTERNAL'))))")
    raw = (NEUTRAL + b"scope:\n  EXTERNAL:\n    related_but_distinct:\n      - id: x\n"
           b"        in_bundle: [!!set {" + b", ".join(b"s%d: null" % i for i in range(40)) + b"}]\n")
    outs = {subprocess.run([sys.executable, "-c", code], input=raw, capture_output=True, check=True,
                           env={**os.environ, "PYTHONHASHSEED": seed}).stdout
            for seed in ("1", "2", "3", "4")}
    assert len(outs) == 1


# An entry that names this dataset itself contradicts the declaration it sits
# in (check_manifest: "the referent is also listed as related-but-distinct").
# Its in_bundle must not take the project's own release record out of its
# counts: it moves nothing, is listed with what it matched on, and the
# project is not reported as lacking release evidence (#3581). The match is
# on the id or an alias in any spelling scope._norm equates, or on a
# manifest_key naming this project; a control entry beside it still moves.
SELF = b"""version: 1
projects:
  OWN:
    - id: own_release
      source_type: data resource
      processed_file: own_release.txt
      priority: 1
    - id: other_release
      source_type: RO-Crate
      processed_file: other_release.txt
scope:
  OWN:
    referent_id: https://doi.org/10.1234/OWN
    related_but_distinct:
      - ENTRY
      - {id: https://example.org/other, manifest_key: OTHER, in_bundle: other_release}
"""


@pytest.mark.parametrize("entry, matched", [
    (b"{id: https://doi.org/10.1234/OWN, manifest_key: OWNX, in_bundle: own_release}",
     [{"field": "id / also_known_as", "value": "https://doi.org/10.1234/OWN",
       "referent_id": "https://doi.org/10.1234/OWN"}]),
    (b"{id: https://example.org/elsewhere, also_known_as: 'doi:10.1234/own', in_bundle: [own_release]}",
     [{"field": "id / also_known_as", "value": "doi:10.1234/own", "referent_id": "https://doi.org/10.1234/OWN"}]),
    (b"{also_known_as: '10.1234/OWN/', in_bundle: own_release}",
     [{"field": "id / also_known_as", "value": "10.1234/OWN/", "referent_id": "https://doi.org/10.1234/OWN"}]),
    (b"{id: https://example.org/elsewhere, manifest_key: OWN, in_bundle: own_release}",
     [{"field": "manifest_key", "value": "OWN"}]),
])
def test_an_entry_naming_this_dataset_itself_moves_nothing(entry, matched, tmp_path):
    from data_sheets_schema import scope
    raw = SELF.replace(b"ENTRY", entry)
    inv = ri.inventory(raw, None, "OWN")
    assert [e["source_id"] for e in inv["release_records"]] == ["own_release"]
    assert [e["source_id"] for e in inv["tier1"]] == ["own_release"]
    assert [e["source_id"] for e in inv["related_sources"]] == ["other_release"]
    assert ri.lacking_release_evidence([inv]) == []
    assert inv["scope"]["status"] == "declared" and inv["scope"]["skipped_entries"] == []
    assert inv["scope"]["self_referential_entries"] == [
        {"index": 0, "matched_on": matched, "in_bundle": ["own_release"]}]
    text = "\n".join(ri.render(inv))
    assert "release record     yes: own_release" in text
    assert "related_but_distinct[0]: names this dataset itself (" in text
    assert "; its in_bundle moves nothing: own_release" in text
    assert "declared in_bundle for OTHER, not counted above" in text
    json.loads(ri.to_json([inv]))
    if entry.startswith(b"{id: https://doi.org/10.1234/OWN,"):
        # The exact-id case is the one check_manifest itself reports.
        manifest = tmp_path / "manifest_3423_3581.yaml"
        manifest.write_bytes(raw)
        assert any(p["problem"] == "the referent is also listed as related-but-distinct"
                   for p in scope.check_manifest(manifest) if p["project"] == "OWN")


def test_the_committed_manifest_has_no_self_referential_entry():
    for project in ("AI_READI", "CHORUS", "CM4AI", "VOICE", "VOICE_PEDIATRIC"):
        assert committed(project)["scope"]["self_referential_entries"] == []
