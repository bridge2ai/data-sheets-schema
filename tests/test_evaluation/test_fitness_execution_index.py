"""Actual loopback execution plus captured-only fitness index; never scoring."""
import copy
import json
from pathlib import Path
import shutil
import socket
from urllib.parse import urlsplit

from click.testing import CliRunner
import pytest

from data_sheets_schema import nested_support_execution as ex
from data_sheets_schema import nested_support_results as saved
from data_sheets_schema import top_level_fitness_results as fit
from data_sheets_schema.cli.evaluate import evaluate
from data_sheets_schema.support_plan import canonical
from tests.test_evaluation.test_support_plan import fixture  # noqa: F401
from tests.test_evaluation.test_top_level_fitness_results import prepared, native  # noqa: F401
from tests.test_evaluation.test_nested_support_execution import peer, declaration  # noqa: F401

_CONNECT = socket.socket.connect


@pytest.fixture
def make(prepared, peer, tmp_path, monkeypatch):
    endpoint = urlsplit(peer['url'])
    def connect(sock, address):
        assert address == ('127.0.0.1', endpoint.port), 'non-fixture network access'
        return _CONNECT(sock, address)
    monkeypatch.setattr(socket.socket, 'connect', connect)
    peer['body'] = canonical(native(usage={'input_tokens': 12, 'output_tokens': 23,
        'cache_read_input_tokens': 0, 'cache_creation_input_tokens': 0}))
    def create(count=2, name='run-case'):
        root = tmp_path / name; root.mkdir()
        descriptor, registered, run = root / 'descriptor', root / 'registered', root / 'run'
        fit.prepare(prepared[1], descriptor, selections=prepared[3][:count], protocol=fit.FORMAT)
        value = declaration(peer, run)
        value['format'] = ex.FITNESS_FORMAT
        value['limits'].update(max_calls=count, input_scheduling_threshold=100 * count,
                               output_scheduling_threshold=417 * count)
        path = root / 'declaration.json'; path.write_bytes(canonical(value))
        registration = ex.prepare(descriptor, path, registered)
        return descriptor, registered, run, registration
    return create


def assert_no_repurchase(registered, peer, expected_calls):
    copied = registered.with_name(registered.name + '-copied')
    shutil.copytree(registered, copied)
    with pytest.raises(ValueError, match='exist'):
        ex.run(copied)
    assert len(peer['requests']) == expected_calls


def test_actual_http_cli_index_relocates_entire_ledger_and_never_dispatches(make, prepared, peer, tmp_path, monkeypatch):
    descriptor, registered, run, registration = make()
    report = ex.run(registered)
    assert report['all_selected_accepted'] and len(peer['requests']) == 2
    for request, observed in zip(registration['requests'], peer['requests']):
        assert observed['raw'] == (registered / 'artifacts' / request['effective_request']['sha256']).read_bytes()
        body = json.loads(observed['raw'])
        assert body['model'] == 'judge' and body['max_tokens'] == 417 and body['stream'] is False
        assert isinstance(body['messages'][0]['content'], str)
    index = tmp_path / 'index'
    result = CliRunner().invoke(evaluate, ['fitness-results', 'index', '--descriptor', str(descriptor),
        '--execution', str(run), '--output', str(index)])
    assert result.exit_code == 0, result.output
    value = json.loads(result.output)
    assert value['mode'] == 'local_fixture' and value['scientific_scoring_eligible'] is False
    assert all(x is None for x in value['decision_references'].values())
    assert value['execution']['report'] == report
    assert value['readiness'] == registration['original_readiness']
    assert value['strata']['fitness_top_level'] == {'selected': 2, 'accepted': 2, 'rejected': 0, 'missing': 0}
    assert all(r['state'] == r['dispatch_state'] == 'accepted' and r['spent'] is True for r in value['fitness_rows'])
    assert all(r['result'] is None for r in value['fitness_rows'])  # No invented result file.
    assert_no_repurchase(registered, peer, 2)
    relocated = tmp_path / 'relocated'; shutil.copytree(index, relocated)
    for path in (prepared[0], prepared[1], descriptor, registered, run, index):
        path.rename(path.with_name(path.name + '-unavailable'))
    old = Path.read_bytes
    def captured_only(path):
        assert path.is_relative_to(relocated), path
        return old(path)
    monkeypatch.setattr(Path, 'read_bytes', captured_only)
    monkeypatch.setattr(socket.socket, 'connect', lambda *_: pytest.fail('index recheck attempted network'))
    monkeypatch.setattr(ex, '_dispatch', lambda *_: pytest.fail('index recheck dispatched'))
    assert fit.recheck_index(relocated) == value


