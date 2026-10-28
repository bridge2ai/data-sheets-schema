"""Pre-dispatch context admission for generic_v10's 128k-cap phases (#5157, owner decision D33).

Scripted fake deliveries through the real selected state machine; no provider
calls. The endpoint count is the fake's answer, never a measured token count.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import httpx
import pytest
import yaml

from data_sheets_schema import api_runner as api, chunking, dollar_readout as dr
from data_sheets_schema import receipt_completion as rc, snapshot_store, typed_audit_runtime as runtime
from data_sheets_schema import usage_ledger as ledger
from data_sheets_schema.resources import physical, resource_path
import tests.test_shared_generation_runtime as sgr
from tests.test_download.test_api_runner import _rate_limit_error
from tests.test_evidence_generation_gate import specification
from tests.test_shared_generation_selection import registration_for, selected_spec

ROOT = Path(__file__).resolve().parents[1]
CHORUS_BUNDLE = ROOT / 'data/preprocessed/concatenated/CHORUS_preprocessed.txt'
ADMITTED = ('reconcile_full', 'report', 'report_regate')
BASIS = 'Synthetic assertion, not measured route capacity'
REPAIR_MARK = '# synthetic validation repair'

#: The CHORUS fixture's dispatched wire at incoming A13 base
#: 04799422669fb2bd9f571bf8c0800dfc4b0ef008, independently derived without
#: the #5210 admission implementation: sha256 of `messages.stream` keyword
#: arguments as sorted compact JSON, with the run's temporary root replaced by
#: `<root>` and the checkout the schema resolved from by `<repo>`, so any
#: checkout reproduces them. They move with any model-facing input (the
#: bundle, the schema, a v10 prompt asset or carry format, the selected
#: settings) or the fake's scripted records; the admission must never move
#: them. The second half of the test re-derives them with admission bypassed.
#: The original f8 baseline remains named historical metadata. Its three
#: hashes reproduce exactly; the incoming A13 differences are explained only
#: by inherited D38 v10 prompt spelling/wrapping. See the committed reversible
#: comparison in notes/wave5_5210_wire_lineage_2026-10-28/README.md.
HISTORICAL_F8_WIRE_SHA256 = {
    'reconcile_full': 'b4f8f925e29b54d80cc95ad7c5bbe3f170e7295ccb1c8b8eb3a3dcaf97421daa',
    'report': '9a13ed423b0c5bb7c0da908100ead81128f713dfc0dc0b565ecd4bd11c8bfbe8',
    'report_regate': '300b1213e94825e41fc22a38bb4100aabebbb533ec0de49487485dfac49a79a9',
}
BASE_WIRE_SHA256 = {
    'reconcile_full': '31340b31d787baa1da17c2b738c99d21efd2a1db9150eb0d0aaf917f1ac6160c',
    'report': 'eea1fe34d3de44efbc85a681b5b2d58c0f66bcc70f7b64450378db75fc996749',
    'report_regate': 'd085cabccdc8d0b7e1e99d498e6f3cfe59b80322c907d3e8d49b177aaf672f1d',
}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: pytest.fail('network forbidden'))
    monkeypatch.setattr(api, 'provider_identity', lambda: {'provider': None, 'base_url': None, 'key_env': None})
    monkeypatch.setattr(api, 'MAX_ATTEMPTS', 1)


def counted_phase(spec, kwargs):
    """The admitted phase a request belongs to, read off its own wire."""
    last = [p['text'] for p in kwargs['messages'][-1]['content'] if isinstance(p, dict)][-1]
    if last.startswith('Report re-check.'):
        return 'report_regate'
    phase = next((p for p in ('reconcile_full', 'report')
                  if last.startswith(api.phase_instruction(p, spec.render_version).split('\n')[0])), None)
    if phase == 'report' and REPAIR_MARK in json.dumps(kwargs['messages']):
        return 'report_after_repair'   # the refresh carries the repaired record
    return phase


def typed_phase(kwargs):
    """The typed audit stage a request belongs to, if it is one."""
    blocks = [p['text'] for p in kwargs['messages'][-1]['content'] if isinstance(p, dict)]
    stage = next((s for s in blocks if s.startswith('# Exact typed stage request\n\n')), None)
    if stage is None:
        return None
    kind = json.loads(stage.split('\n\n', 1)[1]).get('kind')
    return {'typed_audit_worker_request_v1': runtime.WORKER_PHASE,
            'typed_audit_index_v1': runtime.INTEGRATION_PHASE}.get(kind, runtime.OMISSION_PHASE)


def measured(kwargs):
    """A size-proportional synthetic count, so a grown carry grows the count."""
    return len(json.dumps(kwargs['system']) + json.dumps(kwargs['messages'])) // 4


class Counted(sgr.Script):
    """The runtime script, with a count per phase.

    `counts` maps a phase to a count or a callable of the count request;
    `failures` maps an admitted phase to exceptions its successive counts
    raise. `counted` lists the admitted phase of each count, None for the
    receipt completion and the typed stages.
    """

    def __init__(self, spec, *, counts=None, failures=None, padding='', no_table=False, **kwargs):
        super().__init__(spec, **kwargs)
        self.counts, self.failures = counts or {}, {k: list(v) for k, v in (failures or {}).items()}
        self.padding, self.no_table, self.counted = padding, no_table, []

    def count_tokens(self, **kwargs):
        self.count_calls.append(deepcopy(kwargs))
        phase = counted_phase(self.spec, kwargs)
        self.counted.append(phase)
        if self.failures.get(phase):
            raise self.failures[phase].pop(0)
        value = self.counts.get(phase or typed_phase(kwargs), 1000)
        return SimpleNamespace(input_tokens=value(kwargs) if callable(value) else value)

    def create(self, **kwargs):
        result = super().create(**kwargs)
        if self.phases[-1] == 'report':
            self.phases[-1] = counted_phase(self.spec, kwargs)
            text = result.content[0].text
            if self.padding:
                text = text.replace('# Reconciliation\n\n', '# Reconciliation\n\n' + self.padding + '\n\n', 1)
            if self.no_table:
                text = text.split('\n\n## Dispositions', 1)[0] + '\n'
            result.content[0].text = text
        return result


def client_for(messages):
    result = SimpleNamespace(messages=messages, base_url='https://example.invalid', max_retries=2)
    result.with_options = lambda **options: SimpleNamespace(messages=messages,
        base_url=result.base_url, max_retries=options['max_retries'])
    return result


def example(tmp_path, *, limit=None):
    base = specification(tmp_path)
    reg = registration_for(base)
    if limit is not None:
        reg['audit_limits']['context_limit_tokens'] = limit
    return selected_spec(base, reg)


def chorus(root):
    root.mkdir(parents=True)
    bundle = root / 'CHORUS_preprocessed.txt'
    bundle.write_bytes(CHORUS_BUNDLE.read_bytes())
    manifest = root / 'CHORUS_chunks.yaml'
    manifest.write_text(chunking.dump_manifest(chunking.build_manifest(bundle)))
    base = api.RunSpec(project='CHORUS', arm='baseline', method='claudecode_api', bundle=bundle,
                       label='2026-10-25_chorus-report-wire_rep1', condition='generic', manifest=None,
                       chunk_manifest=manifest, profile='neutral', render_version=9, out_dir=root / 'output',
                       runtime='Claude API (direct)', run_date='2026-10-25')
    return selected_spec(base, registration_for(base))


def checkout():
    """The checkout the captured schema resolved from; the registration pins it absolutely."""
    schema = str(physical(resource_path(api.FULL_SCHEMA_PATH)))
    assert schema.endswith('/' + api.FULL_SCHEMA_PATH)
    return schema[:-len(api.FULL_SCHEMA_PATH) - 1]


def wire_sha256(wire, root):
    raw = json.dumps(wire, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    normalised = raw.replace(str(root), '<root>').replace(checkout(), '<repo>')
    return hashlib.sha256(normalised.encode()).hexdigest()


def chorus_wires(root, monkeypatch):
    """The CHORUS fixture's reconcile, report and regate wires, as dispatched."""
    quote = 'NIH RePORTER Project'
    spec = chorus(root)
    source = next(c for c in chunking.build_manifest(spec.bundle)['chunks'] if c['id'] == 'c002')['source']
    monkeypatch.setattr(sgr, 'SOURCE', {'c002': {'source': source, 'text': quote}})
    monkeypatch.setattr(sgr, 'FULL', {'id': 'urn:chorus', 'title': 'CHORUS', 'name': 'chorus',
                                      'description': quote, 'keywords': ['chorus']})
    messages = Counted(spec, bad_report=True)
    result = api.execute(spec, client=client_for(messages))
    assert result['validation_problems'] == []
    assert messages.phases[-3:] == list(ADMITTED)
    return spec, messages, {p: messages.calls[messages.phases.index(p)] for p in ADMITTED}


