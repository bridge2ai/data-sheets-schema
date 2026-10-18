"""Opt-in family evidence must preserve legacy rubric10 selections and bytes."""
from copy import deepcopy
from datetime import datetime
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import summarize_rubric10_results as mod
from data_sheets_schema import model_disclosure as authority

BASELINE = json.loads((ROOT / 'tests/fixtures/rubric10_model_disclosure_default.json').read_text())


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls.fromisoformat(BASELINE['clock']).replace(tzinfo=tz)


def record(source, score=40, **updates):
    remaining = score
    elements = []
    for index in range(1, 11):
        value = min(remaining, 5); remaining -= value
        elements.append({'id': index, 'name': f'Element {index}', 'element_score': value,
                         'element_max': 5,
                         'sub_elements': [{'name': f's{n}', 'score': int(n < value)} for n in range(5)]})
    assert remaining == 0
    result = {'rubric': 'rubric10', 'version': '1.0', 'project': 'AI_READI', 'method': 'gpt5',
              'type': 'concatenated', 'label': 'fixture-run', 'd4d_file': str(source),
              'model': {'name': 'claude-fable-5', 'evaluation_type': 'llm_as_judge'},
              'overall_score': {'total_points': score, 'max_points': 50, 'percentage': 2 * score},
              'elements': elements}
    result.update(updates)
    return result


@pytest.fixture
def sample(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, 'datetime', Clock)
    root = tmp_path / 'evaluations'; (root / 'concatenated').mkdir(parents=True)
    source, provenance = tmp_path / 'input.yaml', tmp_path / 'provenance.yaml'
    source.write_text('id: example:one\ntitle: Example\n')
    doc = record(source)
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


def outputs(results):
    return {'all_scores.csv': mod._csv_summary_text(results),
            'summary_table.md': mod._markdown_table_text(results),
            'summary_report.md': mod._detailed_report_text(results)}


def recorded_discovery(monkeypatch, root, names):
    """Replay a captured parent order without sorting the production loader.

    Path.glob order differs across filesystems. The legacy stable percentage
    sort preserves that order for ties, so exact parent bytes require the
    same input enumeration (#4326).
    """
    directory = root / 'concatenated'
    expected = [directory / name for name in names]
    assert len(expected) == len(set(expected))
    original = Path.glob

    def glob(path, pattern):
        found = list(original(path, pattern))
        if path == directory and pattern == '*_evaluation.json':
            assert set(found) == set(expected)
            return iter(expected)
        return iter(found)

    monkeypatch.setattr(Path, 'glob', glob)


def test_actual_parent_output_bytes_and_all_forty_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, 'datetime', Clock)
    before = {p: (ROOT / p).read_bytes() for p in BASELINE['input_sha256']}
    assert {p: hashlib.sha256(raw).hexdigest() for p, raw in before.items()} == BASELINE['input_sha256']
    root = tmp_path / 'rubric10'; (root / 'concatenated').mkdir(parents=True)
    for p, raw in before.items():
        if '/rubric10/' in p: (root / 'concatenated' / Path(p).name).write_bytes(raw)
    recorded_discovery(monkeypatch, root, BASELINE['rubric10_discovery_order'])
    monkeypatch.setattr(mod, 'EVAL_DIR', root)
    results = mod.load_evaluation_results(); original = deepcopy(results)
    mod.create_csv_summary(results); mod.create_markdown_table(results); mod.create_detailed_report(results)
    for name, expected in BASELINE['rubric10_outputs'].items():
        assert (root / name).read_bytes() == expected.encode()
    output = tmp_path / 'disclosed'; assert mod.write_disclosed_summaries(root, output)['ratings'] == 20
    with (output / 'all_scores.csv').open(newline='') as stream: actual = list(csv.DictReader(stream))
    old = list(csv.DictReader(io.StringIO(BASELINE['rubric10_outputs']['all_scores.csv'], newline='')))
    assert [{k: r[k] for k in old[0]} for r in actual] == old
    assert sum(r['evaluator_family'] == 'claude' for r in actual) == 8
    assert sum(r['evaluator_family'] == 'unknown' for r in actual) == 12
    assert all(r['generator'] == r['same_family'] == 'unknown' for r in actual)
    for name in ('summary_table.md', 'summary_report.md'):
        text = (output / name).read_text()
        assert text.startswith(BASELINE['rubric10_outputs'][name]) and text.count('### Rating ') == 20
    assert results == original and not any('_evaluation_file' in r for r in results)
    assert {p: (ROOT / p).read_bytes() for p in before} == before