@pytest.mark.parametrize('fault', ['http_429', 'truncated', 'unknown_usage'])
def test_failed_transport_or_accounting_cannot_promote_raw_score(make, peer, tmp_path, fault):
    descriptor, registered, run, _ = make()
    if fault == 'http_429': peer['status'] = 429
    elif fault == 'truncated':
        body = json.loads(peer['body']); body['stop_reason'] = 'max_tokens'
        peer['body'] = canonical(body)
    else:
        peer['body'] = canonical(native())
    report = ex.run(registered)
    assert len(peer['requests']) == 1 and report['rows'][0]['status'] == 'failed'
    value = fit.build_index(descriptor, [], tmp_path / 'index', execution=run)
    failed, later = value['fitness_rows']
    assert failed['state'] == 'rejected' and failed['dispatch_state'] == 'failed' and failed['spent'] is True
    assert later['state'] == 'missing' and later['dispatch_state'] == 'not_started' and later['spent'] is False
    assert value['strata']['fitness_top_level']['accepted'] == 0
    if fault == 'truncated':
        assert failed['assessment']['status'] == 'rejected' and failed['assessment']['fitness'] is None
    else:
        assert failed['assessment']['status'] == 'accepted' and failed['assessment']['fitness'] == .75
    assert value['scientific_scoring_eligible'] is False
    assert fit.recheck_index(tmp_path / 'index') == value
    assert_no_repurchase(registered, peer, 1)


@pytest.mark.parametrize('boundary', ['admitted', 'response', 'settled'])
def test_real_http_interruption_retains_unknown_and_recovers_only_complete_raw_response(make, peer, tmp_path, monkeypatch, boundary):
    descriptor, registered, run, _ = make()
    actual = ex._exclusive
    def interrupt(path, raw):
        if path.name == boundary + '.json':
            raise OSError('invented publication interruption')
        return actual(path, raw)
    with monkeypatch.context() as local:
        local.setattr(ex, '_exclusive', interrupt)
        with pytest.raises(OSError, match='invented publication'):
            ex.run(registered)
    value = fit.build_index(descriptor, [], tmp_path / 'index', execution=run)
    first, second = value['fitness_rows']
    expected = {'admitted': ('not_started', False, 'missing', 0),
                'response': ('spent_unknown', True, 'missing', 1),
                'settled': ('accepted', True, 'accepted', 1)}[boundary]
    assert (first['dispatch_state'], first['spent'], first['state'], len(peer['requests'])) == expected
    assert second['dispatch_state'] == 'not_started' and second['spent'] is False
    assert value['execution']['saved_report'] is None
    assert_no_repurchase(registered, peer, expected[-1])
    assert fit.recheck_index(tmp_path / 'index') == value


@pytest.mark.parametrize('mutation', ['report_flag', 'unknown_ledger', 'missing_preceding_settlement', 'missing_body', 'unadmitted_gap'])
def test_portable_index_rechecks_actual_ledger_not_stored_flags(make, peer, tmp_path, mutation):
    descriptor, registered, run, _ = make()
    ex.run(registered)
    output = tmp_path / 'index'
    value = fit.build_index(descriptor, [], output, execution=run)
    changed = copy.deepcopy(value)
    if mutation == 'report_flag': changed['execution']['report']['all_selected_accepted'] = False
    elif mutation == 'unknown_ledger': changed['execution']['ledger']['format'] = 'foreign'
    elif mutation == 'missing_preceding_settlement': changed['execution']['ledger']['attempts'][0]['settled'] = None
    elif mutation == 'unadmitted_gap':
        changed['execution']['ledger']['attempts'][0] = {'admitted': None, 'response': None, 'settled': None}
    else:
        response = changed['execution']['report']['rows'][0]['saved_result']['response']
        (output / 'artifacts' / response['sha256']).unlink()
    (output / 'index.json').write_bytes(canonical(changed))
    with pytest.raises((ValueError, OSError), match='unadmitted empty entry must be terminal' if mutation == 'unadmitted_gap' else None):
        fit.recheck_index(output)
    assert len(peer['requests']) == 2


@pytest.mark.parametrize('foreign', ['descriptor', 'standalone_result', 'saved_report'])
def test_execution_join_refuses_foreign_descriptor_result_or_report(make, prepared, peer, tmp_path, foreign):
    descriptor, registered, run, _ = make()
    ex.run(registered)
    results = []
    if foreign == 'descriptor':
        descriptor = tmp_path / 'different-descriptor'
        fit.prepare(prepared[1], descriptor, selections=prepared[3][1:3], protocol=fit.FORMAT)
    elif foreign == 'saved_report':
        path = run / 'report.json'; report = json.loads(path.read_bytes())
        report['admitted_calls'] = 0; path.write_bytes(canonical(report))
    else:
        aid = prepared[3][0]['attempt_id']
        body = json.loads(peer['body']); body['content'][0]['text'] = json.dumps({'fitness': .2, 'failure': 'form', 'reason': 'Different invented response.'})
        response = tmp_path / 'response.json'
        response.write_bytes(fit.package_response((descriptor / 'descriptor.json').read_bytes(), attempt_id=aid, native_message=canonical(body)))
        result = tmp_path / 'result'; fit.accept(descriptor, response, result, attempt_id=aid); results.append(result)
    output = tmp_path / 'index'
    with pytest.raises(ValueError):
        fit.build_index(descriptor, results, output, execution=run)
    assert not output.exists() and len(peer['requests']) == 2
