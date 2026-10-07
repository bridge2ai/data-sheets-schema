"""Fig09 must not turn missing mapper output into absent source evidence."""
import hashlib
import json
import csv

import pytest

from data_sheets_schema.crate_generation_comparison import (
    compare_records, generated_v8_rep1, parse_report, source_evidence_rows, values_agree,
)


def report(header="3 table rows applied, plus the record's `id`, taken from the crate root",
           disposition="subsumed"):
    return f"""- Mapping table: `mapping.tsv` ({header})
- Distinct top-level `Dataset` slots filled: 2 (from 2 filled rows)
## Outcome
| Status | Rows | Meaning |
|---|---|---|
| filled | 2 | placed |
| {disposition} | 1 | separate |
| empty | 1 | absent |
## Fidelity of what was filled
| Mapping type | Filled fields |
|---|---|
| exactMatch | 2 |
| Information loss | Filled fields |
|---|---|
| none | 2 |
## Per-field detail
| D4D path | Status | Mapping | Loss | Source path | Value / note |
|---|---|---|---|---|---|
| Dataset.id | filled | exactMatch | none | crate root identifier/@id | doi:10.1234/x |
| Dataset.title | filled | exactMatch | none | name | title |
| Other.description | {disposition} | closeMatch | moderate | name | a \\| b |
| Dataset.description | empty | exactMatch | none | description | absent |
"""


def test_current_header_and_subsumed_reconcile_rows_and_slots():
    actual = parse_report(report())
    assert actual['original_rows'] == 3
    assert actual['active_rows'] == 3
    assert actual['report_entries'] == 4
    assert actual['root_identifier_rows'] == 1
    assert actual['distinct_slots'] == 2
    assert actual['outcome']['subsumed'] == 1


def test_declared_header_keeps_disposition_denominators():
    actual = parse_report(report('3 table rows declared', 'retired'))
    assert actual['original_rows'] == 3 and actual['active_rows'] == 2


@pytest.mark.parametrize('label', ['(unstated)', '—', 'unassessed'])
def test_unassessed_fidelity_remains_in_filled_denominator(label):
    text = report().replace('| none | 2 |', f'| {label} | 2 |')
    actual = parse_report(text)
    assert actual['loss'] == {'—': 2}
    assert sum(actual['loss'].values()) == actual['outcome']['filled']


def test_unknown_fidelity_bucket_cannot_disappear_from_figure():
    with pytest.raises(ValueError, match='unrecognized declared loss'):
        parse_report(report().replace('| none | 2 |', '| exceptional | 2 |'))


@pytest.mark.parametrize('disposition', ['retired', 'deferred'])
def test_dispositions_have_a_separate_active_denominator(disposition):
    actual = parse_report(report('3 original table rows; 2 active rows', disposition))
    assert actual['original_rows'] == 3 and actual['active_rows'] == 2
    assert actual['outcome'][disposition] == 1


@pytest.mark.parametrize('before,after', [
    ('| subsumed | 1 |', '| subsumed | 0 |'),
    ('3 table rows applied', '4 table rows applied'),
    ('| exactMatch | 2 |', '| exactMatch | 3 |'),
    ('| subsumed | 1 |', '| ignored | 1 |'),
])
def test_inconsistent_or_unknown_accounting_is_refused(before, after):
    with pytest.raises(ValueError):
        parse_report(report().replace(before, after))


def test_doi_spelling_agrees_but_voice_release_does_not():
    assert values_agree('doi', 'https://doi.org/10.1234/X', '10.1234/x')
    assert values_agree('id', 'doi:10.1234/X', 'http://dx.doi.org/10.1234/x')
    assert not values_agree('doi', '10.13026/k81f-qr68', '10.13026/8xbn-nq66')
    assert not values_agree('id', 'https://example.org/A', 'https://example.org/a')
    assert not values_agree('description', 'doi:10.1234/X', '10.1234/x')


def test_generated_only_is_not_a_source_absence_claim_and_zero_is_populated():
    counts, details = compare_records('P', {'total_size_bytes': 0},
                                     {'data_governance': {'committee_name': 'Board'}})
    assert counts['crate_only'] == counts['generated_only'] == 1
    assert all(row['source_evidence'] == 'not_assessed_by_slot_overlap' for row in details)


def test_generated_selection_deduplicates_scoring_jobs_but_refuses_different_records():
    job = {'cohort': 'v8', 'generation_rep': 1, 'project': 'P', 'input': 'record.yaml'}
    assert generated_v8_rep1({'jobs': [job, dict(job)]}) == {'P': 'record.yaml'}
    with pytest.raises(ValueError, match='ambiguous'):
        generated_v8_rep1({'jobs': [job, {**job, 'input': 'other.yaml'}]})


