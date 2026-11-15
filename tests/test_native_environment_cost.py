"""One real isolated-environment cost canary for the lead ruling, 2026-11-14.

Inputs: this process's installed dependency closure. Output: manifest-cost.json
in pytest's external basetemp, with CPU/wall times and regeneration counters.
No native binary, provider, network request or launch is used.
"""
import json
from pathlib import Path
import time

from data_sheets_schema import native_environment_manifest as manifest


def test_installed_manifest_modes_cost_and_reuse(tmp_path, monkeypatch):
    generate, calls, rows = manifest.generate, [], []
    def counted():
        calls.append(len(calls) + 1)
        return generate()
    monkeypatch.setattr(manifest, 'generate', counted)
    def measure(mode, operation):
        before, cpu, wall = len(calls), time.process_time(), time.perf_counter()
        result = operation()
        rows.append({'operation': mode, 'cpu_seconds': time.process_time() - cpu,
                     'wall_seconds': time.perf_counter() - wall, 'generate_calls': len(calls) - before})
        return result
    pin = measure('write', lambda: manifest.write(tmp_path / 'environment-manifest.json'))
    full = measure('full_reuse', lambda: manifest.verify(pin, mode='full'))
    light = measure('light', lambda: manifest.verify(pin, mode='light'))
    assert full == light
    assert [row['generate_calls'] for row in rows] == [1, 0, 0]
    raw = Path(pin['path']).read_bytes()
    assert len(raw) == pin['bytes'] and manifest.c.sha(raw) == pin['sha256']
    report = {'pin': pin, 'distributions': len(full['distributions']),
              'record_entries': sum(len(row['file_stats']) for row in full['distributions']),
              'unowned_files': len(full['unowned_files']), 'measurements': rows}
    output = tmp_path / 'manifest-cost.json'
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    assert json.loads(output.read_text()) == report
