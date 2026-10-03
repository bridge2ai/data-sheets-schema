"""Opt-in raw-rating disclosure must not alter legacy summary measurements."""
from copy import deepcopy
from datetime import datetime
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import summarize_rubric20_results as mod
from data_sheets_schema import model_disclosure as authority
from tests.test_evaluation.test_summarize_rubric20_results import _adjusted, _evaluation

BASELINE = json.loads((ROOT / 'tests/fixtures/rubric20_model_disclosure_default.json').read_text())


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls.fromisoformat(BASELINE['clock']).replace(tzinfo=tz)


@pytest.fixture
def sample(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, 'datetime', Clock)
    root = tmp_path / 'evaluations'; (root / 'concatenated').mkdir(parents=True)
    source, provenance = tmp_path / 'input.yaml', tmp_path / 'provenance.yaml'
    source.write_text('id: example:one\ntitle: Example\n')
    doc = _evaluation('EXAMPLE', str(source), 'mapping')
    doc.pop('evaluation_type'); doc.update(type='concatenated', label='example-run')
    doc['model'] = {'name': 'claude-fable-5', 'evaluation_type': 'llm_as_judge'}
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    doc['metadata'] = {'input_sha256': digest}
    rating = root / 'concatenated/rating_evaluation.json'; rating.write_text(json.dumps(doc))
    prov = {'run': {k: doc[k] for k in ('project', 'method', 'label')},
            'model': {'model': 'claude-sonnet-4-5'},
            'outputs': {'full': {'path': str(source), 'bytes': source.stat().st_size, 'sha256': digest}}}
    provenance.write_text(yaml.safe_dump(prov))
    return {'root': root, 'rating': rating, 'input': source, 'provenance': provenance,
            'doc': doc, 'prov': prov, 'out': tmp_path / 'new-summary'}


def binding(s):
    return authority.GenerationBinding(s['rating'], s['input'], s['provenance'])


def run(s, *, bindings=True):
    return mod.write_disclosed_summaries(s['root'], s['out'],
                                        generation_bindings=[binding(s)] if bindings else ())


def save(s):
    s['rating'].write_text(json.dumps(s['doc']))
    s['provenance'].write_text(yaml.safe_dump(s['prov']))


def rows(s):
    with (s['out'] / 'all_scores.csv').open(newline='') as stream:
        return list(csv.DictReader(stream))


def default_outputs(results):
    return {'all_scores.csv': mod._csv_summary_text(results),
            'summary_table.md': mod._markdown_table_text(results),
            'summary_report.md': mod._detailed_report_text(results)}


def test_actual_default_producers_and_all_forty_original_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, 'datetime', Clock)
    before = {p: (ROOT / p).read_bytes() for p in BASELINE['input_sha256']}
    assert {p: hashlib.sha256(raw).hexdigest() for p, raw in before.items()} == BASELINE['input_sha256']
    root = tmp_path / 'rubric20'; (root / 'concatenated').mkdir(parents=True)
    for p, raw in before.items():
        if '/rubric20/' in p: (root / 'concatenated' / Path(p).name).write_bytes(raw)
    monkeypatch.setattr(mod, 'EVAL_DIR', root)
    results = mod.load_evaluation_results(); original = deepcopy(results)
    mod.create_csv_summary(results); mod.create_markdown_table(results); mod.create_detailed_report(results)
    for name, expected in BASELINE['rubric20_outputs'].items():
        assert (root / name).read_bytes() == expected.encode()
    output = tmp_path / 'disclosed'
    assert mod.write_disclosed_summaries(root, output)['ratings'] == 20
    with (output / 'all_scores.csv').open(newline='') as stream: actual = list(csv.DictReader(stream))
    old = list(csv.DictReader(BASELINE['rubric20_outputs']['all_scores.csv'].splitlines()))
    assert [{k: r[k] for k in old[0]} for r in actual] == old
    assert sum(r['evaluator_family'] == 'claude' for r in actual) == 8
    assert sum(r['evaluator_family'] == 'unknown' for r in actual) == 12
    assert all(r['generator'] == r['same_family'] == 'unknown' for r in actual)
    for name in ('summary_table.md', 'summary_report.md'):
        text = (output / name).read_text()
        assert text.startswith(BASELINE['rubric20_outputs'][name])
        assert text.count('### Rating ') == 20
    assert results == original
    assert {p: (ROOT / p).read_bytes() for p in before} == before


