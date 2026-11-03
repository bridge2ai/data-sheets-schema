"""Observe final main D41 boundaries with real BC1 controllers; task 5, 2026-11-03."""
import hashlib
import json
from dataclasses import replace
from pathlib import Path
import sys

import pytest
import yaml

from data_sheets_schema import api_runner as api, bc1_runtime as runtime
from data_sheets_schema import latch_journal as journal, typed_audit_runtime as typed, usage_ledger as ledger
from tests.test_bc1_pipeline import external, offline, BC1Script  # noqa: F401
from tests.test_bc1_selection import simulated_hooks, registered as base_registered  # noqa: F401
from tests.test_bc1_pipeline import test_public_bc1_pipeline_multiple_groups_final_and_completed_replay as pipeline
from tests.test_shared_generation_runtime import scripted_client
from tests.test_d68_legacy_readonly import tree


@pytest.fixture
def registered(base_registered):
    # A separate positive-control profile, leaving the neutral pipeline's
    # G1 term-label failure visible in its original, unchanged test.
    from data_sheets_schema import profiles, shared_generation as sg
    spec = base_registered
    reg = json.loads(spec.shared_generation_registration)
    if spec.manifest is not None:
        manifest = yaml.safe_load(spec.manifest.read_bytes())
        manifest['profile'] = 'bridge2ai'
        spec.manifest.write_text(yaml.safe_dump(manifest))
        reg['inputs']['source_manifest'] = sg.file_pin(spec.manifest)
    context = Path(reg['inputs']['context']['path'])
    value = json.loads(context.read_bytes())
    value['vocabulary'] = profiles.vocabulary_for(profiles.BRIDGE2AI)
    context.write_bytes(sg.canonical(value))
    reg['inputs']['context'] = sg.file_pin(context)
    reg['inputs']['profile'] = {'name': 'bridge2ai', 'basis': 'explicit journal control',
                               'vocabulary': sg.file_pin(profiles.BRIDGE2AI.pin_path)}
    raw = sg.canonical(reg)
    Path(reg['registration_path']).write_bytes(raw)
    return replace(spec, profile='bridge2ai', profile_basis='explicit journal control',
                   shared_generation_registration=raw.decode())


def test_every_bc1_response_is_journaled_before_parse(registered, journal_launch_monitor, tmp_path):
    observed = {}
    active = []
    def monitor(frame, event, arg):
        if event != 'call' or frame.f_code is not runtime._rebuild.__code__:
            return
        selected = frame.f_locals.get('spec')
        if selected.project != registered.project or selected.label != registered.label:
            return
        active[:] = [selected]
        state = frame.f_locals['state']
        for row in state.get('stages', []):
            if row.get('state') != 'response_saved':
                continue
            pin = row['response']
            raw = Path(pin['path']).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == pin['sha256']
            saved = json.loads(raw)
            assert saved['text'] and saved['usage_id']
            events = journal._events(selected)
            snapshots = [e for e in events if e['kind'] == 'latch'
                and e['payload']['key'].startswith('snapshot:')
                and e['payload']['value']['usage_id'] == saved['usage_id']
                and e['payload']['value']['sha256'] == pin['sha256']]
            responses = [e for e in events if e['kind'] == 'latch'
                and e['payload']['key'].startswith('response:typed_audit:')
                and e['payload']['value'] == pin]
            assert snapshots and responses, 'BC1 parse reached without final D41 response journal pins'
            observed[saved['usage_id']] = {'phase': row['selection']['phase'], 'raw_sha256': pin['sha256'],
                'snapshot_event': snapshots[-1]['sha256'], 'response_event': responses[-1]['sha256']}
    previous = sys.getprofile()
    sys.setprofile(monitor)
    try:
        pipeline(registered, journal_launch_monitor)
    finally:
        sys.setprofile(previous)
    assert active
    usage = ledger._read(active[0])['rows']
    typed_rows = [row for row in usage if row['phase'] in runtime.PHASES]
    assert typed_rows and set(observed) == {row['usage_id'] for row in typed_rows}
    assert {row['phase'] for row in typed_rows} == set(runtime.PHASES)
    evidence = tmp_path / 'journal-proof.json'
    evidence.write_text(json.dumps({'responses': observed, 'journal': journal.provenance(active[0])}, indent=2))
    assert evidence.stat().st_size > 0


def test_bc1_typed_entry_legacy_refuses_before_dispatch(registered, tmp_path):
    ledger.ledger_path(registered).parent.mkdir(parents=True, exist_ok=True)
    ledger.ledger_path(registered).write_text('{}\n')
    before = tree(tmp_path)
    script = BC1Script(registered)
    with pytest.raises(ledger.UsageLedgerError, match='artifacts have no journal'):
        typed.run(registered, carry={}, settings={}, usage=[], client=scripted_client(script))
    assert script.calls == [] and tree(tmp_path) == before


@pytest.mark.parametrize('resume', [True, False])
def test_bc1_preserves_final_main_owner_refusal_precedence(registered, tmp_path, resume):
    # Final main's Round 7 deliberately keeps owner refusal ahead of journal
    # decoding at public execute. This is distinct from the typed dispatch.
    registered.full_path.parent.mkdir(parents=True, exist_ok=True)
    registered.full_path.write_text('unowned final output\n')
    journal.journal_path(registered).parent.mkdir(parents=True, exist_ok=True)
    journal.journal_path(registered).write_bytes(b'{')
    before = tree(tmp_path)
    script = BC1Script(registered)
    with pytest.raises(Exception, match='no usable live ownership' if resume else 'already spent'):
        api.execute(registered, resume=resume, client=scripted_client(script))
    assert script.calls == [] and tree(tmp_path) == before