def request_payload(wire):
    request = api.PhaseRequest(phase='wire', system=wire['system'], messages=wire['messages'])
    return rc.request_payload(request, {'name': wire['model'], 'temperature': wire.get('temperature'),
        'thinking': wire.get('thinking'), 'effort': (wire.get('extra_body') or {}).get('output_config', {}).get('effort')},
        {'max_output_tokens': wire['max_tokens']})


def snapshots(spec, suffix):
    index = json.loads(snapshot_store.index_path(spec.provenance_path.parent, spec.project).read_bytes())
    return [row for row in index['snapshots'] if row['name'].endswith(suffix)]


def saved(row):
    return json.loads(Path(row['path']).read_bytes())


def record(spec):
    return yaml.safe_load(spec.provenance_path.read_bytes())


def counts_for(messages, phase):
    return [c for c, p in zip(messages.count_calls, messages.counted) if p == phase]


def repaired_once(monkeypatch, artifact):
    """Validation fails once and the repair rewrites one record, as a real repair does."""
    original, seen = api.validate_outputs, []

    def validate(spec):
        seen.append(spec)
        return ([{'artifact': str(spec.full_path), 'class': 'Dataset', 'error': 'synthetic finding'}]
                if len(seen) == 1 else original(spec))

    def repair(spec, client, settings, usage):
        path = spec.full_path if artifact == 'full' else spec.core_path
        path.write_text(path.read_text(encoding='utf-8') + REPAIR_MARK + '\n', encoding='utf-8')
        return [{'phase': f'repair_{artifact}', 'round': 1, 'outcome': 'synthetic rewrite'}]
    monkeypatch.setattr(api, 'validate_outputs', validate)
    monkeypatch.setattr(api, '_repair_invalid', repair)


