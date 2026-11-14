"""Synthetic capture chronology only; no public launch or observed native result.

The component isolates expensive outer registration reconstruction explicitly.
Runtime/review/capture/guard consumers and the guard's actual clock remain real.
"""
from datetime import datetime, timedelta, timezone

from data_sheets_schema import native_subscription_admission as admission
from data_sheets_schema import native_subscription_capture as capture
from data_sheets_schema import native_subscription_guard_v2 as guard
from tests.test_native_subscription_capture import component
from tests.utils import native_synthetic_evidence as fixture


def test_capture_chronology_does_not_borrow_an_older_word_time(tmp_path, monkeypatch):
    arguments, value = component(tmp_path, monkeypatch)
    ci = tmp_path / 'invented-ci.json'
    ci.write_bytes(b'{"synthetic_component_only":true}')
    # Emulate a word issued before slow reconstruction without sleeping or
    # changing the guard's clock. The second reading is the actual capture time.
    old_word_time = datetime.now(timezone.utc) - timedelta(seconds=400)

    class FixtureTimestamps:
        readings = 0

        @classmethod
        def now(cls, zone):
            cls.readings += 1
            return old_word_time if cls.readings == 1 else datetime.now(zone)

    monkeypatch.setattr(fixture, 'datetime', FixtureTimestamps)

    def forbidden(*args, **kwargs):
        raise AssertionError('chronology component must not execute a capture or native peer')

    monkeypatch.setattr(capture, 'capture_subscription', forbidden)
    monkeypatch.setattr(capture.subprocess, 'Popen', forbidden)
    paths = fixture.authority_for(arguments['registration_raw'], ci, tmp_path)
    instance = admission.load_current(paths['subscription_guard_path'],
        paths['subscription_guard_sha256'], registration_raw=arguments['registration_raw'],
        runtime=value['runtime'], launch_word_path=paths['launch_word_path'],
        review_path=paths['review_path'])
    instance.before_reservation()
    word = guard.strict_json(paths['launch_word_path'].read_bytes())
    observed = guard.strict_json(paths['subscription_guard_path'].read_bytes())
    assert word['authorized_at'] == old_word_time.isoformat().replace('+00:00', 'Z')
    assert observed['captured_at'] != word['authorized_at']
    root = arguments['directory'] / 'captures' / guard.sha(paths['launch_word_path'].read_bytes())
    claim = guard.strict_json((root / 'claim-1.json').read_bytes())
    saved = guard.strict_json((root / 'capture-1/capture.json').read_bytes())
    assert claim['claimed_at'] == observed['captured_at'] == saved['selected_event']['captured_at']
    assert not (tmp_path / 'generation-attempt').exists()
    assert not (tmp_path / 'generation-evidence').exists()