def test_raw_types_and_exact_cohort_membership_are_separate_from_score_dicts(sample, monkeypatch):
    s = sample; monkeypatch.setattr(mod, 'EVAL_DIR', s['root'])
    results = mod.load_evaluation_results(); original = deepcopy(results)
    expected = default_outputs(results)
    source_bytes = {s[k]: s[k].read_bytes() for k in ('rating', 'input', 'provenance')}
    run(s)
    row = rows(s)[0]
    assert row['evaluator_family'] == row['generator_family'] == 'claude'
    assert row['same_family'] == 'yes' and row['generation_binding'] == 'associated'
    assert row['evaluation_resolved_path'] == str(s['rating'].resolve())
    assert row['evaluation_sha256'] == hashlib.sha256(source_bytes[s['rating']]).hexdigest()
    assert row['type'] == 'concatenated' and row['model_disclosure_policy'] == authority.VERSION
    for name in ('summary_table.md', 'summary_report.md'):
        text = (s['out'] / name).read_text()
        assert text.startswith(expected[name])
        assert mod.cell(json.dumps(mod.cohort_key(results[0])._asdict(), sort_keys=True, ensure_ascii=False)) in text
        assert 'not provider-authenticated' in text
        assert 'llm\\_as\\_judge' in text and 'evaluation\\_type\\_conflict | False' in text
    assert results == original and {p: p.read_bytes() for p in source_bytes} == source_bytes


@pytest.mark.parametrize('kind', ['cross-family', 'non-llm', 'genuine-type-conflict', 'unknown-identifier', 'unbound'])
def test_shared_family_authority_is_preserved(sample, kind):
    s = sample
    if kind == 'cross-family': s['prov']['model']['model'] = 'openai:gpt-5'
    elif kind == 'non-llm': s['doc']['model']['evaluation_type'] = 'rule_based_with_quality_heuristics'
    elif kind == 'genuine-type-conflict': s['doc']['evaluation_type'] = 'rule_based_with_quality_heuristics'
    elif kind == 'unknown-identifier': s['prov']['model']['model'] = 'local-unclassified'
    save(s); run(s, bindings=kind != 'unbound')
    expected = authority.build_report([s['rating']], bindings=[] if kind == 'unbound' else [binding(s)])['rows'][0]
    row = rows(s)[0]
    for key in ('evaluator_family', 'generator', 'generator_family', 'same_family'):
        assert row[key] == ('unknown' if expected[key] is None else expected[key])
    assert row['same_family'] == ('no' if kind == 'cross-family' else 'unknown')


def test_same_basenames_repeated_records_and_aliases_remain_separate(sample):
    s = sample
    for folder in ('one', 'two'):
        directory = s['root'] / 'individual' / folder; directory.mkdir(parents=True)
        (directory / s['rating'].name).write_bytes(s['rating'].read_bytes())
    alias = s['root'] / 'concatenated/alias_evaluation.json'; alias.symlink_to(s['rating'])
    run(s); result = rows(s)
    assert len(result) == 4 and len({r['evaluation_file'] for r in result}) == 4
    assert [r['disclosure_rating'] for r in result] == ['1', '2', '3', '4']
    assert [r['generation_binding'] for r in result] == ['associated', 'associated', 'unknown', 'unknown']
    assert {r['type'] for r in result} == {'individual', 'concatenated'}
    assert (s['out'] / 'summary_report.md').read_text().count('### Rating ') == 4


@pytest.mark.parametrize('change', ['hash', 'bytes', 'run', 'path', 'duplicate-key', 'duplicate-binding', 'outside-binding'])
def test_contradictory_evidence_refuses_before_directory_creation(sample, change):
    s = sample; bindings = [binding(s)]
    if change == 'hash': s['doc']['metadata']['input_sha256'] = '0' * 64
    elif change == 'bytes': s['prov']['outputs']['full']['bytes'] += 1
    elif change == 'run': s['prov']['run']['project'] = 'OTHER'
    elif change == 'path': s['prov']['outputs']['full']['path'] = str(s['rating'])
    elif change == 'duplicate-binding': bindings *= 2
    elif change == 'outside-binding': bindings = [authority.GenerationBinding(s['input'], s['input'], s['provenance'])]
    save(s)
    if change == 'duplicate-key': s['rating'].write_text(s['rating'].read_text().replace('"rubric":', '"rubric":"rubric10","rubric":', 1))
    with pytest.raises(ValueError): mod.write_disclosed_summaries(s['root'], s['out'], generation_bindings=bindings)
    assert not s['out'].exists()


