"""Run-bound review-pack aliases, mixed schema bases, and immutable write guards (#4291)."""
import copy
import gzip
import hashlib
import importlib
import json
import subprocess
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import review_pack as rp, receipts as rc, run_schema as rs
from tests.test_review_pack import Pack

DOI = (("https://doi.org/", "doi"),)
TEXT = "Original neutral account documented thoroughly."
REPLACED = "Entirely replacement text for another entry."
SLOT = "file_collections[0].description"

def legacy_helpers(module, **kwargs):
    values = ['https://doi.org/10.9999/Case', 'HTTPS://EXAMPLE.org/Path/A', 'https://example.org/path/a',
              'ORCID:0000-0001-2345-6789', 'doi:10.9999/Case', '  urn:neutral:thing  ', 'Plain Name']
    origins = [(v, rid) for v in ['#x', 'https://example.org/#', 'urn:neutral:x',
        'https://doi.org/10.9999/Case#part', 'doi:10.9999/Case#part', 'https://example.org/path#part', None, ['id']]
        for rid in ['doi:10.9999/Case', 'https://doi.org/10.9999/Case', 'https://example.org/Path', None]]
    presences = [('doi:10.9999/Case', 'see https://doi.org/10.9999/Case today'),
                 ('https://doi.org/10.9999/Case', 'see doi:10.9999/Case today'),
                 ('https://example.org/3', 'https://example.org/30'),
                 ('https://example.org/3', 'https://example.org/3/access'),
                 ('https://example.org/3', '(https://example.org/3).'),
                 ('https://example.org/3', 'https://example.org/3/'),
                 ('https://example.org/v', 'https://example.org/v.1/x'),
                 ('https://example.org/v', 'https://example.org/v-2'),
                 ('https://example.org/v', 'https://example.org/v.\nNext')]
    full = {'id':'doi:10.9999/Case', 'file_collections':[
        {'id':'https://doi.org/10.9999/Case#part'}, {'id':'https://doi.org/10.9999/other#part'}],
        'creators':[{'id':'urn:neutral:person'}], 'nonsuch':[{'id':'x#part'}]}
    return {'canonical':[module._canonical_identifier(v, **kwargs) for v in values],
            'origins':[module._id_origin(v, rid, **kwargs) for v,rid in origins],
            'presence':[module._base_in(v, text, **kwargs) for v,text in presences],
            'slots':module._id_slots(full, bundle_text='Source: doi:10.9999/other', **kwargs),
            'unknown_root':module._id_slots(full, root_class='Unknown', **kwargs)}


def test_complete_legacy_helper_output_and_explicit_none_bytes():
    # Captured before editing from bfdcffd822b8, including whole id-slot flags.
    output = legacy_helpers(rp)
    assert hashlib.sha256(json.dumps(output, sort_keys=True).encode()).hexdigest() == "378af3c341f965001f5b4b1e29aa2190ea8fe5ce2edcd4f419d9182b909fc78d"
    assert legacy_helpers(rp, identifier_bases=None) == output


@pytest.mark.parametrize("bad", [False, "", {}, ["https://x/"], [("https://x/",)],
    [(None, "x")], [("https://x/", "bad:prefix")], [("relative/", "x")]])
@pytest.mark.parametrize("invoke", [
    lambda b: rp._canonical_identifier("plain", identifier_bases=b),
    lambda b: rp._id_origin(None, None, identifier_bases=b),
    lambda b: rp._base_in("", "", identifier_bases=b),
    lambda b: rp._id_slots({}, identifier_bases=b),
])
def test_malformed_explicit_rules_refuse_before_shortcuts(bad, invoke):
    with pytest.raises(ValueError, match="identifier_bases"):
        invoke(bad)