def refused_facts(spec, phase, reason, **found):
    limit = json.loads(spec.shared_generation_registration)['audit_limits']['context_limit_tokens']
    return {'phase': phase, 'attempt': 1, 'max_tokens': 128000, 'context_limit_tokens': limit,
            'context_limit_basis': BASIS, 'reason': reason, **found}


def without_hash(facts):
    return {k: v for k, v in facts.items() if k != 'request_sha256'}


def admit(spec, counter):
    """The admission alone, on a fixed report request: no run, no ledger."""
    client = SimpleNamespace(messages=SimpleNamespace(count_tokens=counter))
    kwargs = {'model': 'claude-opus-5', 'system': 'synthetic system', 'max_tokens': 128000, 'temperature': None,
              'thinking': None, 'effort': None,
              'messages': [{'role': 'user', 'content': [{'type': 'text', 'text': 'synthetic request'}]}]}
    api._admit_shared_context(spec, 'report', 1, client, kwargs)


def kept(spec, name):
    return [json.loads(p.read_bytes()) for p in sorted(api._intermediate_dir(spec).glob(f'{spec.project}_{name}'))]


def test_every_phase_sent_at_a_raised_cap_is_admitted():
    """The caps' two phases plus the two that share the report budget, which
    are the phases the readout prices at the raised caps."""
    assert api.SHARED_ADMITTED_PHASES == set(api.SHARED_PHASE_MAX_TOKENS) | {'report_regate', 'report_after_repair'}
    assert api.SHARED_ADMITTED_PHASES == set(dr.SHARED_V1_PHASE_OUTPUT_CAPS)


