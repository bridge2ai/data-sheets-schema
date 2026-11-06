"""Actual render-only legacy/explicit-v2 output equivalence, without native probes."""
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import subprocess
import sys
import shutil
from tests.test_native_authority_v2 import API_ARGS

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'notes/matched_cborg_2026-09-13'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_explicit_old_values_render_identical_files(tmp_path, monkeypatch):
    old = load('historical_preparation', BASE/'prepare_registration.py')
    new = load('explicit_preparation', BASE/'prepare_registration_v2.py')
    # The unchanged old main probes a native version even in render-only mode.
    # Stub only that call; never execute any native binary. Git remains real.
    check_output = subprocess.check_output
    probes = []
    def offline(command, *args, **kwargs):
        if command == ['/Users/marcin/.local/bin/claude', '--version']:
            probes.append(command)
            return 'offline-not-probed'
        assert command[0] == 'git', command
        return check_output(command, *args, **kwargs)
    monkeypatch.setattr(subprocess, 'check_output', offline)
    destination = tmp_path/'rendered'
    argv = ['prepare', '--render-only', '--output', str(destination)]
    monkeypatch.setattr(sys, 'argv', argv)
    old_pins = {}
    new_pins = {}
    old_sha, new_sha = old.sha, new.sha
    def capture(target, original, path):
        value = original(path)
        target[str(Path(path).resolve())] = value
        return value
    monkeypatch.setattr(old, 'sha', lambda path: capture(old_pins, old_sha, path))
    monkeypatch.setattr(new, 'sha', lambda path: capture(new_pins, new_sha, path))
    # Observe the actual final pin maps, not the superset of sha() calls.
    def capture_save(target, original, path, value):
        if path.name == 'rendered_jobs.json':
            frame = inspect.currentframe()
            try:
                manifest = frame.f_back.f_back.f_locals['manifest']
                target.clear()
                target.update(manifest['pinned_files'])
            finally:
                del frame
        original(path, value)
    old_save, new_save = old.save, new.save
    monkeypatch.setattr(old, 'save', lambda path, value: capture_save(old_pins, old_save, path, value))
    monkeypatch.setattr(new, 'save', lambda path, value: capture_save(new_pins, new_save, path, value))
    old.main()
    before = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in destination.rglob('*') if p.is_file()}
    assert before and len(probes) == 1
    shutil.move(destination, tmp_path/'old-rendered')
    metadata = {
        'project': 'KIDS_FIRST', 'profile': 'neutral', 'status': 'registered',
        'basis': 'user nomination of the Kids First Data Resource and its AJHG publication on 2026-09-13',
        'source_capture_authorization': 'user requires links, documentation and information about participating datasets, 2026-09-13',
        'paper_doi': '10.1016/j.ajhg.2026.07.010',
        'article_representation': 'indexed metadata and abstract; publisher full-text retrieval unavailable',
        'catalogue_studies': 36, 'source_documents': 55,
        'source_manifest': str(BASE/'kids_first/manifest.yaml'),
        'applicability_context': str(BASE/'kids_first/applicability.yaml'),
        'chunks': str(BASE/'kids_first/chunks.yaml'),
    }
    external = tmp_path/'external.json'
    external.write_text(json.dumps(metadata))
    monkeypatch.setattr(sys, 'argv', argv + ['--projects', ','.join(old.PROJECTS),
        '--canary-order', old.DEFAULT_CANARY_ORDER, '--external-canary', str(external),
        '--external-sources', str(BASE/'external_clinical'), '--external-sources', str(BASE/'kids_first'), *API_ARGS])
    new.main()
    after = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in destination.rglob('*') if p.is_file()}
    assert set(after) == set(before)
    # The requested truthful profile basis changes recorder text and its hash.
    # Normalize only that exact provenance change; JSON numbers compare by value.
    original = tmp_path/'old-rendered'
    hash_changes = {}
    for relative in before:
        if relative.endswith('.md'):
            text = (original/relative).read_text().replace('stated by the registered caller', 'declared by source manifest')
            assert text == (destination/relative).read_text()
            hash_changes[before[relative]] = hashlib.sha256(text.encode()).hexdigest()
    for relative in before:
        if relative.endswith('.json'):
            text = (original/relative).read_text().replace('stated by the registered caller', 'declared by source manifest')
            for old_hash, new_hash in hash_changes.items():
                text = text.replace(old_hash, new_hash)
            assert json.loads(text) == json.loads((destination/relative).read_bytes())
    # Only the versioned preparer and explicit metadata JSON are additional identities.
    old_pins.pop(str(BASE/'prepare_registration.py'))
    new_pins.pop(str(BASE/'prepare_registration_v2.py'))
    new_pins.pop(str(external))
    assert set(new_pins) == set(old_pins)
    for path, pin in old_pins.items():
        if Path(path).is_relative_to(destination):
            relative = str(Path(path).relative_to(destination))
            # Output equality was checked above, including the provenance delta.
            assert new_pins[path] == after[relative]
        else:
            assert new_pins[path] == pin
    assert sum('/kids_first/' in path for path in new_pins) >= 129
    assert len(probes) == 1  # v2 render-only does not probe the binary
    jobs = json.loads((destination/'rendered_jobs.json').read_bytes())['generation']['jobs']
    assert len(jobs) == 32 and sum(job['canary'] for job in jobs) == 4
    (tmp_path/'equivalence.json').write_text(json.dumps({'old_files': before, 'new_files': after, 'pin_count': len(new_pins), 'kids_first_pins': sum('/kids_first/' in p for p in new_pins), 'allowed_difference': 'truthful profile_basis and derived instruction hashes; JSON numeric representation',
        'jobs': len(jobs), 'canaries': 4, 'native_calls': 0}, indent=2)+'\n')
