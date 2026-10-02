"""Run-bound receipt joins preserve source bytes and the legacy default (#4284)."""
import copy
import gzip
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import receipts as rc, run_schema

ORIGINAL = {"items": [{"id": "https://doi.org/10.9999/neutral",
                       "description": "Original neutral account documented thoroughly."}]}
FINAL = {"items": [{"id": "doi:10.9999/neutral",
                    "description": "Revised neutral account with different content."}]}
DOI_BASES = (("https://doi.org/", "doi"),)
PATH = "items[0].description"


def pure_inputs():
    text = ORIGINAL["items"][0]["description"]
    md5 = hashlib.md5(text.encode()).hexdigest()
    receipt = {"bundle_md5": md5, "chunks": [{"id": "c001", "status": "extracted",
        "extracted": [{"slot": PATH, "snippet": text}]}]}
    manifest = {"bundle_md5": md5, "chunks": [{"id": "c001"}]}
    return receipt, manifest, {"c001": text}, copy.deepcopy(FINAL), md5, copy.deepcopy(ORIGINAL)


def legacy_outputs(module, **kwargs):
    args = pure_inputs()
    return {"check": module.check(*args, **kwargs),
            "claims": module.claim_receipts(args[0], args[3], args[5], **kwargs),
            "uncovered": module.uncovered_receiptable_leaves(*args, **kwargs),
            "remap": module.remap_path(PATH, args[5], args[3], **kwargs)}


def test_default_output_bytes_match_pre_change_baseline():
    # Captured from 0a510290b receipts.py before #4284, with only these public
    # neutral inputs. This freezes the complete pure output, not a subset.
    output = legacy_outputs(rc)
    assert hashlib.sha256(json.dumps(output, sort_keys=True).encode()).hexdigest() == "468951171a94431fe94e8d4a4a635041a625780fd07019c4bc95cf8c35b7edb3"
    assert legacy_outputs(rc, identifier_bases=None) == output


@pytest.mark.parametrize("bases,joined", [(None, True), ((), False), (DOI_BASES, True),
    ((("https://example.org/unrelated/", "doi"),), False)])
def test_checker_inventory_and_claims_use_the_same_table(bases, joined):
    args = pure_inputs()
    before = copy.deepcopy(args)
    block = rc.check(*args, identifier_bases=bases)
    uncovered = rc.uncovered_receiptable_leaves(*args, identifier_bases=bases)
    claim = rc.claim_receipts(args[0], args[3], args[5], identifier_bases=bases)["slots"][PATH]
    assert claim["resolved_path"] == (PATH if joined else None)
    assert (PATH not in uncovered) is joined
    assert block["slots"]["without_receipt"] == uncovered
    assert len(uncovered) == block["slots"]["receiptable"] - block["slots"]["with_receipt"]
    assert args == before


@pytest.mark.parametrize("invoke", [
    lambda table: rc._canonical_identifier("plain", identifier_bases=table),
    lambda table: rc._entry_key(None, identifier_bases=table),
    lambda table: rc._locate({}, 0, [], identifier_bases=table),
    lambda table: rc.remap_path("", None, {}, identifier_bases=table),
    lambda table: rc._follow_receipt_paths([], {}, None, identifier_bases=table),
    lambda table: rc.claim_receipts({}, identifier_bases=table),
    lambda table: rc.check({}, {}, {}, {}, None, identifier_bases=table),
    lambda table: rc.uncovered_receiptable_leaves({}, {}, {}, {}, identifier_bases=table),
])
@pytest.mark.parametrize("bad", [False, "", {}, ["https://x/"], [("https://x/",)],
    [(None, "x")], [({}, "x")], [("https://x/", "")], [("https://x/", "bad:prefix")],
    [("https://x/", "with space")], [("relative/", "x")], [("https:///", "x")],
    [("https://x/\n", "x")]])
def test_explicit_malformed_tables_refuse_even_without_paths(invoke, bad):
    with pytest.raises(ValueError, match="identifier_bases"):
        invoke(bad)