def test_chorus_wire_is_byte_identical_to_the_base_and_is_what_was_counted(tmp_path, monkeypatch):
    spec, messages, wires = chorus_wires(tmp_path / 'head', monkeypatch)
    assert {p: wire_sha256(w, tmp_path / 'head') for p, w in wires.items()} == BASE_WIRE_SHA256
    # Each admitted phase was counted once, on exactly the request it then sent.
    for phase, wire in wires.items():
        [count] = counts_for(messages, phase)
        assert {k: count.get(k) for k in ('model', 'system', 'messages', 'thinking', 'extra_body')} == {
            k: wire.get(k) for k in ('model', 'system', 'messages', 'thinking', 'extra_body')}
        [row] = snapshots(spec, f'_{phase}_context.json')
        assert saved(row)['request_sha256'] == rc.sha(rc.canonical(request_payload(wire)))
        assert 'usage_id' not in row   # a measurement, not a delivery to account for
    # Without the admission the same wire goes out: the check adds a count, never bytes.
    monkeypatch.setattr(api, '_admit_shared_context', lambda *a, **k: None)
    _, unchecked, plain = chorus_wires(tmp_path / 'base', monkeypatch)
    assert {p: wire_sha256(w, tmp_path / 'base') for p, w in plain.items()} == BASE_WIRE_SHA256
    assert not any(unchecked.counted)


def test_a_fitting_request_is_admitted_and_its_count_is_kept(tmp_path):
    spec = example(tmp_path)
    messages = Counted(spec)
    result = api.execute(spec, client=client_for(messages))
    assert result['validation_problems'] == []
    assert [p for p in messages.counted if p] == ['reconcile_full', 'report']
    for phase in ('reconcile_full', 'report'):
        [row] = snapshots(spec, f'_{phase}_context.json')
        value = saved(row)
        assert value == {'input_tokens': 1000, 'method': 'endpoint messages.count_tokens',
            'request_sha256': value['request_sha256'], 'context_limit_tokens': 900000,
            'context_limit_basis': BASIS, 'capacity_authority': 'caller assertion',
            'phase': phase, 'attempt': 1, 'max_tokens': 128000}
    assert not snapshots(spec, '_context_refused.json')
    # The provenance record pins the measurement among its intermediates.
    names = {i['phase'] for i in record(spec)['intermediates'] if 'usage_id' not in i}
    assert {f'{spec.project}_reconcile_full_context.json', f'{spec.project}_report_context.json'} <= names


def test_exactly_at_the_limit_is_admitted(tmp_path):
    spec = example(tmp_path)
    messages = Counted(spec, counts={'report': 900000 - 128000})
    result = api.execute(spec, client=client_for(messages))
    assert result['validation_problems'] == [] and messages.phases[-1] == 'report'


def test_over_by_one_refuses_the_report_before_dispatch_and_is_not_retried(tmp_path, monkeypatch):
    """The run cannot complete without its report, so a refused report stops it."""
    monkeypatch.setattr(api, 'MAX_ATTEMPTS', 5)   # a retry would recount and re-send
    spec = example(tmp_path)
    messages = Counted(spec, counts={'report': 900000 - 128000 + 1})
    with pytest.raises(api.ContextNotAdmitted, match='report not admitted') as refused:
        api.execute(spec, client=client_for(messages))
    assert '772,001' in str(refused.value) and '900,000' in str(refused.value)
    assert 'report' not in messages.phases and messages.counted.count('report') == 1
    data = ledger._read(spec)
    assert data.get('pending_call') is None
    assert [r['phase'] for r in data['rows']][-1] == 'reconcile_full'
    assert not snapshots(spec, '_report_context.json') and not spec.report_path.exists()
    [row] = snapshots(spec, '_report_context_refused.json')
    assert without_hash(saved(row)) == refused_facts(spec, 'report', 'over_window', input_tokens=772001)
    assert 'reconcile_full' in api._load_progress(spec)['completed']
    # Nothing billed, nothing pending, no abandoned attempt: the readout is unchanged.
    readout = dr.compute_readout(ledger.ledger_path(spec), project=spec.project)
    assert not readout['has_pending_call'] and readout['settled_calls'] == len(data['rows'])
    assert readout['settled_dollars'] == dr.price_settled_rows(data['rows'])
    assert not ledger.abandoned_journal_path(spec).exists()
    # Deterministic: a resume recounts the same request and refuses it again, still unsent.
    again = Counted(spec, counts={'report': 900000 - 128000 + 1})
    with pytest.raises(api.ContextNotAdmitted, match='report not admitted'):
        api.execute(replace(spec), client=client_for(again))
    assert again.phases == [] and again.counted.count('report') == 1
    assert ledger._read(spec)['rows'] == data['rows']