@pytest.mark.parametrize('change', ['bytes', 'symlink-target'])
def test_changed_evaluation_between_captures_refuses(sample, monkeypatch, change):
    s = sample; original = authority.build_report
    def mutate(*a, **k):
        raw = s['rating'].read_bytes()
        if change == 'bytes': s['rating'].write_bytes(raw + b'\n')
        else:
            other = s['rating'].with_name('replacement.json'); other.write_bytes(raw)
            s['rating'].unlink(); s['rating'].symlink_to(other)
        return original(*a, **k)
    monkeypatch.setattr(authority, 'build_report', mutate)
    with pytest.raises(ValueError, match='changed between score and disclosure'): run(s)
    assert not s['out'].exists()


@pytest.mark.parametrize('target', ['existing-directory', 'symlink-directory', 'evaluation-file', 'provenance-file'])
def test_existing_destinations_refuse_without_replacing_sources(sample, target):
    s = sample; before = {s[k]: s[k].read_bytes() for k in ('rating', 'input', 'provenance')}
    if target == 'existing-directory': s['out'].mkdir()
    elif target == 'symlink-directory': s['out'].symlink_to(s['root'])
    else: s['out'] = s['rating'] if target == 'evaluation-file' else s['provenance']
    with pytest.raises(ValueError, match='directory must be new'): run(s)
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('alias', ['hardlink', 'symlink'])
def test_publication_race_retains_partial_evidence_and_protects_input(sample, monkeypatch, alias):
    s = sample; original = Path.mkdir; before = s['input'].read_bytes()
    def race(path, *a, **k):
        result = original(path, *a, **k)
        if path == s['out']:
            p = path / 'summary_table.md'
            (p.hardlink_to if alias == 'hardlink' else p.symlink_to)(s['input'])
        return result
    monkeypatch.setattr(Path, 'mkdir', race)
    with pytest.raises(FileExistsError): run(s)
    assert s['input'].read_bytes() == before
    assert (s['out'] / 'all_scores.csv').exists()  # failed publication evidence is retained
    assert not (s['out'] / 'summary_report.md').exists()


def test_default_csv_validation_still_precedes_opening_existing_output(sample, monkeypatch):
    s = sample; monkeypatch.setattr(mod, 'EVAL_DIR', s['root'])
    output = s['root'] / 'all_scores.csv'; output.write_text('preserve')
    damaged = deepcopy(s['doc']); damaged['overall_score']['max_points'] = -1
    with pytest.raises(ValueError): mod.create_csv_summary([damaged])
    assert output.read_text() == 'preserve'


