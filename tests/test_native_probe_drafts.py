"""Draft rejection and source-derived facts; no executable is invoked."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]


def test_probe_drafts_are_not_runtime_or_authorization(tmp_path):
    spec=importlib.util.spec_from_file_location('draft_probe',ROOT/'scripts/draft_native_probe_packet.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    binary=tmp_path/'SYNTHETIC-INERT-NEVER-EXECUTE'; binary.write_bytes(b'SYNTHETIC inert fingerprint only\n'); binary.chmod(0o700)
    out=tmp_path/'draft'
    module.generate(ROOT,binary,out)
    from data_sheets_schema import native_u4b_probe_sequence as sequence
    from data_sheets_schema.native_u4b_policy import TERM_VALUES
    runtime=json.loads((out/'provisional-runtime.DRAFT.json').read_bytes())
    auth=(out/'authorization.DRAFT.json').read_bytes()
    packet=json.loads((out/'probe-packet.DRAFT.json').read_bytes())
    candidate=runtime['candidate_runtime']
    from data_sheets_schema.native_run_limits import CANARY, require_registered_pair
    assert require_registered_pair(candidate)==CANARY==('90',21600)
    assert candidate['environment']['PYSTOW_HOME'].startswith('OWNER_INPUT_REQUIRED:')
    with pytest.raises(ValueError): sequence.validate_provisional_runtime(runtime)
    with pytest.raises(ValueError): sequence.authorization(auth,runtime)
    nested=json.loads(auth)['candidate_authorization']
    assert nested['word']=='DRAFT_NOT_AUTHORIZED'
    assert packet['running_source_contract']['admission_terms']==TERM_VALUES
    assert packet['execution_count']['successful_total']==1+1+len(packet['execution_count']['traces'])
    assert all(path.stat().st_size for path in out.iterdir())
    with pytest.raises(FileExistsError): module.generate(ROOT,binary,out)