@pytest.mark.parametrize('mode', ['over_window', 'count_unavailable'])
def test_a_refused_regate_keeps_the_report_and_the_run_publishes(tmp_path, mode):
    """A regate the window cannot hold is a regate that failed (#967): the
    report as written stands, the gate records why, the record is written."""
    limit = 128000 + 100000
    spec = example(tmp_path, limit=limit)
    if mode == 'over_window':
        padding = 'Padding prose. ' * 40000   # 600 kB: the rejected report the regate must carry
        messages = Counted(spec, no_table=True, padding=padding, counts={p: measured for p in ADMITTED})
    else:
        padding = ''
        messages = Counted(spec, no_table=True, failures={'report_regate': [RuntimeError('route count unavailable')]})
    result = api.execute(spec, client=client_for(messages))
    assert result['validation_problems'] == []
    assert messages.phases[-1] == 'report' and 'report_regate' not in messages.phases
    [regate] = counts_for(messages, 'report_regate')
    gate = record(spec)['report_gate']
    assert gate['table_missing_before'] and gate['regenerated'] is False
    assert gate['regeneration_attempted'] is False and not ledger.report_regate_attempted(spec)
    assert gate['reason'] == 'the regate was not admitted before dispatch; the report as written was kept'
    if mode == 'over_window':
        [report] = counts_for(messages, 'report')
        assert measured(report) + 128000 <= limit < measured(regate) + 128000
        blocks = [p['text'] for p in regate['messages'][0]['content']]
        assert any(b.startswith(api.REGATE_HEADERS[0]) and padding in b for b in blocks)
        expected = refused_facts(spec, 'report_regate', mode, input_tokens=measured(regate))
    else:
        expected = refused_facts(spec, 'report_regate', mode, error=(
            'report_regate endpoint token count unavailable: route count unavailable'))
    assert without_hash(gate['regate_refused']) == expected
    [row] = snapshots(spec, '_report_regate_context_refused.json')
    assert saved(row) == gate['regate_refused']
    [kept_report] = snapshots(spec, '_report_before_regate.md')
    assert spec.report_path.read_text(encoding='utf-8') == Path(kept_report['path']).read_text(encoding='utf-8')
    assert padding in spec.report_path.read_text(encoding='utf-8')
    # The published run is complete: a resume sends and counts nothing and adds no snapshot.
    index, before = snapshot_store.index_path(spec.provenance_path.parent, spec.project).read_bytes(), record(spec)
    again = Counted(spec)
    assert api.execute(replace(spec), client=client_for(again))['already_complete']
    assert not again.calls and not again.count_calls
    assert snapshot_store.index_path(spec.provenance_path.parent, spec.project).read_bytes() == index
    assert record(spec) == before


def test_a_refused_regate_is_recorded_before_the_evidence_refusal(tmp_path):
    """The record is written first and the terminal refusal follows (#1818),
    so a resume refuses without a count, a send or another snapshot."""
    spec = example(tmp_path)
    messages = Counted(spec, bad_report=True, counts={'report_regate': 900000})
    with pytest.raises(RuntimeError, match='report evidence assertions failed'):
        api.execute(spec, client=client_for(messages))
    assert 'report_regate' not in messages.phases
    gate = record(spec)['report_gate']
    assert gate['regenerated'] is False and gate['findings_after'] == gate['findings_before'] == 1
    assert without_hash(gate['regate_refused']) == refused_facts(spec, 'report_regate', 'over_window',
                                                                   input_tokens=900000)
    assert ledger.evidence_refusal(spec)['stage'] == 'report'
    index = snapshot_store.index_path(spec.provenance_path.parent, spec.project).read_bytes()
    again = Counted(spec)
    with pytest.raises(RuntimeError, match='report evidence assertions failed'):
        api.execute(replace(spec), client=client_for(again))
    assert not again.calls and not again.count_calls
    assert snapshot_store.index_path(spec.provenance_path.parent, spec.project).read_bytes() == index


