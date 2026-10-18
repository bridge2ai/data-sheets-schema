"""Opt-in disclosure joins exact rating bytes without changing score cohorts."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import report_semantic_comparison as consumer
from data_sheets_schema import model_disclosure as authority

BASELINE = json.loads((ROOT / "tests/fixtures/semantic_model_disclosure_default.json").read_text())


@pytest.fixture
def bound(tmp_path):
    input_path = tmp_path / 'input.yaml'
    input_path.write_text('id: example:one\ntitle: Example\n')
    digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
    rating, provenance = tmp_path / 'rating.json', tmp_path / 'provenance.yaml'
    doc = {'rubric': 'rubric10-semantic', 'version': '2.0', 'project': 'EXAMPLE',
           'method': 'method_label', 'label': 'run', 'd4d_file': str(input_path),
           'model': {'name': 'Display label', 'evaluator_model': 'claude-opus-5',
                     'evaluation_type': 'semantic_llm_judge'},
           'metadata': {'input_sha256': digest},
           'overall_score': {'total_points': 30, 'max_points': 50, 'adjusted_max_points': 45,
                             'excluded_max_points': 5},
           'elements': [{'id': 1, 'sub_elements': [{'id': '1.1', 'name': 'Scoped criterion',
                         'applicable': False, 'score': None}]}]}
    prov = {'run': {'project': 'EXAMPLE', 'method': 'method_label', 'label': 'run'},
            'model': {'model': 'claude-sonnet-4-5'},
            'outputs': {'full': {'path': str(input_path), 'bytes': input_path.stat().st_size,
                                 'sha256': digest}}}
    rating.write_text(json.dumps(doc)); provenance.write_text(yaml.safe_dump(prov))
    return rating, input_path, provenance, doc, prov


def binding(bound):
    return authority.GenerationBinding(*bound[:3])


def save(bound):
    bound[0].write_text(json.dumps(bound[3])); bound[2].write_text(yaml.safe_dump(bound[4]))


def opted(bound, paths=None, **kwargs):
    return consumer.report(paths or [bound[0]], disclosure_policy='declared-v1',
                           generation_bindings=[binding(bound)], **kwargs)


@pytest.mark.parametrize('case', BASELINE['cases'], ids=lambda case: case['name'])
def test_default_complete_output_is_byte_identical(case, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name, doc in case['files'].items():
        Path(name).write_text(json.dumps(doc))
    monkeypatch.setattr(authority, 'build_report', lambda *a, **k: pytest.fail('default invoked disclosure'))
    cohort = None if case['cohort'] is None else list(map(Path, case['cohort']))
    assert consumer.report(list(map(Path, case['paths'])), cohort) == case['expected']


def test_declared_rows_and_full_appendix_preserve_existing_score_and_cohort_text(bound):
    paths = [bound[0], bound[0]]
    before = {p: p.read_bytes() for p in bound[:3]}
    old = consumer.report(paths, cohort=[bound[0]])
    text = opted(bound, paths, cohort=[bound[0]])
    table = [line for line in text.splitlines() if line.startswith('| ')]
    assert 'Evaluator family | Generator | Generator family | Same family | Generation binding |' in table[0]
    assert sum('| claude | claude-sonnet-4-5 | claude | yes | associated |' in line for line in table) == 2
    assert 'Display label (evaluator claude-opus-5)' in text
    heading = '## Item discrimination'
    assert text[text.index(heading):].split('\n## Model disclosure', 1)[0].rstrip() == old[old.index(heading):].rstrip()
    for row in [line for line in old.splitlines() if line.startswith('| ' + str(bound[0]))]:
        assert row in text
    assert text.count('### Rating ') == 2
    for raw in before.values():
        assert hashlib.sha256(raw).hexdigest() in text
    assert 'not provider-authenticated' in text and 'none are pooled' in text
    assert r'binding\_checks' in text and r'association\_reasons' in text
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('generator,evaluator,kind,expected', [
    ('openai:gpt-5', 'claude-opus-5', 'semantic_llm_judge', 'no'),
    ('claude-opus-5', 'google/claude-sonnet-4', 'llm_as_judge', 'yes'),
    ('unknown-model', 'claude-opus-5', 'semantic_llm_judge', 'unknown'),
    ('claude-opus-5', 'claude-opus-5', 'rule_based_with_quality_heuristics', 'unknown'),
])
def test_existing_authority_controls_family_and_non_llm_meaning(bound, generator, evaluator, kind, expected):
    bound[4]['model']['model'] = generator
    bound[3]['model'].update(evaluator_model=evaluator, evaluation_type=kind); save(bound)
    row = next(line for line in opted(bound).splitlines() if line.startswith('| ' + str(bound[0])))
    assert f'| {expected} | associated |' in row


def test_unbound_and_conflicting_type_remain_unknown(bound):
    unbound = consumer.report([bound[0]], disclosure_policy='declared-v1')
    assert '| claude | unknown | unknown | unknown | unknown |' in unbound
    bound[3]['evaluation_type'] = 'rule_based_with_quality_heuristics'; save(bound)
    assert '| unknown | claude-sonnet-4-5 | claude | unknown | associated |' in opted(bound)


@pytest.mark.parametrize('policy', [False, 1, [], {}, '', 'declared-v2'])
def test_unknown_policy_is_refused(bound, policy):
    with pytest.raises(ValueError, match='unknown model disclosure policy'):
        consumer.report([bound[0]], disclosure_policy=policy)


def test_binding_options_require_explicit_policy(bound):
    with pytest.raises(ValueError, match='explicit disclosure policy'):
        consumer.report([bound[0]], generation_bindings=[binding(bound)])
    with pytest.raises(ValueError, match='explicit disclosure policy'):
        consumer.report([bound[0]], disclosure_root=bound[0].parent)


@pytest.mark.parametrize('change', ['hash', 'size', 'run', 'path', 'malformed-type'])
def test_supplied_binding_contradictions_keep_shared_refusals(bound, change):
    if change == 'hash': bound[3]['metadata']['input_sha256'] = '0' * 64
    elif change == 'size': bound[4]['outputs']['full']['bytes'] += 1
    elif change == 'run': bound[4]['run']['project'] = 'OTHER'
    elif change == 'path': bound[4]['outputs']['full']['path'] = str(bound[2])
    else: bound[3]['metadata'] = []
    save(bound)
    with pytest.raises(ValueError): opted(bound)


def test_same_basename_is_not_a_binding_and_repeats_remain_rows(bound, tmp_path):
    other = tmp_path / 'other' / bound[0].name; other.parent.mkdir(); other.write_bytes(bound[0].read_bytes())
    text = opted(bound, [bound[0], other, bound[0]])
    rows = [line for line in text.splitlines() if line.startswith('| ' + str(tmp_path))]
    assert len(rows) == 3
    assert '| yes | associated |' in rows[0] and '| yes | associated |' in rows[2]
    assert '| unknown | unknown | unknown | unknown |' in rows[1]
    with pytest.raises(ValueError, match='outside the report'):
        opted(bound, [other])
    with pytest.raises(ValueError, match='more than one binding'):
        consumer.report([bound[0]], disclosure_policy='declared-v1',
                        generation_bindings=[binding(bound), binding(bound)])


@pytest.mark.parametrize('change', ['bytes', 'same-sized-bytes', 'symlink-target'])
def test_changed_rating_between_disclosure_and_scoring_is_refused(bound, monkeypatch, change):
    original = authority.build_report
    def capture_then_change(*args, **kwargs):
        result = original(*args, **kwargs)
        raw = bound[0].read_bytes()
        if change == 'bytes': bound[0].write_bytes(raw + b'\n')
        elif change == 'same-sized-bytes': bound[0].write_bytes(raw.replace(b'30', b'31', 1))
        else:
            replacement = bound[0].with_name('replacement.json'); replacement.write_bytes(raw)
            bound[0].unlink(); bound[0].symlink_to(replacement)
        return result
    monkeypatch.setattr(authority, 'build_report', capture_then_change)
    with pytest.raises(ValueError, match='changed between disclosure and score capture'):
        opted(bound)


def invoke(monkeypatch, bound, output, *extra):
    monkeypatch.setattr(sys, 'argv', ['report_semantic_comparison', str(bound[0]), '--output', str(output),
                       '--model-disclosure', 'declared-v1', '--generation-binding',
                       *map(str, bound[:3]), *map(str, extra)])
    return consumer.main()


def test_actual_cli_writes_fresh_report_and_keeps_default_bytes(bound, tmp_path):
    output = tmp_path / 'new.md'
    argv = [sys.executable, str(ROOT / 'scripts/report_semantic_comparison.py'), str(bound[0]),
            '--output', str(output)]
    import os
    env = {**os.environ, 'PYTHONPATH': str(ROOT / 'src'), 'PYTHONDONTWRITEBYTECODE': '1'}
    run = subprocess.run(argv, capture_output=True, text=True, env=env)
    assert run.returncode == 0, run.stderr
    assert output.read_text() == consumer.report([bound[0]])
    new = tmp_path / 'disclosed.md'; argv[argv.index(str(output))] = str(new)
    run = subprocess.run([*argv, '--model-disclosure', 'declared-v1', '--generation-binding',
                          *map(str, bound[:3])], capture_output=True, text=True, env=env)
    assert run.returncode == 0, run.stderr
    assert new.read_text() == opted(bound)


@pytest.mark.parametrize('target', ['evaluation', 'input', 'provenance', 'context', 'evidence'])
@pytest.mark.parametrize('alias', ['direct', 'hardlink', 'symlink'])
def test_new_mode_never_overwrites_any_input_alias(bound, tmp_path, monkeypatch, target, alias):
    context, evidence = tmp_path / 'context.yaml', tmp_path / 'evidence.yaml'
    context.write_text('version: example\n'); evidence.write_text('id: example:one\n')
    source = dict(zip(('evaluation', 'input', 'provenance'), bound[:3]))
    source.update(context=context, evidence=evidence)
    files = {p: p.read_bytes() for p in source.values()}
    output = source[target]
    if alias != 'direct':
        output = tmp_path / 'alias.md'
        if alias == 'hardlink': output.hardlink_to(source[target])
        else: output.symlink_to(source[target])
    with pytest.raises(SystemExit) as exc:
        invoke(monkeypatch, bound, output, '--evidence-input', bound[0], evidence,
               '--evidence-context', bound[0], context)
    assert exc.value.code == 2
    assert {p: p.read_bytes() for p in files} == files


def test_fresh_publication_refuses_existing_file_and_postcheck_race(bound, tmp_path, monkeypatch):
    output = tmp_path / 'existing.md'; output.write_text('preserve')
    with pytest.raises(SystemExit): invoke(monkeypatch, bound, output)
    assert output.read_text() == 'preserve'
    raced = tmp_path / 'raced.md'; real = consumer.report
    def render_then_link(*args, **kwargs):
        text = real(*args, **kwargs); raced.hardlink_to(bound[1]); return text
    original = bound[1].read_bytes(); monkeypatch.setattr(consumer, 'report', render_then_link)
    with pytest.raises(SystemExit): invoke(monkeypatch, bound, raced)
    assert bound[1].read_bytes() == original


def test_bad_binding_is_refused_before_new_output(bound, tmp_path, monkeypatch):
    bound[4]['outputs']['full']['bytes'] += 1; save(bound)
    output = tmp_path / 'never-created.md'
    with pytest.raises(SystemExit): invoke(monkeypatch, bound, output)
    assert not output.exists()


def test_frozen_cborg_report_import_does_not_use_live_disclosure_consumer(bound, monkeypatch):
    import reference_rescore_cborg
    runner = reference_rescore_cborg.load_runner()
    frozen = runner.__dict__['__builtins__']['__import__']('report_semantic_comparison', fromlist=['report'])
    monkeypatch.setattr(consumer, 'report', lambda *a, **k: pytest.fail('frozen replay imported current report'))
    text = frozen.report([bound[0]])
    assert 'Fixed: 30/50' in text and 'Model disclosure' not in text