@pytest.mark.parametrize('kind', ['individual', 'concatenated'])
def test_opt_in_preserves_adjustment_exclusions_repeats_and_membership(tmp_path, monkeypatch, kind):
    monkeypatch.setattr(mod, 'datetime', Clock)
    root, output = tmp_path / 'evaluations', tmp_path / 'disclosed'
    docs = [_adjusted({1}, filename='left', kind=kind),
            _adjusted({2}, filename='right', kind=kind),
            _adjusted(set(range(1, 21)), total=0, filename='undefined', kind=kind, api=True),
            _adjusted({1}, filename='unrecorded', kind=kind)]
    docs[-1]['categories'] = []  # adjusted maximum alone does not prove exclusions
    repeated = deepcopy(docs[0]); repeated['_evaluation_file'] = f'{kind}/repeat_evaluation.json'
    docs.append(repeated)
    for doc in docs:
        path = root / doc.pop('_evaluation_file'); path.parent.mkdir(parents=True, exist_ok=True)
        doc['type'] = doc.pop('evaluation_type')
        path.write_text(json.dumps(doc))
    dated = root / 'concatenated/dated/excluded_evaluation.json'
    dated.parent.mkdir(parents=True, exist_ok=True); dated.write_text(json.dumps(docs[0]))
    monkeypatch.setattr(mod, 'EVAL_DIR', root)
    loaded = mod.load_evaluation_results(); original = deepcopy(loaded)
    expected = default_outputs(loaded)
    assert len(loaded) == 5 and len(mod.summary_cohorts(loaded)) == 4
    before = {p: p.read_bytes() for p in root.rglob('*.json')}
    mod.write_disclosed_summaries(root, output)
    with (output / 'all_scores.csv').open(newline='') as stream: actual = list(csv.DictReader(stream))
    old = list(csv.DictReader(expected['all_scores.csv'].splitlines()))
    assert [{k: r[k] for k in old[0]} for r in actual] == old
    assert {r['excluded_items'] for r in actual} >= {'["Q1"]', '["Q2"]', 'null'}
    undefined = next(r for r in actual if 'undefined' in r['evaluation_file'])
    assert undefined['adjusted_max_score'] == '0' and undefined['adjusted_percentage'] == ''
    for name in ('summary_table.md', 'summary_report.md'):
        text = (output / name).read_text()
        assert text.startswith(expected[name]) and text.count('### Rating ') == 5
        assert 'dated/excluded_evaluation.json' not in text
        assert sum(text.count(mod.cell(json.dumps(mod.cohort_key(r)._asdict(), sort_keys=True,
                                                ensure_ascii=False))) for r in loaded) == 7
    assert 'Rated more than once' in expected['summary_report.md']
    assert 'Withheld: adjusted basis or excluded-item identities are unrecorded' in expected['summary_report.md']
    assert loaded == original and {p: p.read_bytes() for p in before} == before


def test_explicit_recorded_path_root_is_forwarded_to_shared_authority(sample):
    s = sample
    s['doc']['d4d_file'] = 'relative/input.yaml'
    s['prov']['outputs']['full']['path'] = 'relative/input.yaml'
    source_root = s['input'].parent / 'recorded-root'; (source_root / 'relative').mkdir(parents=True)
    (source_root / 'relative/input.yaml').symlink_to(s['input'])
    save(s)
    mod.write_disclosed_summaries(s['root'], s['out'], generation_bindings=[binding(s)],
                                  disclosure_root=source_root)
    assert rows(s)[0]['generation_binding'] == 'associated'


@pytest.mark.parametrize('damage', ['nonfinite-json', 'duplicate-provenance', 'malformed-provenance'])
def test_strict_raw_parsers_refuse_before_publication(sample, damage):
    s = sample
    if damage == 'nonfinite-json':
        s['doc']['nonfinite'] = float('nan'); save(s)
    elif damage == 'duplicate-provenance':
        s['provenance'].write_text(s['provenance'].read_text() + '\nmodel: {}\n')
    else:
        s['provenance'].write_text('outputs: [unterminated')
    with pytest.raises(ValueError): run(s)
    assert not s['out'].exists()


def test_no_option_cli_uses_the_original_writer_entrypoint(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(mod, '_legacy_main', lambda: sentinel)
    assert mod.main([]) is sentinel


@pytest.mark.parametrize('args', [['--output-dir', 'new'], ['--evaluation-root', 'missing'],
                                  ['--model-disclosure', 'declared-v1'], ['--model-disclosure', 'unknown']])
def test_cli_requires_explicit_selector_and_destination(args, monkeypatch):
    monkeypatch.setattr(mod, '_legacy_main', lambda: pytest.fail('invalid disclosure options entered default writers'))
    with pytest.raises(SystemExit) as exc: mod.main(args)
    assert exc.value.code == 2


def test_actual_cli_only_writes_fresh_opt_in_outputs(sample):
    s = sample; before = {s[k]: s[k].read_bytes() for k in ('rating', 'input', 'provenance')}
    proc = subprocess.run([sys.executable, str(ROOT / 'scripts/summarize_rubric20_results.py'),
        '--model-disclosure', 'declared-v1', '--evaluation-root', str(s['root']), '--output-dir', str(s['out']),
        '--generation-binding', str(s['rating']), str(s['input']), str(s['provenance'])],
        env={**os.environ, 'PYTHONPATH': str(ROOT / 'src'), 'PYTHONDONTWRITEBYTECODE': '1'}, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)['ratings'] == 1 and rows(s)[0]['same_family'] == 'yes'
    assert {p: p.read_bytes() for p in before} == before
