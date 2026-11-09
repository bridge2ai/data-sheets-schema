"""A4 P3-3: a saved word-A guard cannot authorize recorded word B.

2026-11-08 (#4354). The inherited component isolates protected registration
construction; its ordinary Python capture peer, saved runtime, review parser,
word journal, capture readback and guard admission all execute. No real native
program, provider, account or generation attempt is used.
"""
from pathlib import Path
import subprocess

import pytest

from data_sheets_schema import native_launch_review as review
from data_sheets_schema import native_subscription_admission as admission
from data_sheets_schema import native_subscription_capture as capture
from data_sheets_schema import native_subscription_guard_v2 as guard
from tests.test_native_u4b_admission import prepared
from tests.test_native_u4b_a3_captures import newer, journal_rows
from tests.test_native_subscription_capture import component, read_arguments, word_directory


def test_capture_process_trap_leaves_real_review_git_reads_intact(tmp_path, monkeypatch):
    original = subprocess.Popen
    arguments, _ = component(tmp_path, monkeypatch)
    assert capture.subprocess is not subprocess
    assert capture.subprocess.Popen is original
    class CaptureRefused(Exception):
        pass
    def forbidden(*args, **kwargs):
        raise CaptureRefused('capture launch remains trapped')
    monkeypatch.setattr(capture.subprocess, 'Popen', forbidden)
    assert review.validate_bundle(arguments['registration_raw'], arguments['review_bundle_raw'],
                                  arguments['launch_word_raw'])
    assert subprocess.Popen is original
    with pytest.raises(CaptureRefused, match='capture launch remains trapped'):
        capture.subprocess.Popen(['never-run'])


def test_saved_word_a_guard_refuses_recorded_word_b_before_dispatch(tmp_path, monkeypatch):
    arguments, value, paths, raw = prepared(tmp_path, monkeypatch)
    first = word_directory(arguments) / 'capture-1' / 'capture.json'
    retained = first.read_bytes()
    admitted = admission.load_current(paths['guard'], guard.sha(raw),
        registration_raw=arguments['registration_raw'], runtime=value['runtime'],
        launch_word_path=paths['word'], review_path=paths['review'])
    assert admitted.value['launch_word_sha256'] == guard.sha(arguments['launch_word_raw'])
    assert not admitted.dispatched

    # Word B is genuinely recorded in the same registration's journal. It has
    # no capture; A's saved event/guard must not be relabelled as B's evidence.
    renewed = newer(arguments)
    activated = capture.activate_capture_word(**read_arguments(renewed))
    assert activated['word_sha256'] == guard.sha(renewed['launch_word_raw'])
    assert activated['word_sha256'] != admitted.value['launch_word_sha256']
    word_b = tmp_path / 'recorded-word-b.json'
    word_b.write_bytes(renewed['launch_word_raw'])
    terms_b = review.validate_bundle(arguments['registration_raw'], arguments['review_bundle_raw'],
                                    renewed['launch_word_raw'])
    monkeypatch.setattr(capture.subprocess, 'Popen',
                        lambda *a, **k: pytest.fail('cross-word refusal started another capture'))

    # Direct guard admission proves the immutable word digest check itself;
    # removing it must not be hidden by the outer capture-history refusal.
    with pytest.raises(ValueError, match='binding differs: launch_word_sha256'):
        guard.load_guard(paths['guard'], guard.sha(raw),
            registration_raw=arguments['registration_raw'], runtime=value['runtime'],
            launch_word_path=word_b, owner_statement=terms_b)
    # The outer route seeks B's own reservation, never scans A's directory.
    # No B capture was made, so its missing persisted reservation refuses.
    with pytest.raises(FileNotFoundError) as missing_b:
        admission.load_current(paths['guard'], guard.sha(raw),
            registration_raw=arguments['registration_raw'], runtime=value['runtime'],
            launch_word_path=word_b, review_path=paths['review'])
    assert Path(missing_b.value.filename) == word_directory(renewed) / 'reserve.json'
    with pytest.raises(ValueError, match='superseded'):
        admission.load_current(paths['guard'], guard.sha(raw),
            registration_raw=arguments['registration_raw'], runtime=value['runtime'],
            launch_word_path=paths['word'], review_path=paths['review'])

    assert capture.read_capture(first, **read_arguments(arguments))['status'] == 'captured'
    assert first.read_bytes() == retained and paths['guard'].read_bytes() == raw
    assert len(journal_rows(arguments)) == 2
    assert not word_directory(renewed).exists()
    assert not Path(value['attempt_directory']).exists()
    assert not Path(value['evidence_directory']).exists()