def evidence(root=(), members=(), expression="@graph[?@type='Dataset']['value']"):
    return {'format_version': 1, 'project': 'P', 'rows': [{
        'rule_id': 'r1', 'execution': 'deferred', 'd4d_path': 'Old.value',
        'destination_slot': None, 'mapping_rule': '', 'source_expression': expression,
        'status': 'deferred', 'root_assertions': list(root), 'member_assertions': list(members),
    }]}


@pytest.mark.parametrize('root,members,expression,expected', [
    ([{'value': 0}], [], 'value', 'root_value_present'),
    ([{'value': False}], [], 'value', 'root_value_present'),
    ([], [{'value': 'member fact'}], 'generatedBy', 'member_value_only'),
    ([{'value': ''}], [], 'value', 'property_present_but_empty'),
    ([], [], 'value', 'source_absent_for_expression'),
    ([], [], 'N/A', 'not_assessed'),
    ([], [], 'encodingFormat MIME parameter', 'not_assessed'),
])
def test_source_scope_and_observation_are_not_record_overlap(root, members, expression, expected):
    row = source_evidence_rows(evidence(root, members, expression))[0]
    assert row['source_evidence'] == expected
    assert row['mapping_status'] == 'deferred' and row['placed_by_this_row'] is False


def test_source_rows_require_unique_identity():
    sidecar = evidence()
    sidecar['rows'] *= 2
    with pytest.raises(ValueError, match='duplicate'):
        source_evidence_rows(sidecar)


@pytest.fixture
def prepared_inputs(tmp_path, monkeypatch):
    from scripts.figures import fig09_mapping_revision as figure
    monkeypatch.setattr(figure, 'PROJECTS', ('P',))
    packages = tmp_path / 'packages'
    processed = packages / 'P/processed'
    processed.mkdir(parents=True)
    static = tmp_path / 'new-label'
    static.mkdir()
    raw_record = b'id: doi:10.1234/x\ntitle: title\n'
    (processed / 'P_crate_mapped_d4d.yaml').write_bytes(raw_record)
    (static / 'P_d4d.yaml').write_bytes(raw_record)
    (processed / 'P_crate_mapping_provenance.md').write_text(
        report('3 table rows declared', 'retired'))
    sidecar = evidence([{'value': 'title'}])
    first = sidecar['rows'][0]
    first.update(rule_id='r1', execution='active', d4d_path='Dataset.title',
                 destination_slot='title', status='filled', source_expression='name')
    sidecar['rows'] += [
        {**first, 'rule_id': 'r2', 'd4d_path': 'Other.description', 'execution': 'retired', 'status': 'retired'},
        {**first, 'rule_id': 'r3', 'd4d_path': 'Dataset.description', 'source_expression': 'description', 'status': 'empty', 'root_assertions': []},
    ]
    for key in ('schema', 'mapping_table'):
        path = tmp_path / key
        path.write_bytes(key.encode())
        sidecar[key] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    table = tmp_path / 'mapping_table'
    with table.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['Rule_ID', 'D4D_Full_Path', 'Execution', 'RO_Crate_JSON_Path'], delimiter='\t')
        writer.writeheader()
        for row in sidecar['rows']:
            writer.writerow(dict(zip(writer.fieldnames, (row['rule_id'], row['d4d_path'], row['execution'], row['source_expression']))))
    sidecar['mapping_table']['sha256'] = hashlib.sha256(table.read_bytes()).hexdigest()
    crate_source = tmp_path / 'crate.json'
    crate_source.write_text('{"@graph": []}')
    sidecar['source'] = {'path': str(crate_source), 'sha256': hashlib.sha256(crate_source.read_bytes()).hexdigest()}
    sidecar['record_sha256'] = hashlib.sha256(raw_record).hexdigest()
    producer = {}
    for name in ('rocrate_map', 'rocrate_sources', 'rocrate_assertions', 'scope', 'schema_view'):
        path = tmp_path / f'src/data_sheets_schema/{name}.py'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# fixture producer\n')
        producer[str(path.relative_to(tmp_path))] = hashlib.sha256(path.read_bytes()).hexdigest()
    sidecar['producer'] = {'files_sha256': producer}
    source_path = processed / 'P_crate_mapping_sources.json'
    source_path.write_text(json.dumps(sidecar))
    generated = tmp_path / 'historical.yaml'
    generated.write_text('id: https://doi.org/10.1234/x\ntitle: title\n')
    manifest = tmp_path / 'historical-manifest.json'
    manifest.write_text(json.dumps({'jobs': [{'cohort': 'v8', 'generation_rep': 1,
                                            'project': 'P', 'input': str(generated)}]}))
    return figure, packages, static, manifest, source_path