def test_explicit_empty_opposite_and_forward_reverse_aliases_never_use_ambient(monkeypatch):
    from data_sheets_schema import api_runner
    def forbidden():
        raise AssertionError("ambient aliases consulted")
    monkeypatch.setattr(api_runner, "_identifier_form_tables", forbidden)
    url, curie = "https://doi.org/10.9999/Case", "doi:10.9999/Case"
    assert rp._canonical_identifier(url, identifier_bases=()) == url
    assert rp._canonical_identifier(url, identifier_bases=DOI) == curie
    assert rp._canonical_identifier(url, identifier_bases=(("https://doi.org/", "old"),)) == "old:10.9999/Case"
    assert rp._id_origin(url + "#part", curie, identifier_bases=DOI) == ("minted", None)
    assert rp._id_origin(url + "#part", curie, identifier_bases=()) == ("constructed", url)
    for a, b in ((url, curie), (curie, url)):
        assert rp._base_in(a, "Source: " + b, identifier_bases=DOI)
        assert not rp._base_in(a, "Source: " + b, identifier_bases=())
    # The released exemption protocol remains separate from schema aliases.
    assert rp._id_origin("urn:neutral:x", None, identifier_bases=()) == ("minted", None)
    assert rp._id_origin("doi:10.9999/case#part", curie, identifier_bases=()) == ("minted", None)


def test_url_case_path_case_and_delimiter_boundaries_are_preserved():
    assert rp._canonical_identifier("HTTPS://EXAMPLE.org/Path/A", identifier_bases=()) == "https://example.org/Path/A"
    assert rp._id_origin("https://example.org/Path#part", "https://example.org/path", identifier_bases=())[0] == "constructed"
    for suffix in ("0", "/access", "/", ".1/x", "-2"):
        assert not rp._base_in("https://example.org/3", "https://example.org/3" + suffix, identifier_bases=())
    assert rp._base_in("https://example.org/3", "(https://example.org/3).", identifier_bases=())
    bases = (("https://example.org/name", "unbounded"),)
    assert rp._canonical_identifier("https://example.org/nameOther", identifier_bases=bases) == "https://example.org/nameOther"
    assert not rp._base_in("unbounded:Other", "https://example.org/nameOther", identifier_bases=bases)


def fixture_run(tmp_path, prefixes=None, *, resolver="https://doi.org/", prefix="doi"):
    from data_sheets_schema.chunking import chunk_texts
    old = {"id": prefix + ":10.9999/dataset", "file_collections": [
        {"id": resolver + "10.9999/neutral", "description": TEXT},
        {"id": resolver + "10.9999/dataset#part", "name": "Own part"},
        {"id": resolver + "10.9999/source#part", "name": "Other referenced part"}]}
    new = copy.deepcopy(old)
    new["file_collections"][0] = {"id": prefix + ":10.9999/neutral", "description": REPLACED}
    prov, instr = Pack()._run(tmp_path, full=new,
        bundle_extra="\n" + TEXT + "\nSource identifier: " + prefix + ":10.9999/source\n")
    record = yaml.safe_load(prov.read_text())
    schema = {"id": "https://example.test/schema", "name": "neutral", "default_range": "string",
        "prefixes": {"linkml": "https://w3id.org/linkml/", "xsd": "http://www.w3.org/2001/XMLSchema#", **(prefixes or {})},
        "types": {"string": {"base": "str", "uri": "xsd:string"}, "uriorcurie": {"base": "URIorCURIE", "uri": "xsd:anyURI"}},
        "classes": {"Dataset": {"attributes": {"id": {"range": "uriorcurie", "identifier": True},
            "file_collections": {"range": "FileCollection", "multivalued": True, "inlined_as_list": True}}},
            # Deliberately optional historically; current flags must still use
            # the separately disclosed current implementation schema.
            "FileCollection": {"attributes": {"id": {"range": "uriorcurie"}, "name": {}, "description": {}}}}}
    schema_path = tmp_path / "historical-schema.yaml"
    schema_path.write_text(yaml.safe_dump(schema))
    record["schema"] = {"full_path": str(schema_path), "full_sha256": hashlib.sha256(schema_path.read_bytes()).hexdigest()}
    prov.write_text(yaml.safe_dump(record))
    inter = prov.parent / "intermediate"; inter.mkdir()
    (inter / "P_full.yaml").write_text(yaml.safe_dump(old))
    manifest = yaml.safe_load(Path(record["inputs"]["chunks"]["path"]).read_text())
    bundle = Path(record["inputs"]["bundle_path"]).read_text()
    cid = next(c["id"] for c, text in zip(manifest["chunks"], chunk_texts(bundle, manifest["chunks"])) if TEXT in text)
    receipt = {"bundle_md5": record["inputs"]["bundle_md5"], "chunks": [
        {"id": cid, "status": "extracted", "extracted": [{"slot": SLOT, "snippet": TEXT}]}]}
    (prov.parent / "P_coverage_receipt.yaml").write_text(yaml.safe_dump(receipt))
    return prov, instr, record, schema_path