@pytest.mark.parametrize('order', ['name_ascending', 'name_descending', 'ci_observed_ties'])
def test_alternate_discovery_orders_preserve_actual_parent_bytes(tmp_path, monkeypatch, order):
    """Hashes were captured by running the pinned parent, not this renderer."""
    monkeypatch.setattr(mod, 'datetime', Clock)
    root = tmp_path / 'rubric10'; (root / 'concatenated').mkdir(parents=True)
    for path, digest in BASELINE['input_sha256'].items():
        if '/rubric10/' in path:
            raw = (ROOT / path).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == digest
            (root / 'concatenated' / Path(path).name).write_bytes(raw)
    capture = BASELINE['alternate_discovery_parity'][order]
    recorded_discovery(monkeypatch, root, capture['order'])
    monkeypatch.setattr(mod, 'EVAL_DIR', root)
    results = mod.load_evaluation_results()
    expected_files = [json.loads((root / 'concatenated' / name).read_bytes())['d4d_file']
                      for name in capture['order']]
    assert [row['d4d_file'] for row in results] == expected_files
    mod.create_csv_summary(results); mod.create_markdown_table(results); mod.create_detailed_report(results)
    legacy = {name: (root / name).read_bytes() for name in capture['output_sha256']}
    assert {name: hashlib.sha256(raw).hexdigest() for name, raw in legacy.items()} == capture['output_sha256']
    disclosed = tmp_path / 'disclosed'
    assert mod.write_disclosed_summaries(root, disclosed)['ratings'] == len(capture['order'])
    for name in ('summary_table.md', 'summary_report.md'):
        assert (disclosed / name).read_bytes().startswith(legacy[name])
    old = list(csv.DictReader(io.StringIO(legacy['all_scores.csv'].decode(), newline='')))
    with (disclosed / 'all_scores.csv').open(newline='') as stream:
        actual = list(csv.DictReader(stream))
    assert [{key: row[key] for key in old[0]} for row in actual] == old


def test_raw_type_declarations_and_occurrence_identity_do_not_enter_scores(sample, monkeypatch):
    s = sample; monkeypatch.setattr(mod, 'EVAL_DIR', s['root'])
    legacy = mod.load_evaluation_results(); original = deepcopy(legacy); expected = outputs(legacy)
    source_bytes = {s[k]: s[k].read_bytes() for k in ('rating', 'input', 'provenance')}
    run(s); row = rows(s)[0]
    assert row['evaluator_family'] == row['generator_family'] == 'claude' and row['same_family'] == 'yes'
    assert row['generation_binding'] == 'associated' and row['type'] == 'concatenated'
    assert row['evaluation_file'] == 'concatenated/rating_evaluation.json'
    assert row['evaluation_resolved_path'] == str(s['rating'].resolve())
    assert row['evaluation_sha256'] == hashlib.sha256(source_bytes[s['rating']]).hexdigest()
    for name in ('summary_table.md', 'summary_report.md'):
        text = (s['out'] / name).read_text()
        assert text.startswith(expected[name]) and 'selected_first_rating' in text
        assert 'not provider-authenticated' in text and 'evaluation\\_type\\_conflict | False' in text
    assert legacy == original and {p: p.read_bytes() for p in source_bytes} == source_bytes


@pytest.mark.parametrize('kind', ['cross-family', 'non-llm', 'genuine-type-conflict', 'unknown-identifier', 'unbound'])
def test_declared_labels_follow_shared_authority(sample, kind):
    s = sample
    if kind == 'cross-family': s['prov']['model']['model'] = 'openai:gpt-5'
    elif kind == 'non-llm': s['doc']['model']['evaluation_type'] = 'rule_based_with_quality_heuristics'
    elif kind == 'genuine-type-conflict': s['doc']['evaluation_type'] = 'rule_based_with_quality_heuristics'
    elif kind == 'unknown-identifier': s['prov']['model']['model'] = 'unclassified-local'
    save(s); run(s, bindings=kind != 'unbound')
    expected = authority.build_report([s['rating']], bindings=[] if kind == 'unbound' else [binding(s)])['rows'][0]
    row = rows(s)[0]
    for key in ('evaluator_family', 'generator', 'generator_family', 'same_family'):
        assert row[key] == ('unknown' if expected[key] is None else expected[key])
    assert row['same_family'] == ('no' if kind == 'cross-family' else 'unknown')