def test_preparation_reconciles_published_record_report_sidecar_and_bound_inputs(prepared_inputs, tmp_path):
    figure, packages, static, manifest, sidecar = prepared_inputs
    result = figure.prepare(tmp_path, packages, static, manifest)
    assert result['projects'][0]['active_rows'] == 2
    assert result['projects'][0]['overlap']['both_agree'] == 2
    assert len(result['source_observations']) == 3
    (tmp_path / 'schema').write_bytes(b'changed')
    with pytest.raises(ValueError, match='schema hash'):
        figure.prepare(tmp_path, packages, static, manifest)


def test_markdown_row_order_is_independent_of_stable_table_order(prepared_inputs, tmp_path):
    figure, packages, static, manifest, sidecar = prepared_inputs
    path = packages / 'P/processed/P_crate_mapping_provenance.md'
    lines = path.read_text().splitlines()
    positions = [i for i, line in enumerate(lines) if line.startswith(('| Dataset.', '| Other.'))]
    ordered = sorted((lines[i] for i in positions), key=lambda line: ('| filled |' not in line, line.split('|')[1]))
    for index, line in zip(positions, ordered):
        lines[index] = line
    path.write_text('\n'.join(lines) + '\n')
    assert figure.prepare(tmp_path, packages, static, manifest)['projects'][0]['active_rows'] == 2


@pytest.mark.parametrize('changed', ['raw', 'record', 'rule', 'row_status', 'producer'])
def test_preparation_refuses_stale_source_or_wrong_row_join(prepared_inputs, tmp_path, changed):
    figure, packages, static, manifest, path = prepared_inputs
    sidecar = json.loads(path.read_text())
    if changed == 'raw':
        sidecar['source']['sha256'] = '0' * 64
    elif changed == 'record':
        sidecar['record_sha256'] = '0' * 64
    elif changed == 'rule':
        sidecar['rows'][0]['rule_id'] = 'different'
    elif changed == 'producer':
        sidecar['producer']['files_sha256']['src/data_sheets_schema/rocrate_sources.py'] = '0' * 64
    else:
        sidecar['rows'][0]['status'], sidecar['rows'][2]['status'] = sidecar['rows'][2]['status'], sidecar['rows'][0]['status']
    path.write_text(json.dumps(sidecar))
    with pytest.raises(ValueError):
        figure.prepare(tmp_path, packages, static, manifest)


def test_derived_evidence_retains_referenced_assertions():
    sidecar = evidence([{'value': {'@id': 'board'}}])
    linked = [{'json_pointer': '/@graph/2', 'value': {'@id': 'board', '@type': 'Organization', 'name': 'Review Board'}}]
    sidecar['rows'][0]['linked_assertions'] = linked
    assert source_evidence_rows(sidecar)[0]['linked_assertions'] == linked


def test_publication_refuses_input_drift_without_a_completion_manifest(prepared_inputs, tmp_path, monkeypatch):
    figure, packages, static, manifest, sidecar = prepared_inputs
    prepared = figure.prepare(tmp_path, packages, static, manifest)
    def render_then_change_input(*args):
        sidecar.write_bytes(b'changed during rendering')
    monkeypatch.setattr(figure, 'render', render_then_change_input)
    output = tmp_path / 'figure'
    with pytest.raises(ValueError, match='input changed'):
        figure.publish(prepared, output, 'f' * 40)
    assert not (output / 'manifest.json').exists()


def test_new_export_keeps_original_rows_and_source_values_and_refuses_overwrite(prepared_inputs, tmp_path, monkeypatch):
    figure, packages, static, manifest, sidecar = prepared_inputs
    prepared = figure.prepare(tmp_path, packages, static, manifest)
    monkeypatch.setattr(figure, 'render', lambda *args: None)
    output = tmp_path / 'figure'
    completed = figure.publish(prepared, output, 'f' * 40)
    assert completed['state'] == 'complete' and completed['scientific_scoring'] is False
    assert 'historical' in (output / 'README.txt').read_text()
    assert 'title' in (output / 'fig09_crate_vs_generation_source_observations.csv').read_text()
    before = (output / 'manifest.json').read_bytes()
    with pytest.raises(FileExistsError):
        figure.publish(prepared, output, 'f' * 40)
    assert (output / 'manifest.json').read_bytes() == before