def test_explicit_table_is_frozen_and_does_not_consult_ambient_rules(monkeypatch):
    from data_sheets_schema import api_runner
    def ambient_forbidden():
        raise AssertionError("ambient aliases consulted")
    monkeypatch.setattr(api_runner, "_identifier_form_tables", ambient_forbidden)
    supplied = [["https://doi.org/", "doi"]]
    assert rc.remap_path(PATH, ORIGINAL, FINAL, identifier_bases=supplied)["path"] == PATH
    assert supplied == [["https://doi.org/", "doi"]]
    supplied.clear()
    assert rc.remap_path(PATH, ORIGINAL, FINAL, identifier_bases=supplied)["path"] is None


def test_nested_reordering_changed_values_case_fragments_and_boundary():
    old = {"groups": [{"name": "outer", "items": ORIGINAL["items"]}]}
    new = {"groups": [{"name": "other"}, {"name": "outer", "items": [
        {"id": "doi:unrelated", "description": "not that entry"}, FINAL["items"][0]]}]}
    assert rc.remap_path("groups[0].items[0].description", old, new,
                         identifier_bases=DOI_BASES) == {"path": "groups[1].items[1].description", "basis": "by_id"}
    assert rc.remap_path("groups[0].items[0].description", old, new, identifier_bases=())["path"] is None
    assert rc._canonical_identifier("HTTPS://DOI.ORG/Case#Frag", identifier_bases=DOI_BASES) == "doi:Case#Frag"
    assert rc._canonical_identifier("https://doi.org/", identifier_bases=DOI_BASES) == "https://doi.org/"
    # Preserve #976's resolver boundary, even when a schema declares a
    # namespace without a trailing delimiter.
    assert rc._canonical_identifier("https://x.test/namespaceOther", identifier_bases=
                                    (("https://x.test/namespace", "x"),)) == "https://x.test/namespaceOther"
    assert rc._canonical_identifier("https://x.test/namespace/a", identifier_bases=
        (("https://x.test/namespace/", "specific"), ("https://x.test/", "broad"))) == "specific:a"


@pytest.fixture
def disk(tmp_path):
    from data_sheets_schema.chunking import build_manifest, dump_manifest, chunk_texts
    bundle, full, receipt, manifest, snapshot = (tmp_path / name for name in (
        "NEUTRAL.txt", "NEUTRAL_d4d.yaml", "NEUTRAL_coverage_receipt.yaml", "chunks.yaml", "NEUTRAL_full.yaml"))
    bundle.write_text(ORIGINAL["items"][0]["description"])
    full.write_text(yaml.safe_dump(FINAL, sort_keys=False))
    snapshot.write_text(yaml.safe_dump(ORIGINAL, sort_keys=False))
    built = build_manifest(bundle)
    manifest.write_text(dump_manifest(built))
    cid = built["chunks"][0]["id"]
    rec = {"bundle_md5": built["bundle_md5"], "chunks": [{"id": cid, "status": "extracted",
           "extracted": [{"slot": PATH, "snippet": bundle.read_text()}]}]}
    receipt.write_text(yaml.safe_dump(rec))
    record = {"run": {"project": "NEUTRAL", "generation_id": "owned-neutral-generation"},
              "intermediates": [{"phase": "NEUTRAL_full.yaml", "path": str(snapshot),
                   "sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
                   "generation_id": "owned-neutral-generation"}]}
    options = dict(full_path=full, receipt=receipt, bundle=bundle,
                   record_bundle_md5=built["bundle_md5"], record_bundle_sha256=built["bundle_sha256"],
                   expected=True, manifest=manifest, snapshot_record=record)
    args = (rec, built, dict(zip([c["id"] for c in built["chunks"]],
                                chunk_texts(bundle.read_text(), built["chunks"]))), FINAL,
            built["bundle_md5"], ORIGINAL)
    return options, args, record


def pin_schema(record, path, raw):
    path.write_bytes(raw)
    record["schema"] = {"full_path": str(path), "full_sha256": hashlib.sha256(raw).hexdigest(),
                        "full_md5": hashlib.md5(raw).hexdigest()}


@pytest.fixture
def historical(tmp_path, disk):
    raw = gzip.decompress((Path(__file__).parent / "fixtures/verifiable/historical_full_88142c4.yaml.gz").read_bytes())
    assert hashlib.sha256(raw).hexdigest() == "533f561ba3c85a31486ff2ff962be83555a9d81ac57a0891aaf39b411d283f4b"
    pin_schema(disk[2], tmp_path / "historical.yaml", raw)
    return disk


