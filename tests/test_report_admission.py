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

import pytest
import yaml

from data_sheets_schema import api_runner as api, chunking, dollar_readout as dr
from data_sheets_schema import receipt_completion as rc, snapshot_store, usage_ledger as ledger
import tests.test_shared_generation_runtime as sgr
from tests.test_evidence_generation_gate import specification
from tests.test_shared_generation_selection import registration_for, selected_spec

ROOT = Path(__file__).resolve().parents[1]
CHORUS_BUNDLE = ROOT / 'data/preprocessed/concatenated/CHORUS_preprocessed.txt'
ADMITTED = ('reconcile_full', 'report', 'report_regate')

#: The CHORUS fixture's dispatched wire at the base f8c5ac73c (PR #5158's head,
#: before this check existed): sha256 of the `messages.stream` keyword
#: arguments as sorted compact JSON, with the run's temporary root replaced by
#: `<root>`. They move with any model-facing input (the bundle, the schema, a
#: v10 prompt asset or carry format, the selected settings) or the fake's
#: scripted records; the admission must never move them. The second half of
#: the test re-derives them with the admission bypassed.
BASE_WIRE_SHA256 = {
    'reconcile_full': '9c1f125db0714d77aab5b028a401f23c0f019a73570d11442cead667994c0da9',
    'report': '84f509216ea460cbaa3d2a9011b825eba6c1f490750367603b5408ffdc0d383a',
    'report_regate': '13d82d2849129ca32cca15cac31b86a2a56f0e222a8c190cfd71ad377a660e46',
}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: pytest.fail('network forbidden'))
    monkeypatch.setattr(api, 'provider_identity', lambda: {'provider': None, 'base_url': None, 'key_env': None})
    monkeypatch.setattr(api, 'MAX_ATTEMPTS', 1)


def counted_phase(spec, kwargs):
    """The admitted phase a count request belongs to, read off its own wire."""
    last = [p['text'] for p in kwargs['messages'][-1]['content'] if isinstance(p, dict)][-1]
    if last.startswith('Report re-check.'):
        return 'report_regate'
    return next((p for p in ('reconcile_full', 'report')
                 if last.startswith(api.phase_instruction(p, spec.render_version).split('\n')[0])), None)


def measured(kwargs):
    """A size-proportional synthetic count, so a grown carry grows the count."""
    return len(json.dumps(kwargs['system']) + json.dumps(kwargs['messages'])) // 4


class Counted(sgr.Script):
    def __init__(self, spec, *, counts=None, padding='', **kwargs):
        super().__init__(spec, **kwargs)
        self.counts, self.padding, self.counted = counts or {}, padding, []

    def count_tokens(self, **kwargs):
        self.count_calls.append(deepcopy(kwargs))
        phase = counted_phase(self.spec, kwargs)
        self.counted.append(phase)
        value = self.counts.get(phase, 1000)
        return SimpleNamespace(input_tokens=value(kwargs) if callable(value) else value)

    def create(self, **kwargs):
        result = super().create(**kwargs)
        if self.padding and self.phases[-1] == 'report':
            text = result.content[0].text
            result.content[0].text = text.replace('# Reconciliation\n\n', '# Reconciliation\n\n' + self.padding + '\n\n', 1)
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


