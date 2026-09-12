"""Failed qualified-report rebuilds must retain the previous manuscript caveats."""
import importlib.util
import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'notes/reference_rescore_2026-09-11/execution_tools/qualify_reference_results.py'
REPORTS = ('results.json', 'results.md', 'completion_summary.md', 'semantic_errata.md')


def reports(tmp_path, *, omit_erratum=False):
    plan = tmp_path / 'notes/reference_rescore_2026-09-11'
    plan.mkdir(parents=True)
    before = {}
    for name in REPORTS:
        content = None if omit_erratum and name == 'semantic_errata.md' else f'Qualified prior report: {name}\n'.encode()
        before[name] = content
        if content is not None:
            (plan / name).write_bytes(content)
    return plan, before


def assert_preserved(plan, before):
    for name, content in before.items():
        path = plan / name
        if content is None:
            assert not path.exists()
        else:
            assert path.read_bytes() == content


def load_helper():
    spec = importlib.util.spec_from_file_location('reference_qualification_test', HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('metadata', [None, '{malformed JSON'])
def test_rebuild_refuses_bad_errata_before_overwriting_reports(tmp_path, monkeypatch, metadata):
    plan, before = reports(tmp_path)
    (plan / 'manifest.json').write_text('{}')
    if metadata is not None:
        (plan / 'semantic_errata.json').write_text(metadata)
    invoked = []

    def raw_report(_manifest):
        invoked.append('report')
        (plan / 'results.json').write_text(json.dumps({'completed': 56, 'planned': 56, 'pending': []}))
        (plan / 'results.md').write_text('Completed 56 of 56 planned evaluations.\n')

    runner = SimpleNamespace(ROOT=tmp_path, PLAN=plan, verify_frozen=lambda _m: None, report_results=raw_report)
    monkeypatch.setitem(sys.modules, 'reference_rescore', runner)
    monkeypatch.setattr(sys, 'argv', [str(HELPER), '--rebuild'])
    monkeypatch.chdir(tmp_path)
    original_run_path = runpy.run_path

    def run_path(path, **kwargs):
        if Path(path).name == 'write_reference_completion.py':
            invoked.append('completion')
            (plan / 'completion_summary.md').write_text('All 56 ratings complete.\n')
            return {}
        return original_run_path(path, **kwargs)

    monkeypatch.setattr(runpy, 'run_path', run_path)
    with pytest.raises((FileNotFoundError, json.JSONDecodeError)):
        runpy.run_path(str(HELPER), run_name='__main__')
    assert invoked == []
    assert_preserved(plan, before)


@pytest.mark.parametrize('error', [RuntimeError('rebuild failed'), KeyboardInterrupt()])
def test_later_rebuild_failure_restores_all_previous_reports(tmp_path, monkeypatch, error):
    plan, before = reports(tmp_path)
    helper = load_helper()
    monkeypatch.setattr(helper, 'preflight', lambda _root: {})

    def fail_after_writes(_root):
        for name in REPORTS:
            (plan / name).write_text('Unqualified replacement\n')
        raise error

    monkeypatch.setattr(helper, '_rebuild', fail_after_writes)
    with pytest.raises(type(error)):
        helper.qualify(tmp_path, rebuild=True)
    assert_preserved(plan, before)


def test_qualification_failure_restores_reports_and_prior_absence(tmp_path, monkeypatch):
    plan, before = reports(tmp_path, omit_erratum=True)
    helper = load_helper()
    monkeypatch.setattr(helper, 'preflight', lambda _root: {})

    def raw_report(_root):
        for name in REPORTS[:3]:
            (plan / name).write_text('Unqualified replacement\n')

    def broken_qualification(_root, _errata):
        (plan / 'results.md').write_text('Partly qualified\n')
        (plan / 'semantic_errata.md').write_text('Partial new erratum\n')
        raise ValueError('qualification failed')

    monkeypatch.setattr(helper, '_rebuild', raw_report)
    monkeypatch.setattr(helper, '_write_qualified', broken_qualification)
    with pytest.raises(ValueError, match='qualification failed'):
        helper.qualify(tmp_path, rebuild=True)
    assert_preserved(plan, before)
