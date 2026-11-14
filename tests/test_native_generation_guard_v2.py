"""Offline current guard CLI routing; invented capture bytes, no executable calls.

Registration reconstruction and metadata are isolated routing inputs. Runtime,
review/word, retained capture reconstruction, latest-claim selection, guard
construction and exclusive publication use their real implementations.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

import pytest

from data_sheets_schema import native_generation as cli
from data_sheets_schema import native_shared_registration_orchestration as registration
from data_sheets_schema import native_shared_render as render
from data_sheets_schema import native_subscription_capture as capture
from tests.test_native_subscription_capture import component
from tests.test_native_generation_frontdoor import choice_document
from tests.utils.native_synthetic_evidence import authority_for


def test_prepare_guard_v2_reads_supplied_capture_publishes_once_and_refuses_stale_claim(
        tmp_path, monkeypatch, capsys):
    original_popen = subprocess.Popen

    def git_only(argv, *args, **kwargs):
        assert not kwargs.get('shell')
        assert isinstance(argv, (list, tuple)) and Path(argv[0]).name == 'git', (
            'offline guard routing must not execute a binary, capture or provider')
        return original_popen(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, 'Popen', git_only)
    _, value = component(tmp_path, monkeypatch)
    metadata = {'routing_fixture': 'invented metadata; not full registration acceptance'}
    value['selection'] = {'render_spec': metadata}
    raw = capture.canonical({'authority_version': 2, 'controller_sources_sha256': 'f' * 64,
                             'registration': value})

    def reconstructed(submitted):
        assert submitted == raw
        return deepcopy(value)

    def checked_metadata(recorded):
        assert recorded == metadata

    monkeypatch.setattr(registration, 'verified', reconstructed)
    monkeypatch.setattr(render, 'validate_metadata', checked_metadata)
    ci = tmp_path / 'invented-ci.json'
    ci.write_bytes(b'{"scope":"fabricated offline routing only"}\n')
    paths = authority_for(raw, ci, tmp_path)
    registration_path = tmp_path / 'registration.json'
    registration_path.write_bytes(raw)
    choice_path = tmp_path / 'account-choice.json'
    choice_path.write_bytes(capture.canonical(choice_document(raw, value['runtime'])))
    review_raw = paths['review_path'].read_bytes()
    word_raw = paths['launch_word_path'].read_bytes()
    root = Path(json.loads(value['runtime']['limits_basis'])['admission']['capture_state_directory'])
    reservation = root / 'captures' / capture.sha(word_raw)
    manifest = reservation / 'capture-1' / 'capture.json'
    original_manifest = manifest.read_bytes()
    output = tmp_path / 'cli-guard.json'
    reads, writes = [], []
    base_read = capture._read_capture_records_at_root
    base_write = cli._new_file

    def read_given(path, *args, **kwargs):
        reads.append((path, kwargs.get('require_latest')))
        return base_read(path, *args, **kwargs)

    def write_once(path, body):
        base_write(path, body)
        writes.append((path, body))

    def no_producer(*args, **kwargs):
        pytest.fail('offline guard command dispatched capture or native execution')

    monkeypatch.setattr(capture, '_read_capture_records_at_root', read_given)
    monkeypatch.setattr(cli, '_new_file', write_once)
    monkeypatch.setattr(capture, 'capture_subscription', no_producer)
    argv = ['prepare-subscription-guard-v2', '--registration', str(registration_path),
        '--review', str(paths['review_path']), '--launch-word', str(paths['launch_word_path']),
        '--capture', str(manifest), '--output', str(output), '--account-choice', str(choice_path)]
    assert cli.main(argv) == 0
    guard_raw = output.read_bytes()
    assert guard_raw and writes == [(str(output), guard_raw)]
    assert reads == [(manifest, True)]
    guard = capture.strict_json(guard_raw)
    saved = capture.strict_json(original_manifest)
    assert guard['event_sha256'] == saved['selected_event']['event_sha256']
    assert guard['registration_sha256'] == capture.sha(raw)
    assert guard['launch_word_sha256'] == capture.sha(word_raw)
    emitted = json.loads(capsys.readouterr().out)
    assert emitted['command'] == 'prepare-subscription-guard-v2'
    assert emitted['result'] == {'path': str(output), 'guard_sha256': capture.sha(guard_raw)}
    assert emitted['account_choice_sha256'] == capture.sha(choice_path.read_bytes())
    with pytest.raises(FileExistsError):
        cli.main(argv)
    assert output.read_bytes() == guard_raw
    assert writes == [(str(output), guard_raw)]
    assert capsys.readouterr().out == ''

    # A later durable claim is spent even without a completed capture. The CLI
    # must refuse the supplied older capture, not silently choose another slot.
    _, statement, _, binding = capture._authority(raw, review_raw, word_raw, root)
    slot = reservation / 'capture-2'
    slot.mkdir()
    bound = capture._slot_binding(binding, 2, (reservation / 'reserve.json').read_bytes(),
                                  (reservation / 'claim-1.json').read_bytes())
    stamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    claim_raw = capture.canonical(capture._claim(slot, statement['quota_capture'],
                                               value['runtime'], bound, stamp))
    (reservation / 'claim-2.json').write_bytes(claim_raw)
    (slot / 'claim.json').write_bytes(claim_raw)
    refused_output = tmp_path / 'refused-guard.json'
    argv[argv.index('--output') + 1] = str(refused_output)
    with pytest.raises(ValueError, match='^subscription guard must use the last claimed capture under the word$'):
        cli.main(argv)
    assert reads == [(manifest, True)] * 3
    assert not refused_output.exists()
    assert output.read_bytes() == guard_raw and manifest.read_bytes() == original_manifest
    assert writes == [(str(output), guard_raw)]
    assert capsys.readouterr().out == ''