@pytest.mark.parametrize('artifact', ['full', 'core'])
def test_a_refused_refresh_after_repair_is_latched_under_its_own_cause(tmp_path, monkeypatch, artifact):
    """The refresh regenerates the report after repair rewrote a record
    (#604). Refused, the report as written no longer describes the records,
    so the refusal is latched as terminal, naming the admission and its
    numbers, and a resume re-raises it before any drift logic (#1820): no
    count, no send, no new snapshot."""
    repaired_once(monkeypatch, artifact)
    spec = example(tmp_path)
    messages = Counted(spec, counts={'report_after_repair': 900000 - 128000 + 1})
    with pytest.raises(RuntimeError, match='report evidence assertions failed.*report_refresh_not_admitted'):
        api.execute(spec, client=client_for(messages))
    assert messages.phases[-1] == 'report' and 'report_after_repair' not in messages.phases
    [refresh] = counts_for(messages, 'report_after_repair')
    assert REPAIR_MARK in json.dumps(refresh['messages'])   # counted on the refreshed request
    facts = refused_facts(spec, 'report_after_repair', 'over_window', input_tokens=772001)
    [row] = snapshots(spec, '_report_after_repair_context_refused.json')
    assert without_hash(saved(row)) == facts
    refusal = ledger.evidence_refusal(spec)
    assert refusal['stage'] == 'report' and refusal['reading']['checked'] is False
    assert refusal['reading']['findings'] == [{'kind': 'report_refresh_not_admitted', **saved(row)}]
    [written] = snapshots(spec, f'{spec.project}_report.md')
    assert spec.report_path.read_text(encoding='utf-8') == Path(written['path']).read_text(encoding='utf-8')
    data = ledger._read(spec)
    assert data.get('pending_call') is None and 'report_after_repair' not in [r['phase'] for r in data['rows']]
    index = snapshot_store.index_path(spec.provenance_path.parent, spec.project).read_bytes()
    again = Counted(spec)
    with pytest.raises(RuntimeError, match='report evidence assertions failed.*report_refresh_not_admitted'):
        api.execute(replace(spec), client=client_for(again))
    assert not again.calls and not again.count_calls
    assert snapshot_store.index_path(spec.provenance_path.parent, spec.project).read_bytes() == index


def test_an_admitted_refresh_after_repair_is_counted_and_sent(tmp_path, monkeypatch):
    repaired_once(monkeypatch, 'full')
    spec = example(tmp_path)
    messages = Counted(spec)
    result = api.execute(spec, client=client_for(messages))
    assert result['validation_problems'] == []
    assert messages.phases[-2:] == ['report', 'report_after_repair']
    [count] = counts_for(messages, 'report_after_repair')
    sent = messages.calls[messages.phases.index('report_after_repair')]
    assert {k: count.get(k) for k in ('model', 'system', 'messages', 'thinking')} == {
        k: sent.get(k) for k in ('model', 'system', 'messages', 'thinking')}
    [row] = snapshots(spec, '_report_after_repair_context.json')
    assert saved(row)['request_sha256'] == rc.sha(rc.canonical(request_payload(sent)))
    refreshed = record(spec)['report_regenerated_after_repair']
    assert refreshed['refreshed'] is True and refreshed['changed'] == ['full']
    assert 'report_after_repair' in [r['phase'] for r in ledger._read(spec)['rows']]


def test_an_unavailable_counter_is_refused_without_dispatch_and_a_resume_recovers(tmp_path, monkeypatch):
    """A count error the dispatch would not retry is not retried either."""
    monkeypatch.setattr(api, 'MAX_ATTEMPTS', 3)
    sleeps = []
    monkeypatch.setattr(api.time, 'sleep', sleeps.append)
    spec = example(tmp_path)
    messages = Counted(spec, failures={'reconcile_full': [RuntimeError('route count unavailable')]})
    with pytest.raises(api.ContextNotAdmitted, match='reconcile_full endpoint token count unavailable'):
        api.execute(spec, client=client_for(messages))
    assert 'reconcile_full' not in messages.phases and messages.counted.count('reconcile_full') == 1
    assert sleeps == []
    [row] = snapshots(spec, '_reconcile_full_context_refused.json')
    assert saved(row)['reason'] == 'count_unavailable'
    again = Counted(spec)
    assert api.execute(replace(spec), client=client_for(again))['validation_problems'] == []
    assert again.phases == ['reconcile_full', 'report']