def test_real_historical_block_selects_once_and_preserves_all_inputs(historical, tmp_path, monkeypatch):
    options, args, record = historical
    rules, _ = run_schema.identifier_rules(record)
    assert "doi" not in rules.prefixes
    selected = []
    real = run_schema.identifier_rules
    def selecting(actual):
        assert actual is record
        selected.append(actual)
        return real(actual)
    monkeypatch.setattr(run_schema, "identifier_rules", selecting)
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    record_before = copy.deepcopy(record)
    block = rc.block_for(**options)
    assert len(selected) == 1
    assert block["checked"], block
    assert block["instrument"] == rc.RECEIPTS_INSTRUMENT
    assert PATH in block["slots"]["without_receipt"]
    assert PATH not in rc.check(*args)["slots"]["without_receipt"]
    assert block["slots"] == rc.check(*args, identifier_bases=rules.bases)["slots"]
    assert block["slots"]["without_receipt"] == rc.uncovered_receiptable_leaves(*args, identifier_bases=rules.bases)
    identity = block["identity_rules"]
    assert identity["instrument"] == rc.IDENTITY_RULES_INSTRUMENT
    assert identity["schema_basis"]["sha256"] == record["schema"]["full_sha256"]
    assert identity["schema_basis"]["source"] == "the run's schema, on disk"
    assert identity["bases_sha256"] == hashlib.sha256(json.dumps(identity["bases"], separators=(",", ":")).encode()).hexdigest()
    assert {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before
    assert record == record_before


def test_recorded_empty_table_is_not_current_fallback(disk, tmp_path):
    options, _, record = disk
    pin_schema(record, tmp_path / "empty-schema.yaml", b"id: https://example.org/neutral\nname: neutral\nprefixes: {}\nclasses: {}\n")
    block = rc.block_for(**options)
    assert block["checked"], block
    assert block["identity_rules"]["bases"] == []
    assert block["identity_rules"]["schema_basis"]["source"] != run_schema.TODAY
    assert PATH in block["slots"]["without_receipt"]


@pytest.mark.parametrize("schema_state", ["missing", "unrecoverable", "malformed"])
def test_fallback_discloses_actual_current_bytes_not_requested_hash(disk, tmp_path, monkeypatch, schema_state):
    from data_sheets_schema import provenance
    from data_sheets_schema.identifiers import FULL_SCHEMA
    from data_sheets_schema.resources import resource_path
    options, args, record = disk
    if schema_state == "unrecoverable":
        record["schema"] = {"full_path": str(tmp_path / "missing.yaml"), "full_sha256": "1" * 64}
        monkeypatch.setattr(provenance, "committed_bytes_for", lambda *a, **k: None)
    elif schema_state == "malformed":
        pin_schema(record, tmp_path / "invalid-schema.yaml", b"[]\n")
    block = rc.block_for(**options)
    assert block["checked"], block
    assert block["slots"] == rc.check(*args)["slots"]
    basis = block["identity_rules"]["schema_basis"]
    raw = resource_path(FULL_SCHEMA).read_bytes()
    assert basis["source"] == run_schema.TODAY
    assert basis["path"] == str(FULL_SCHEMA)
    assert basis["sha256"] == hashlib.sha256(raw).hexdigest()
    assert basis["md5"] == hashlib.md5(raw).hexdigest()
    assert basis["reason"]
    if schema_state != "missing":
        assert basis["requested_schema"]["sha256"] == record["schema"]["full_sha256"] != basis["sha256"]


def test_inconsistent_current_byte_projection_refuses_checked_block(disk, monkeypatch):
    real = run_schema.identifier_rules
    def inconsistent(record):
        rules, basis = real(record)
        return rules._replace(bases=()), basis
    monkeypatch.setattr(run_schema, "identifier_rules", inconsistent)
    block = rc.block_for(**disk[0])
    assert not block["checked"]
    assert "current schema bytes disagree" in block["reason"]


def test_receipt_v4_selection_is_independent_of_recorded_schema(historical):
    from tests.test_receipt_completion_policy import declaration
    options, args, record = historical
    record["prompts"] = {"request": {"spec": declaration()}}
    block = rc.block_for(**options)
    assert block["checked"], block
    assert block["instrument"] == rc.RERECEIPTS_INSTRUMENT
    assert "coverage_floor" in block
    assert block["identity_rules"]["schema_basis"]["source"] != run_schema.TODAY
    assert PATH in block["slots"]["without_receipt"]