def wire_sha256(wire, root):
    raw = json.dumps(wire, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(raw.replace(str(root), '<root>').encode()).hexdigest()


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
        [count] = [c for c, p in zip(messages.count_calls, messages.counted) if p == phase]
        assert {k: count.get(k) for k in ('model', 'system', 'messages', 'thinking', 'extra_body')} == {
            k: wire.get(k) for k in ('model', 'system', 'messages', 'thinking', 'extra_body')}
        [row] = snapshots(spec, f'_{phase}_context.json')
        saved = json.loads(Path(row['path']).read_bytes())
        assert saved['request_sha256'] == rc.sha(rc.canonical(request_payload(wire)))
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
        saved = json.loads(Path(row['path']).read_bytes())
        assert saved == {'input_tokens': 1000, 'method': 'endpoint messages.count_tokens',
            'request_sha256': saved['request_sha256'], 'context_limit_tokens': 900000,
            'context_limit_basis': 'Synthetic assertion, not measured route capacity',
            'capacity_authority': 'caller assertion', 'phase': phase, 'attempt': 1, 'max_tokens': 128000}
    # The provenance record pins the measurement among its intermediates.
    record = yaml.safe_load(spec.provenance_path.read_bytes())
    names = {i['phase'] for i in record['intermediates'] if 'usage_id' not in i}
    assert {f'{spec.project}_reconcile_full_context.json', f'{spec.project}_report_context.json'} <= names


def test_exactly_at_the_limit_is_admitted(tmp_path):
    spec = example(tmp_path)
    messages = Counted(spec, counts={'report': 900000 - 128000})
    result = api.execute(spec, client=client_for(messages))
    assert result['validation_problems'] == [] and messages.phases[-1] == 'report'


def test_over_by_one_refuses_before_dispatch_and_is_not_retried(tmp_path, monkeypatch):
    monkeypatch.setattr(api, 'MAX_ATTEMPTS', 5)   # a retry would recount and re-send
    spec = example(tmp_path)
    messages = Counted(spec, counts={'report': 900000 - 128000 + 1})
    with pytest.raises(ledger.UsageLedgerError, match='report not admitted') as refused:
        api.execute(spec, client=client_for(messages))
    assert '772,001' in str(refused.value) and '900,000' in str(refused.value)
    assert 'report' not in messages.phases and messages.counted.count('report') == 1
    data = ledger._read(spec)
    assert data.get('pending_call') is None
    assert [r['phase'] for r in data['rows']][-1] == 'reconcile_full'
    assert not snapshots(spec, '_report_context.json') and not spec.report_path.exists()
    assert 'reconcile_full' in api._load_progress(spec)['completed']
    # Nothing billed, nothing pending, no abandoned attempt: the readout is unchanged.
    readout = dr.compute_readout(ledger.ledger_path(spec), project=spec.project)
    assert not readout['has_pending_call'] and readout['settled_calls'] == len(data['rows'])
    assert readout['settled_dollars'] == dr.price_settled_rows(data['rows'])
    assert not ledger.abandoned_journal_path(spec).exists()
    # Deterministic: a resume recounts the same request and refuses it again, still unsent.
    again = Counted(spec, counts={'report': 900000 - 128000 + 1})
    with pytest.raises(ledger.UsageLedgerError, match='report not admitted'):
        api.execute(replace(spec), client=client_for(again))
    assert again.phases == [] and again.counted.count('report') == 1
    assert ledger._read(spec)['rows'] == data['rows']


def test_a_regate_carrying_a_grown_rejected_report_is_refused(tmp_path):
    padding = 'Padding prose. ' * 40000   # 600 kB: the rejected report the regate must carry
    limit = 128000 + 100000
    spec = example(tmp_path, limit=limit)
    messages = Counted(spec, bad_report=True, padding=padding,
                       counts={p: measured for p in ADMITTED})
    with pytest.raises(ledger.UsageLedgerError, match='report_regate not admitted'):
        api.execute(spec, client=client_for(messages))
    assert messages.phases[-1] == 'report' and 'report_regate' not in messages.phases
    [regate] = [c for c, p in zip(messages.count_calls, messages.counted) if p == 'report_regate']
    [report] = [c for c, p in zip(messages.count_calls, messages.counted) if p == 'report']
    assert measured(report) + 128000 <= limit < measured(regate) + 128000
    blocks = [p['text'] for p in regate['messages'][0]['content']]
    assert any(b.startswith(api.REGATE_HEADERS[0]) and padding in b for b in blocks)
    # The one regate allowance is not consumed and the report as written stays.
    assert not ledger.report_regate_attempted(spec)
    assert padding in spec.report_path.read_text(encoding='utf-8')
    assert ledger._read(spec).get('pending_call') is None


@pytest.mark.parametrize('count', [None, -1, True, '5', 1.5])
def test_an_unusable_count_is_refused_without_dispatch(tmp_path, count):
    spec = example(tmp_path)
    messages = Counted(spec, counts={'reconcile_full': count})
    with pytest.raises(ledger.UsageLedgerError, match='reconcile_full context count unavailable'):
        api.execute(spec, client=client_for(messages))
    assert 'reconcile_full' not in messages.phases


def test_an_unavailable_counter_is_refused_without_dispatch(tmp_path):
    spec = example(tmp_path)
    messages = Counted(spec)
    original = messages.count_tokens

    def count_tokens(**kwargs):
        if counted_phase(spec, kwargs) == 'reconcile_full':
            raise RuntimeError('route count unavailable')
        return original(**kwargs)
    messages.count_tokens = count_tokens
    with pytest.raises(ledger.UsageLedgerError, match='reconcile_full endpoint token count unavailable'):
        api.execute(spec, client=client_for(messages))
    assert 'reconcile_full' not in messages.phases


def test_refusal_record_shape(tmp_path):
    """The refusal is the other admission stages' refusal: a UsageLedgerError
    raised before the usage call begins, naming the phase and its numbers."""
    spec = example(tmp_path)
    messages = Counted(spec, counts={'reconcile_full': 800000})
    with pytest.raises(ledger.UsageLedgerError) as refused:
        api.execute(spec, client=client_for(messages))
    assert type(refused.value) is ledger.UsageLedgerError
    assert str(refused.value) == (
        'reconcile_full not admitted: the endpoint counted 800,000 input tokens and max_tokens is 128,000, '
        '928,000 in all, over the registered context limit of 900,000 tokens '
        '(Synthetic assertion, not measured route capacity); refused before dispatch and not retried')
    data = ledger._read(spec)
    assert data.get('pending_call') is None and 'reconcile_full' not in [r['phase'] for r in data['rows']]
    assert not snapshots(spec, '_reconcile_full_context.json')
