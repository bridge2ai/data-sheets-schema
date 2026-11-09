"""D114 explicit toolchain exposure, 2026-11-08; no native execution."""
from pathlib import Path

import pytest

from data_sheets_schema import agentic_runtime as subject
from tests.test_generation_specificity_delegated import ROOT, scan


def test_historical_default_keeps_exact_auto_enumerated_resources():
    expected = set(subject.SCHEMAS)
    for directory in ('.claude/commands', '.claude/agents'):
        expected.update(name for name in subject.resource_names(directory)
                        if name not in subject.SELECTED_SHARED_PLAYBOOKS)
    default = subject.toolchain()
    assert default == subject.toolchain(native_shared=False)
    assert set(default['resources']) == expected
    assert '.claude/agents/d4d-rubric10.md' in default['resources']


def test_native_selection_is_closed_and_never_enumerates_future_agents(monkeypatch):
    def forbidden(*args):
        pytest.fail('explicit D114 toolchain must not enumerate ambient agents')
    monkeypatch.setattr(subject, 'resource_names', forbidden)
    actual = subject.toolchain(native_shared=True)
    assert set(actual['resources']) == set(subject.NATIVE_SHARED_RESOURCES)
    assert len(actual['resources']) == 7
    assert {name for name in actual['resources'] if name.startswith('.claude/agents/')} == {
        '.claude/agents/d4d-provenance-guard.md', '.claude/agents/d4d-validator.md'}
    assert all(Path(value).is_file() for value in actual['resources'].values())
    assert subject.validate_toolchain(actual) == actual


@pytest.mark.parametrize('value', [None, 0, 1, 'true', [], {}])
def test_native_route_selection_cannot_be_implicit_truthiness(value):
    with pytest.raises(ValueError, match='explicit boolean'):
        subject.toolchain(native_shared=value)


def test_specificity_scanner_checks_every_exposed_native_markdown(tmp_path):
    tokens = scan.load_tokens(ROOT)
    exposed = subject.toolchain(native_shared=True)['resources']
    hits = []
    paths = sorted(path for path in exposed if path.endswith('.md'))
    assert len(paths) == 5
    for relative in paths:
        surface = scan.Surface(relative, ['native_agentic'], 'model_facing', 'live', 'D114 exposed text')
        hits.extend(scan.scan_file(ROOT, surface, tokens))
    violations = [hit for hit in hits if hit['category'] == 'gc_project']
    assert not violations, violations
    # Keep a positive token-detection control: absent hits are not a scanner skip.
    relative = '.claude/agents/d4d-provenance-guard.md'
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text(Path(exposed[relative]).read_text() + '\nAI_READI named-study contamination.\n')
    surface = scan.Surface(relative, ['native_agentic'], 'model_facing', 'live', 'D114 hostile control')
    found = scan.scan_file(tmp_path, surface, tokens)
    assert any(hit['category'] == 'gc_project' and hit['model_facing']
               and 'native_agentic' in hit['gates_in'] for hit in found)