@pytest.mark.parametrize('alias_kind', ['symlink', 'hardlink'])
def test_repeated_same_basenames_and_aliases_are_distinct_occurrences(sample, alias_kind, monkeypatch):
    s = sample
    for folder in ('one', 'two'):
        directory = s['root'] / 'individual' / folder; directory.mkdir(parents=True)
        (directory / s['rating'].name).write_bytes(s['rating'].read_bytes())
    alias = s['root'] / 'concatenated/alias_evaluation.json'
    (alias.symlink_to if alias_kind == 'symlink' else alias.hardlink_to)(s['rating'])
    monkeypatch.setattr(mod, 'EVAL_DIR', s['root'])
    loaded = mod.load_evaluation_results(); captured, report, links = mod._disclosed_inputs(s['root'], [binding(s)], None)
    assert captured == loaded and len(links) == 4
    expected = outputs(loaded); run(s); actual = rows(s)
    assert len(actual) == len({r['evaluation_file'] for r in actual}) == 4
    assert len({r['disclosure_rating'] for r in actual}) == 4
    # Symlink identity resolves to the bound rating; a different hardlink path is not that binding.
    assert sum(r['generation_binding'] == 'associated' for r in actual) == (2 if alias_kind == 'symlink' else 1)
    old = list(csv.DictReader(io.StringIO(expected['all_scores.csv'], newline='')))
    assert [{k: r[k] for k in old[0]} for r in actual] == old
    membership = mod._membership(captured, links)
    assert sum(r['concatenated_table'] == 'selected_first_rating' for r in membership) == 1
    assert sum(r['concatenated_table'] == 'unshown_repeat' for r in membership) == 1
    assert sum(r['individual_table'] == 'included_in_legacy_average' for r in membership) == 2
    for row in membership:
        csv_row = actual[row['csv_row'] - 1]
        assert csv_row['evaluation_file'] == row['evaluation_file']
        assert int(csv_row['disclosure_rating']) == row['disclosure_rating']
    assert (s['out'] / 'summary_table.md').read_text().startswith(expected['summary_table.md'])


def test_legacy_selection_first_top20_ties_and_unshown_membership(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, 'datetime', Clock)
    root = tmp_path / 'evaluations'; (root / 'concatenated').mkdir(parents=True)
    # Creation order deliberately differs from lexical order; ties must follow the old loader.
    for n in reversed(range(22)):
        doc = record('same.yaml', score=40, label=f'repeat-{n}')
        (root / f'concatenated/rating_{n:02d}_evaluation.json').write_text(json.dumps(doc))
    cases = [('concatenated/unlisted_evaluation.json', record('unlisted.yaml', project='NEW', method='new')),
             ('individual/nested/rating_evaluation.json', record('one.yaml', score=30, type='individual')),
             ('individual/unlisted_evaluation.json', record('two.yaml', score=10, method='unlisted', type='individual'))]
    for name, doc in cases:
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(doc))
    dated = root / 'concatenated/dated/excluded_evaluation.json'; dated.parent.mkdir(); dated.write_text(json.dumps(cases[0][1]))
    monkeypatch.setattr(mod, 'EVAL_DIR', root)
    loaded = mod.load_evaluation_results(); preserved = deepcopy(loaded)
    captured, report, links = mod._disclosed_inputs(root, (), None); assert captured == loaded
    expected = outputs(loaded); output = tmp_path / 'disclosed';mod.write_disclosed_summaries(root, output)
    membership = mod._membership(captured, links)
    assert len(membership) == 25 and sum(r['concatenated_table'] == 'unshown_repeat' for r in membership) == 21
    assert sum(r['concatenated_table'] == 'selected_first_rating' for r in membership) == 1
    assert sum(r['concatenated_table'] == 'unshown_project_or_method' for r in membership) == 1
    assert sum(r['individual_table'] == 'included_in_legacy_average' for r in membership) == 1
    assert sum(r['individual_table'] == 'unshown_project_or_method' for r in membership) == 1
    assert sorted(r['top_rank'] for r in membership if r['top_rank']) == list(range(1, 21))
    assert sum(r['top_performers'] == 'unshown_beyond_top20' for r in membership) == 3
    assert sum(r['top_performers'] == 'below_threshold' for r in membership) == 2
    first = next(r for r in captured if r['evaluation_type'] == 'concatenated' and r['project'] == 'AI_READI')
    selected = next(r for r in membership if r['concatenated_table'] == 'selected_first_rating')
    assert selected['evaluation_file'] == links[id(first)][0]['evaluation_file']
    for name in ('summary_table.md', 'summary_report.md'):
        text = (output / name).read_text();assert text.startswith(expected[name])
        assert text.count('### Rating ') == 25 and 'dated/excluded_evaluation.json' not in text
    assert loaded == preserved


@pytest.mark.parametrize('damage', ['hash', 'bytes', 'run', 'path', 'duplicate-json', 'nonfinite-json',
                                    'duplicate-provenance', 'malformed-provenance', 'duplicate-binding', 'outside-binding'])