def tree_bytes(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def build(prov, instr):
    return rp.build_pack(prov, instr, {"receipted_slots": 100, "receiptless_slots": 100},
                         write_instruction=False, instruction_out=[])


@pytest.mark.parametrize("prefixes,joined", [({}, False), ({"doi": "https://doi.org/"}, True),
                                              ({"old": "https://doi.org/"}, False)])
def test_actual_disk_authority_controls_both_inventories_and_id_labels(tmp_path, monkeypatch, prefixes, joined):
    prov, instr, record, schema = fixture_run(tmp_path, prefixes)
    before = tree_bytes(tmp_path)
    real = rs.identifier_rules
    selections = []
    def once(actual):
        selections.append(copy.deepcopy(actual))
        return real(actual)
    monkeypatch.setattr(rs, "identifier_rules", once)
    pack = build(prov, instr)
    assert len(selections) == 1
    assert pack["pack_version"] == 7
    identity = pack["identity_rules"]
    assert identity["schema_basis"]["source"] == "the run's schema, on disk"
    assert identity["schema_basis"]["sha256"] == record["schema"]["full_sha256"]
    assert identity["bases_sha256"] == hashlib.sha256(json.dumps(identity["bases"], separators=(",", ":")).encode()).hexdigest()
    item = next(i for i in pack["items"] if i["kind"] == "slot_receipted")
    assert item["resolved_path"] == (SLOT if joined else None)
    assert item["resolution"] == ("same" if joined else "entry_dropped")
    assert item["value"] == (REPLACED if joined else rp.UNRESOLVED)
    without = {i["slot"] for i in pack["items"] if i["kind"] == "slot_receiptless"}
    assert (SLOT not in without) == joined
    rows = {r["path"]: r for r in pack["id_slots"]["entries"]}
    assert rows["file_collections[1].id"]["origin"] == ("minted" if joined else "constructed")
    assert rows["file_collections[2].id"]["base_in_bundle"] == joined
    assert rows["file_collections[0].id"]["forced"] is True  # Current, although historical slot is optional.
    assert "current implementation" in pack["schema_bases"]["id_class_flags"]["basis"]
    assert "historical run's schema" in pack["id_slots"]["note"]
    assert "current implementation" in pack["schema_bases"]["reference_attributes"]
    assert pack["schema_bases"]["pair_warnings"]["paths"] == list(rp.PAIR_SCHEMAS)
    assert "current implementation" in pack["schema_bases"]["registry_labels"]
    assert tree_bytes(tmp_path) == before
    assert build(prov, instr) == pack  # Stable seed and sampling.


def test_historical_only_alias_is_used_even_when_current_schema_lacks_it(tmp_path):
    resolver, prefix = "https://neutral-resolver.example/", "neutral"
    prov, instr, _, _ = fixture_run(tmp_path, {prefix: resolver}, resolver=resolver, prefix=prefix)
    pack = build(prov, instr)
    row = next(i for i in pack["items"] if i["kind"] == "slot_receipted")
    assert row["resolved_path"] == SLOT and row["value"] == REPLACED
    assert rp._canonical_identifier(resolver + "10.9999/neutral") != prefix + ":10.9999/neutral"
    assert pack["id_slots"]["entries"][1]["origin"] == "minted"


def test_current_class_reference_and_pair_results_do_not_switch_with_alias_basis(tmp_path):
    prov, instr, record, schema = fixture_run(tmp_path)
    empty = build(prov, instr)
    document = yaml.safe_load(schema.read_bytes()); document["prefixes"]["doi"] = "https://doi.org/"
    schema.write_text(yaml.safe_dump(document)); record["schema"]["full_sha256"] = hashlib.sha256(schema.read_bytes()).hexdigest()
    prov.write_text(yaml.safe_dump(record))
    selected = build(prov, instr)
    flags = lambda p: [{k: row[k] for k in ("path", "class", "identifier", "required", "forced")}
                       for row in p["id_slots"]["entries"]]
    assert flags(empty) == flags(selected)
    assert empty["reference_attributes"] == selected["reference_attributes"]
    assert [i for i in empty["items"] if i["kind"] == "pair_warning"] == [i for i in selected["items"] if i["kind"] == "pair_warning"]


def test_class_flag_disclosure_names_the_view_actually_selected(tmp_path, monkeypatch):
    from data_sheets_schema.constants import schemas
    prov, instr, _, historical = fixture_run(tmp_path)
    selected = tmp_path / "current-implementation.yaml"
    selected.write_bytes(historical.read_bytes())
    monkeypatch.setattr(schemas, "SCHEMA_FULL_PATH", selected)
    pack = build(prov, instr)
    assert pack["schema_bases"]["id_class_flags"]["path"] == str(selected)
    assert all(not row["forced"] for row in pack["id_slots"]["entries"])
    assert pack["schema_bases"]["pair_warnings"]["paths"] == list(rp.PAIR_SCHEMAS)


def test_explicit_empty_recorded_table_is_not_current_fallback(tmp_path):
    prov, instr, record, schema = fixture_run(tmp_path)
    schema.write_bytes(b"id: https://example.org/empty\nname: empty\nprefixes: {}\nclasses: {}\n")
    record["schema"]["full_sha256"] = hashlib.sha256(schema.read_bytes()).hexdigest(); prov.write_text(yaml.safe_dump(record))
    pack = build(prov, instr)
    assert pack["identity_rules"]["bases"] == []
    assert pack["identity_rules"]["schema_basis"]["source"] != rs.TODAY
    assert next(i for i in pack["items"] if i["kind"] == "slot_receipted")["resolved_path"] is None


@pytest.mark.parametrize("mode", ["missing", "unrecoverable", "malformed"])
def test_fallback_names_actual_current_bytes_separately_from_historical_request(tmp_path, monkeypatch, mode):
    from data_sheets_schema.identifiers import FULL_SCHEMA
    from data_sheets_schema.resources import resource_path
    prov, instr, record, schema = fixture_run(tmp_path)
    if mode == "missing":
        record.pop("schema")
    elif mode == "unrecoverable":
        schema.unlink()
        monkeypatch.setattr("data_sheets_schema.reconstructed_bytes.reconstructed_bytes_for", lambda *a, **k: None)
        monkeypatch.setattr("data_sheets_schema.provenance.committed_bytes_for", lambda *a, **k: None)
    else:
        schema.write_bytes(b"[]\n"); record["schema"]["full_sha256"] = hashlib.sha256(schema.read_bytes()).hexdigest()
    prov.write_text(yaml.safe_dump(record)); before = tree_bytes(tmp_path)
    pack = build(prov, instr); basis = pack["identity_rules"]["schema_basis"]
    assert basis["source"] == rs.TODAY and basis["reason"]
    raw = resource_path(FULL_SCHEMA).read_bytes()
    assert basis["sha256"] == hashlib.sha256(raw).hexdigest()
    assert basis["md5"] == hashlib.md5(raw).hexdigest()
    if mode != "missing":
        assert basis["requested_schema"]["sha256"] == record["schema"]["full_sha256"] != basis["sha256"]
    assert next(i for i in pack["items"] if i["kind"] == "slot_receipted")["resolved_path"] == SLOT
    assert tree_bytes(tmp_path) == before


@pytest.mark.parametrize("mode", ["git", "reconstruction"])
def test_actual_historical_recovery_feeds_the_pack(tmp_path, monkeypatch, mode):
    from data_sheets_schema import provenance as pv, reconstructed_bytes as rb
    prov, instr, record, schema = fixture_run(tmp_path)
    raw = schema.read_bytes(); sha = hashlib.sha256(raw).hexdigest(); md5 = hashlib.md5(raw).hexdigest()
    # Unique path prevents the released per-path Git cache crossing fixtures.
    rel = tmp_path.name + "/schema.yaml"
    record["schema"] = {"full_path": rel, "full_sha256": sha, "full_md5": md5}
    prov.write_text(yaml.safe_dump(record)); schema.unlink()
    if mode == "git":
        git_root = tmp_path / "history"; git_root.mkdir()
        path = git_root / rel; path.parent.mkdir(); path.write_bytes(raw)
        def git(*args):
            return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                "-c", "user.name=Neutral fixture", "-c", "user.email=fixture@example.test", *args],
                cwd=git_root, check=True, capture_output=True).stdout.decode().strip()
        git("init", "-q"); git("add", rel); git("commit", "-qm", "Neutral historical schema")
        commit = git("rev-parse", "HEAD"); path.write_bytes(b"[]\n")
        monkeypatch.setattr(pv, "_REPO_ROOT", git_root)
    else:
        artifact = tmp_path / "reconstructed.yaml.gz"; artifact.write_bytes(gzip.compress(raw, mtime=0))
        entry = {"path": rel, "sha256": sha, "md5": md5, "artefact": str(artifact),
            "artefact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            "base_commit": "fixture-only", "observed_at": "neutral fixture", "issue": 4291}
        monkeypatch.setattr(rb, "RECONSTRUCTIONS", (entry,))
        monkeypatch.setattr(pv, "committed_bytes_for", lambda *a, **k: pytest.fail("reconstruction must not need Git"))
    before = tree_bytes(tmp_path)
    pack = build(prov, instr); basis = pack["identity_rules"]["schema_basis"]
    assert basis["source"] == ("the run's schema, a git blob" if mode == "git" else "the run's schema, reconstructed")
    assert basis["sha256"] == sha and basis["md5"] == md5
    assert set(basis["matched_on"]) == {"sha256", "md5"}
    if mode == "git":
        assert basis["commit"] == commit
    assert next(i for i in pack["items"] if i["kind"] == "slot_receipted")["resolved_path"] is None
    assert tree_bytes(tmp_path) == before


@pytest.mark.parametrize("bad", [None, False, (("relative/", "bad"),), (("https://x/", ""),)])
def test_invalid_authority_refuses_before_any_instruction_or_pack_write(tmp_path, monkeypatch, bad):
    prov, instr, record, _ = fixture_run(tmp_path)
    paths = rp.record_paths(prov)
    paths["pack"].write_text("historical pack bytes\n"); paths["instruction"].write_text("historical instruction bytes\n")
    rules, basis = rs.identifier_rules(record)
    monkeypatch.setattr(rs, "identifier_rules", lambda _: (rules._replace(bases=bad), basis))
    before = tree_bytes(tmp_path)
    with pytest.raises(rp.IdentifierAuthorityUnavailable, match="identifier alias authority unavailable"):
        rp.build_pack(prov, instr)  # Public default normally writes instructions.
    with pytest.raises(rp.IdentifierAuthorityUnavailable):
        rp.write_pack(prov, instr, force=True)  # Force cannot grant an identity authority.
    assert tree_bytes(tmp_path) == before


def test_current_capture_disagreement_is_a_named_cli_refusal(tmp_path, monkeypatch):
    prov, instr, _, _ = fixture_run(tmp_path)
    selected = rs.todays_identifier_rules()._replace(bases=())
    monkeypatch.setattr(rs, "identifier_rules", lambda _: (selected, {"source": rs.TODAY, "reason": "history missing"}))
    module = importlib.import_module("data_sheets_schema.cli.review")
    monkeypatch.setattr(module, "_provenance", lambda *args: prov)
    before = tree_bytes(tmp_path)
    result = CliRunner().invoke(module.review, ["pack", "--method", "claudecode_agent", "--label", "L",
        "--project", "VOICE", "--instruction", str(instr), "--force"])
    assert result.exit_code != 0 and "identifier alias authority unavailable" in result.output
    assert "disagree" in result.output
    assert tree_bytes(tmp_path) == before


def test_existing_version6_pack_pin_blocks_automatic_upgrade(tmp_path):
    prov, instr, _, _ = fixture_run(tmp_path)
    paths = rp.record_paths(prov)
    # The guard is byte-based and must preserve an older-format attestation.
    paths["pack"].write_text("pack_version: 6\nitems: [{id: old-rule, kind: rule}]\n")
    paths["instruction"].write_text("Historical pinned instruction\n")
    digest = hashlib.sha256(paths["pack"].read_bytes()).hexdigest()
    (prov.parent / "P_review.yaml").write_text(yaml.safe_dump({"pack_sha256": digest, "items": []}))
    before = tree_bytes(tmp_path)
    with pytest.raises(rp.PackAttested):
        rp.write_pack(prov, instr)
    assert tree_bytes(tmp_path) == before
