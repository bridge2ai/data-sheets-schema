"""Issue 6046: offline power admission, bounded probes and retained host clocks."""
from datetime import datetime
import json
from pathlib import Path
import sys

import pytest
from data_sheets_schema import native_host_power as power

AC = {'source': 'ac', 'battery_percent': 90, 'lid': 'closed'}


@pytest.mark.parametrize('text,source,level', [
    ("Now drawing from 'AC Power'\n -InternalBattery-0\t89%; charging;", 'ac', 89),
    ("Now drawing from 'Battery Power'\n -InternalBattery-0\t1%; discharging;", 'battery', 1),
    ('unavailable', 'unknown', None),
    ("Now drawing from 'AC Power'\nNow drawing from 'Battery Power'\n", 'unknown', None),
    ("Now drawing from 'AC Power'\n invalid 101%;", 'ac', None),
])
def test_power_parser(text, source, level):
    assert power.parse_power(text, '"AppleClamshellState" = Yes') == {
        'source': source, 'battery_percent': level, 'lid': 'closed'}
    assert power.parse_power(text, '')['lid'] == 'unknown'


def test_probe_uses_only_fixed_bounded_local_interfaces(monkeypatch):
    calls = []
    def local(argv, **kwargs):
        calls.append((argv, kwargs))
        return {'status': 'read', 'reason': None, 'text':
            "Now drawing from 'AC Power'\n95%;" if argv[0].endswith('pmset') else '"AppleClamshellState" = No'}
    monkeypatch.setattr(power, '_local', local)
    actual = power.probe()
    assert (actual['source'], actual['battery_percent'], actual['lid']) == ('ac', 95, 'open')
    assert calls == [(['/usr/bin/pmset', '-g', 'batt'], {'limit': 16384}),
                     (['/usr/sbin/ioreg', '-r', '-n', 'IOPMrootDomain', '-d', '1'], {'limit': 1024 * 1024})]


@pytest.mark.parametrize('source', ['battery', 'unknown'])
def test_refusal_retains_start_reading(tmp_path, monkeypatch, source):
    monkeypatch.setattr(power, 'probe', lambda: {**AC, 'source': source})
    path = tmp_path / 'sequence-start.json'
    with pytest.raises(ValueError, match='positively observed as AC'):
        power.sequence_start(path, '2026-11-13T00:00:00Z')
    assert json.loads(path.read_bytes())['host_power']['source'] == source


def test_ac_closed_lid_admitted_and_start_is_exclusive(tmp_path, monkeypatch):
    monkeypatch.setattr(power, 'probe', lambda: AC)
    path = tmp_path / 'sequence-start.json'
    power.sequence_start(path, '2026-11-13T00:00:00Z')
    assert json.loads(path.read_bytes())['host_power'] == AC
    before = path.read_bytes()
    with pytest.raises(FileExistsError): power.sequence_start(path, 'later')
    assert path.read_bytes() == before


def test_saved_pmset_excerpt_pairs_sleep_and_wake():
    raw = (Path(__file__).parent / 'fixtures/native_host_power/pmset-sleep-20261112.txt').read_text()
    stamp = lambda text: int(datetime.fromisoformat(text).timestamp() * 1e9)
    result = power.parse_sleep_events(raw, stamp('2026-11-12T15:20:00-08:00'), stamp('2026-11-12T18:00:00-08:00'))
    assert [row['overlap_ns'] / 1e9 for row in result['intervals']] == [1252, 7034]
    assert [row['event'] for row in result['events']] == ['Sleep', 'Wake', 'Sleep', 'Wake']
    result = power.parse_sleep_events(raw, stamp('2026-11-12T17:00:00-08:00'), stamp('2026-11-12T17:30:00-08:00'))
    assert result['intervals'][0]['overlap_ns'] / 1e9 == 1800


def test_clock_jump_is_retained_separately_from_sleep_attribution(tmp_path, monkeypatch):
    monkeypatch.setattr(power, 'probe', lambda: AC)
    ticks = iter([(10, 10), (20, 15), (30, 25)])
    def clock(label):
        wall, mono = next(ticks)
        return {'label': label, 'wall_ns': wall * 10**9, 'monotonic_ns': mono * 10**9}
    monkeypatch.setattr(power, 'clock_reading', clock)
    monkeypatch.setattr(power, 'sleep_events', lambda *args: {'status': 'read', 'events': [], 'intervals': []})
    power.start_run(tmp_path, require_ac_power=True)
    power.checkpoint(tmp_path, 'stage-' + 'a' * 64)
    result = power.finish_run(tmp_path)
    assert result['suspension_detected'] is True
    assert result['host_slept'] is False  # A clock jump alone cannot establish its cause.
    assert result['clock_gaps'][0]['difference_ns'] == 5 * 10**9
    assert len(result['clocks']) == 3
    assert json.loads((tmp_path / 'host-observation.json').read_bytes()) == result


def test_unknown_sleep_log_is_not_a_no_sleep_claim(monkeypatch):
    monkeypatch.setattr(power, '_local', lambda *a, **k: {'status': 'unknown', 'reason': 'TimeoutError', 'text': ''})
    assert power.sleep_events(0, 10)['status'] == 'unknown'
    assert power.probe()['source'] == 'unknown'
    assert power.parse_sleep_events('unrecognized output', 0, 10)['status'] == 'unknown'


def test_end_record_failure_does_not_replace_cleanup_failure(tmp_path, monkeypatch):
    def fail(*args): raise OSError('synthetic disk failure')
    monkeypatch.setattr(power, 'finish_run', fail)
    with pytest.raises(RuntimeError, match='cleanup failed') as caught:
        with power.finishing_run(tmp_path):
            raise RuntimeError('cleanup failed')
    assert 'host observation could not be persisted' in caught.value.__notes__[0]


@pytest.mark.parametrize('program,limit,timeout,reason', [
    ("print('x'*10000)", 64, 5, 'ValueError'),
    ('import time; time.sleep(5)', 64, 0.05, 'TimeoutError'),
])
def test_local_probe_bounds_and_reaps_its_child(monkeypatch, program, limit, timeout, reason):
    real = power.subprocess.Popen
    children = []
    def spawn(*args, **kwargs):
        child = real(*args, **kwargs); children.append(child); return child
    monkeypatch.setattr(power.subprocess, 'Popen', spawn)
    result = power._local([sys.executable, '-I', '-c', program], limit=limit, timeout=timeout)
    assert result['status'] == 'unknown' and result['reason'] == reason
    assert len(children) == 1 and children[0].poll() is not None