def test_contradictory_or_malformed_evidence_refuses_before_creation(sample, damage):
    s = sample; bindings = [binding(s)]
    if damage == 'hash': s['doc']['metadata']['input_sha256'] = '0' * 64
    elif damage == 'bytes': s['prov']['outputs']['full']['bytes'] += 1
    elif damage == 'run': s['prov']['run']['project'] = 'OTHER'
    elif damage == 'path': s['prov']['outputs']['full']['path'] = str(s['rating'])
    elif damage == 'nonfinite-json': s['doc']['nonfinite'] = float('nan')
    elif damage == 'duplicate-binding': bindings *= 2
    elif damage == 'outside-binding': bindings = [authority.GenerationBinding(s['input'], s['input'], s['provenance'])]
    save(s)
    if damage == 'duplicate-json': s['rating'].write_text(s['rating'].read_text().replace('"rubric":', '"rubric":"rubric20","rubric":', 1))
    elif damage == 'duplicate-provenance': s['provenance'].write_text(s['provenance'].read_text() + '\nmodel: {}\n')
    elif damage == 'malformed-provenance': s['provenance'].write_text('outputs: [unterminated')
    with pytest.raises(ValueError): mod.write_disclosed_summaries(s['root'], s['out'], generation_bindings=bindings)
    assert not s['out'].exists()


@pytest.mark.parametrize('change', ['bytes', 'symlink-target'])
def test_changed_rating_between_captures_refuses(sample, monkeypatch, change):
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


@pytest.mark.parametrize('target', ['existing-directory', 'symlink-directory', 'rating', 'input', 'provenance'])
def test_existing_destinations_are_not_replaced(sample, target):
    s = sample; before = {s[k]: s[k].read_bytes() for k in ('rating', 'input', 'provenance')}
    if target == 'existing-directory': s['out'].mkdir()
    elif target == 'symlink-directory': s['out'].symlink_to(s['root'])
    else: s['out'] = s[target]
    with pytest.raises(ValueError, match='directory must be new'): run(s)
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('alias', ['hardlink', 'symlink'])
def test_late_output_alias_preserves_input_and_failed_partial_evidence(sample, monkeypatch, alias):
    s = sample; original = Path.mkdir; before = s['input'].read_bytes()
    def race(path, *a, **k):
        result = original(path, *a, **k)
        if path == s['out']:
            p = path / 'summary_table.md';(p.hardlink_to if alias == 'hardlink' else p.symlink_to)(s['input'])
        return result
    monkeypatch.setattr(Path, 'mkdir', race)
    with pytest.raises(FileExistsError): run(s)
    assert s['input'].read_bytes() == before and (s['out'] / 'all_scores.csv').exists()
    assert not (s['out'] / 'summary_report.md').exists()


def test_explicit_recorded_path_root_is_used(sample):
    s = sample; root = s['input'].parent / 'recorded-root'; (root / 'relative').mkdir(parents=True)
    (root / 'relative/input.yaml').symlink_to(s['input'])
    s['doc']['d4d_file'] = s['prov']['outputs']['full']['path'] = 'relative/input.yaml';save(s)
    mod.write_disclosed_summaries(s['root'], s['out'], generation_bindings=[binding(s)], disclosure_root=root)
    assert rows(s)[0]['generation_binding'] == 'associated'


def test_missing_percentage_refuses_before_new_directory(sample):
    s = sample;s['doc']['overall_score'].pop('percentage');save(s)
    with pytest.raises(mod.MissingPercentage):run(s)
    assert not s['out'].exists()
    with pytest.raises(SystemExit) as exc:
        mod.main(['--model-disclosure', 'declared-v1', '--evaluation-root', str(s['root']),
                  '--output-dir', str(s['out'])])
    assert exc.value.code == 2 and not s['out'].exists()


def test_no_option_cli_uses_legacy_entrypoint(monkeypatch):
    sentinel = object();monkeypatch.setattr(mod, '_legacy_main', lambda: sentinel)
    assert mod.main([]) is sentinel


@pytest.mark.parametrize('args', [['--output-dir', 'new'], ['--evaluation-root', 'missing'],
                                  ['--model-disclosure', 'declared-v1'], ['--model-disclosure', 'unknown']])
def test_cli_requires_explicit_selector_and_new_destination(args, monkeypatch):
    monkeypatch.setattr(mod, '_legacy_main', lambda: pytest.fail('invalid options entered default writer'))
    with pytest.raises(SystemExit) as exc:mod.main(args)
    assert exc.value.code == 2


def test_actual_opt_in_cli_preserves_inputs(sample):
    s = sample;before = {s[k]: s[k].read_bytes() for k in ('rating', 'input', 'provenance')}
    proc = subprocess.run([sys.executable, str(ROOT / 'scripts/summarize_rubric10_results.py'),
        '--model-disclosure', 'declared-v1', '--evaluation-root', str(s['root']), '--output-dir', str(s['out']),
        '--generation-binding', str(s['rating']), str(s['input']), str(s['provenance'])],
        env={**os.environ, 'PYTHONPATH': str(ROOT / 'src'), 'PYTHONDONTWRITEBYTECODE': '1'}, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)['ratings'] == 1 and rows(s)[0]['same_family'] == 'yes'
    assert {p: p.read_bytes() for p in before} == before