def test_refusal_record_shape(tmp_path):
    """A UsageLedgerError raised before the usage call begins, naming the
    phase and its numbers, with the same facts kept beside the run."""
    spec = example(tmp_path)
    messages = Counted(spec, counts={'reconcile_full': 800000})
    with pytest.raises(ledger.UsageLedgerError) as refused:
        api.execute(spec, client=client_for(messages))
    assert type(refused.value) is api.ContextNotAdmitted
    assert str(refused.value) == (
        'reconcile_full not admitted: the endpoint counted 800,000 input tokens and max_tokens is 128,000, '
        '928,000 in all, over the registered context limit of 900,000 tokens '
        f'({BASIS}); refused before dispatch and not retried')
    facts = refused_facts(spec, 'reconcile_full', 'over_window', input_tokens=800000)
    assert without_hash(refused.value.facts) == facts
    data = ledger._read(spec)
    assert data.get('pending_call') is None and 'reconcile_full' not in [r['phase'] for r in data['rows']]
    assert not snapshots(spec, '_reconcile_full_context.json')
    [row] = snapshots(spec, '_reconcile_full_context_refused.json')
    assert saved(row) == refused.value.facts


def test_a_typed_stage_refusal_names_its_stage_and_numbers(tmp_path):
    """The typed stages' own admission, with its label and numbers."""
    spec = example(tmp_path)
    messages = Counted(spec, counts={runtime.INTEGRATION_PHASE: 900000})
    with pytest.raises(ledger.UsageLedgerError, match=(
            'typed_audit_integration context count exceeds the registered window: '
            r'900,000 input tokens \+ max_tokens 4,000 > 900,000')):
        api.execute(spec, client=client_for(messages))
    assert runtime.INTEGRATION_PHASE not in messages.phases


@pytest.mark.parametrize('count', [None, -1, True, '5', 1.5])
def test_an_unusable_count_is_refused(tmp_path, count):
    spec = example(tmp_path)
    with pytest.raises(api.ContextNotAdmitted, match='report context count unavailable or unbound'):
        admit(spec, lambda **kwargs: SimpleNamespace(input_tokens=count))
    [facts] = kept(spec, 'report_context_refused.json')
    assert facts['reason'] == 'count_unusable' and facts['input_tokens'] == count
    assert not kept(spec, 'report_context.json')


def test_a_transient_count_error_is_retried_as_the_dispatch_would_be(tmp_path, monkeypatch):
    monkeypatch.setattr(api, 'MAX_ATTEMPTS', 3)
    sleeps = []
    monkeypatch.setattr(api.time, 'sleep', sleeps.append)
    spec = example(tmp_path)
    resets = 'Limit resets at: 2026-01-01 00:00:00 UTC'   # already past: the shortest stated wait
    errors = [httpx.ConnectError('synthetic reset'), _rate_limit_error(resets)]

    def counter(**kwargs):
        if errors:
            raise errors.pop(0)
        return SimpleNamespace(input_tokens=1000)
    admit(spec, counter)
    assert sleeps == [api.BACKOFF_BASE_SECONDS ** 1, 1.0]
    [facts] = kept(spec, 'report_context.json')
    assert facts['input_tokens'] == 1000 and not kept(spec, 'report_context_refused.json')


def test_a_count_still_failing_after_max_attempts_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(api, 'MAX_ATTEMPTS', 3)
    sleeps, calls = [], []
    monkeypatch.setattr(api.time, 'sleep', sleeps.append)
    spec = example(tmp_path)

    def counter(**kwargs):
        calls.append(kwargs)
        raise httpx.ConnectError('synthetic reset')
    with pytest.raises(api.ContextNotAdmitted, match='report endpoint token count unavailable: synthetic reset'):
        admit(spec, counter)
    assert len(calls) == 3
    assert sleeps == [api.BACKOFF_BASE_SECONDS ** 1, api.BACKOFF_BASE_SECONDS ** 2]
    [facts] = kept(spec, 'report_context_refused.json')
    assert facts['reason'] == 'count_unavailable'


def test_the_count_retries_what_the_dispatch_retries():
    """One classification for both: a rate limit, a dropped connection, a 5xx
    or a declared transient body is retried; anything else is not."""
    import anthropic
    request = httpx.Request('POST', 'https://example.invalid/v1/messages')

    def status(code, body=None):
        return anthropic.APIStatusError('synthetic', response=httpx.Response(code, request=request), body=body)
    assert api._transient(_rate_limit_error('slow down'))
    assert api._transient(httpx.ConnectError('synthetic reset'))
    assert api._transient(status(503))
    assert api._transient(status(200, {'type': 'error', 'error': {'type': 'overloaded_error'}}))
    assert not api._transient(status(400, {'type': 'error', 'error': {'type': 'invalid_request_error'}}))
    assert not api._transient(RuntimeError('route count unavailable'))
