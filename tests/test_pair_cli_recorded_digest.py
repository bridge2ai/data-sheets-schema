"""The actual Phase 4 CLI must use the recorded per-slot presence rule (#4309)."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from data_sheets_schema import d4d_pair_consistency as pair, schema_digest as sd
from data_sheets_schema.profiles import BRIDGE2AI, NEUTRAL
from data_sheets_schema.resources import resource_path


@pytest.fixture
def known_digest():
    entries = yaml.safe_load(resource_path(sd.INVENTORY_LEDGER).read_bytes())["digests"]
    current = sd.fingerprint(sd.digest_text("Dataset", profile=BRIDGE2AI))
    return next(d for d, inventory in entries.items()
                if d != current and "title" in inventory.get("CoreDataset", []))


def files(tmp_path, digest=None, *, profile=None, full=None, core=None):
    f, c, p = [tmp_path / name for name in ("EXAMPLE_d4d.yaml", "EXAMPLE_d4d_core.yaml", "EXAMPLE_provenance.yaml")]
    f.write_text(yaml.safe_dump(full if full is not None else {"id": "example", "title": "A stated title"}))
    c.write_text(yaml.safe_dump(core if core is not None else {"id": "example"}))
    schema = {} if digest is None else {"digest_md5": digest}
    if profile: schema["profile"] = profile
    p.write_text(yaml.safe_dump({"schema": schema}))
    return f, c, p


def invoke(f, c, *args):
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        status = pair.main(["--full", str(f), "--core", str(c), "--json", *args])
    return status, json.loads(stdout.getvalue())


def test_actual_subprocess_does_not_excuse_a_known_historical_title(tmp_path, known_digest):
    f,c,p = files(tmp_path, known_digest)
    before = {x:x.read_bytes() for x in (f,c,p)}
    proc = subprocess.run([sys.executable, "-m", "data_sheets_schema.d4d_pair_consistency",
                           "--full", str(f), "--core", str(c), "--json"], capture_output=True, text=True)
    assert proc.returncode == 1, proc.stderr
    result = json.loads(proc.stdout)
    assert [x["path"] for x in result["errors"]] == ["$.title"]
    assert result["warnings"] == []
    history = result["presence_context"]
    assert history["schema_moved"] and history["run_digest"] == known_digest
    assert history["ledger_inventory"] == "known"
    assert history["provenance_sha256"] == hashlib.sha256(before[p]).hexdigest()
    assert {x:x.read_bytes() for x in before} == before


def test_slot_not_in_known_historical_core_stays_warning(tmp_path, known_digest, monkeypatch):
    # Synthetic history exercises absence; every retained real ledger row
    # currently contains related_datasets. Never rewrite the captured ledger.
    ledger = tmp_path / 'synthetic_ledger.yaml'
    ledger.write_text(yaml.safe_dump({'digests': {known_digest: {'CoreDataset': ['id', 'title']}}}))
    monkeypatch.setattr(sd, 'INVENTORY_LEDGER', ledger)
    f,c,_ = files(tmp_path, known_digest, full={"id":"example", "related_datasets":[]})
    status, result = invoke(f,c)
    assert status == 0 and result["errors"] == []
    assert [x["path"] for x in result["warnings"]] == ["$.related_datasets"]
    assert result["presence_context"]["ledger_inventory"] == "known"


@pytest.mark.parametrize('digest', [None, '0'*32])
def test_missing_digest_is_strict_and_unknown_digest_retains_disclosed_fallback(tmp_path, digest):
    f,c,_ = files(tmp_path,digest)
    status, result = invoke(f,c)
    assert status == (1 if digest is None else 0)
    assert result["presence_context"]["ledger_inventory"] == "unknown"
    assert result["presence_context"]["schema_moved"] is (digest is not None)
    assert len(result["errors"] if digest is None else result["warnings"]) == 1


@pytest.mark.parametrize('raw', [None, b'\xff', b'[broken', b'- a\n', b'schema: []\n',
    b'schema: {digest_md5: [bad]}\n', b'schema: {digest_md5: false}\n',
    b'schema: {digest_md5: 42}\n', b'schema: {digest_md5: first, digest_md5: second}\n'])
def test_unavailable_or_malformed_provenance_does_not_excuse_presence(tmp_path, raw):
    f,c,p = files(tmp_path)
    if raw is None:p.unlink()
    else:p.write_bytes(raw)
    status,result = invoke(f,c)
    assert status == 1
    assert not result["presence_context"]["schema_moved"]
    assert result["presence_context"]["run_digest"] is None
    assert pair.pair_predates_current_schema(c) is False


def test_matching_records_and_content_disagreement_keep_their_contract(tmp_path,known_digest):
    f,c,_=files(tmp_path,known_digest,core={"id":"example","title":"A stated title"})
    assert invoke(f,c)[0] == 0
    c.write_text('id: example\ntitle: Different\n')
    status,result=invoke(f,c)
    assert status == 1
    assert [e['code'] for e in result['errors']] == ['shared-slot-content']


def test_current_digest_uses_recorded_profile(tmp_path,monkeypatch):
    monkeypatch.setenv('D4D_PROFILE','bridge2ai')
    current=sd.fingerprint(sd.digest_text('Dataset',profile=NEUTRAL))
    f,c,_=files(tmp_path,current,profile='neutral')
    status,result=invoke(f,c)
    assert status==1
    assert result['presence_context']['current_profile']=='neutral'
    assert not result['presence_context']['schema_moved']
    assert not pair.pair_predates_current_schema(c)


def test_comparison_and_ledger_receive_the_same_captured_provenance(tmp_path,known_digest,monkeypatch):
    f,c,p=files(tmp_path,known_digest)
    original=p.read_bytes(); read=Path.read_bytes; reads=[]
    def replacing_read(self):
        data=read(self)
        if self==p:
            reads.append(data)
            p.write_text('schema: {}\n')
        return data
    monkeypatch.setattr(Path,'read_bytes',replacing_read)
    status,result=invoke(f,c)
    assert status==1 and reads==[original]
    assert result['presence_context']['run_digest']==known_digest
    assert result['presence_context']['provenance_sha256']==hashlib.sha256(original).hexdigest()


def test_known_empty_class_inventory_is_distinct_from_unknown(tmp_path,known_digest,monkeypatch):
    ledger=tmp_path/'ledger.yaml'
    ledger.write_text(yaml.safe_dump({'digests':{known_digest:{'CoreDataset':[]}}}))
    monkeypatch.setattr(sd,'INVENTORY_LEDGER',ledger)
    f,c,_=files(tmp_path,known_digest)
    status,result=invoke(f,c)
    assert status==0 and result['presence_context']['ledger_inventory']=='known'
    assert len(result['warnings'])==1


def test_custom_schema_selection_does_not_replace_digest_comparison(tmp_path,known_digest):
    common={'id':'https://example.org/schema','name':'neutral','imports':['linkml:types'],
            'prefixes':{'linkml':'https://w3id.org/linkml/'},'default_range':'string'}
    full_schema=tmp_path/'custom_full.yaml';core_schema=tmp_path/'custom_core.yaml'
    full_schema.write_text(yaml.safe_dump({**common,'classes':{'Dataset':{'attributes':{'id':{'range':'string'},'title':{'range':'string'}}}}}))
    core_schema.write_text(yaml.safe_dump({**common,'classes':{'CoreDataset':{'attributes':{'id':{'range':'string'},'title':{'range':'integer'}}}}}))
    f,c,_=files(tmp_path,known_digest)
    status,result=invoke(f,c,'--full-schema',str(full_schema),'--core-schema',str(core_schema))
    assert status==0 and 'title' not in result['identity_slots']
    history=result['presence_context']
    assert history['full_schema_path']==str(full_schema) and history['core_schema_path']==str(core_schema)
    assert history['current_digest']==sd.fingerprint(sd.digest_text('Dataset', profile=BRIDGE2AI))
    assert history['schema_moved'] and history['run_digest']==known_digest


def test_pure_validator_json_stays_unextended():
    result=pair.validate_pair_data({'id':'example'},{'id':'example'},pair.load_pair_schema()).to_dict()
    assert set(result)=={'passed','identity_slot_count','identity_slots','projected_slots','per_record_slots','errors','warnings'}
