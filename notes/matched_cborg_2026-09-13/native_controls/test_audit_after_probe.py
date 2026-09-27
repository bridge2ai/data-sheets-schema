"""An audit whose immediate predecessor is a transport probe (#2469); synthetic lineages only."""
import copy
import json
from pathlib import Path

import httpx
import pytest

from budgeted_cborg import BudgetStop
from audit_controls import probe_predecessor
from audit_controls import registration as r
import transport_probe as probe
from test_transport_probe import (Upstream, lineage, prepared, run, save, sha, ok_stream,  # noqa: F401  (fixtures)
                                  accounting)


def completed(lin):
    return run(lin, Upstream(ok_stream))


def refused(lin):
    """A 400 leaves the probe's one row pending; the standing debit reconciles it."""
    return run(lin, Upstream(lambda request, clock: httpx.Response(400, json={'error': 'synthetic'})))


def successor(lin, result):
    """The next audit: the first audit's registration, continued from the probe's checkpoint."""
    first = r.read_json(lin.source)
    manifest = copy.deepcopy(first)
    manifest['job'] = {**first['job'], 'id': 'after_probe', 'attempt_dir': str(lin.root / 'after' / 'attempts' / 'after_probe')}
    checkpoint = Path(result['successor_continues_from'])
    continuation = {'checkpoint': str(checkpoint), 'sha256': sha(checkpoint), 'cost_usd': result['successor_cost_usd']}
    out = lin.root / 'probe'
    if checkpoint.name == 'reconciled_billing.json':
        continuation['reconciliation'] = {'source_registration': str(out / 'registration.json'),
                                          'source_ledger': str(out / 'billing.json'),
                                          'receipt': str(out / 'debit_receipt.json'),
                                          'result': str(out / 'result.json')}
    manifest['budget'] = {**first['budget'], 'per_job_attempt_usd': {'after_probe': 20},
                          'ledger_path': str(lin.root / 'after' / 'billing.json'), 'continuation': continuation}
    repin(manifest)
    return manifest, lin.root / 'after' / 'registration.json'


def repin(manifest):
    bridge = manifest['budget']['continuation'].get('reconciliation') or {}
    names = {manifest['budget']['continuation']['checkpoint'], *bridge.values(),
             *map(str, probe_predecessor.paths(manifest))}
    manifest['pinned_files'].update({name: sha(name) for name in names})


def continue_after(lin, manifest, path):
    save(path, manifest)
    identity = r.sha(path)
    with r.sequence_guard(manifest, identity):
        ledger = r.open_audit_ledger(manifest, path, identity)
    return identity, r.read_json(ledger.path)


@pytest.mark.parametrize('outcome', [completed, refused])
def test_an_audit_continues_from_the_probe_and_takes_the_tip(prepared, outcome):
    result = outcome(prepared)
    manifest, path = successor(prepared, result)
    assert probe_predecessor.is_probe_predecessor(manifest)
    identity, state = continue_after(prepared, manifest, path)
    carried = r.read_json(result['successor_continues_from'])['requests']
    assert state['requests'] == carried and state['continued_from']['manifest_sha256'] == prepared.identity
    tip = json.loads(prepared.state.read_text())
    assert tip['registration_sha256'] == identity and tip['ledger_path'] == manifest['budget']['ledger_path']
    # The debit's receipt and the probe's link are pinned by the successor's registration.
    assert {str(prepared.root / 'probe' / name) for name in ('registration.json', 'billing.json', 'result.json')} \
        <= set(manifest['pinned_files'])


def test_an_audit_from_the_tip_before_the_probe_is_a_fork(prepared):
    completed(prepared)
    first = r.read_json(prepared.source)
    manifest = copy.deepcopy(first)
    manifest['job'] = {**first['job'], 'id': 'forked'}
    reconciliation = {'source_registration': str(prepared.source), 'source_ledger': str(prepared.tip_ledger),
                      'receipt': str(prepared.receipt),
                      'result': str(Path(first['job']['attempt_dir']) / 'result.json')}
    manifest['budget'] = {**first['budget'], 'per_job_attempt_usd': {'forked': 20},
                          'ledger_path': str(prepared.root / 'fork' / 'billing.json'),
                          'continuation': {'checkpoint': str(prepared.checkpoint), 'sha256': sha(prepared.checkpoint),
                                           'cost_usd': '0', 'reconciliation': reconciliation}}
    repin(manifest)
    path = save(prepared.root / 'fork' / 'registration.json', manifest)
    with pytest.raises(BudgetStop, match='current sequence tip'):
        with r.sequence_guard(manifest, r.sha(path)):
            pass


def _tamper(lin, manifest, name, change):
    target = lin.root / 'probe' / name
    value = r.read_json(target)
    change(value)
    save(target, value)
    if name == 'reconciled_billing.json':
        # Rebind the result to the changed file, so only the recomputation can refuse it.
        result = lin.root / 'probe' / 'result.json'
        recorded = r.read_json(result)
        recorded['settlement']['sha256'] = sha(target)
        save(result, recorded)
    if name in ('billing.json', 'reconciled_billing.json'):
        manifest['budget']['continuation']['sha256'] = sha(manifest['budget']['continuation']['checkpoint'])
    repin(manifest)


@pytest.mark.parametrize('name, change, match', [
    ('reconciled_billing.json', lambda v: v['requests'][-1].update(cost_usd='0.01'), 'beyond the one debit'),
    ('reconciled_billing.json', lambda v: v['requests'][0].update(cost_usd='0'), 'beyond the one debit'),
    ('debit_receipt.json', lambda v: v['user_authorization'].update(exact_response='another'), 'standing authorization'),
    ('debit_receipt.json', lambda v: v['runtime_at_settlement'].update(unfinished_handlers=1), 'closed runtime'),
    ('result.json', lambda v: v.update(tip_claimed=False), 'did not claim the tip'),
    ('result.json', lambda v: v['settlement'].update(status='needs_person'), 'needs a person'),
])
def test_a_changed_probe_link_is_refused(prepared, name, change, match):
    manifest, path = successor(prepared, refused(prepared))
    _tamper(prepared, manifest, name, change)
    save(path, manifest)
    with pytest.raises(BudgetStop, match=match):
        r.validate_audit_reconciliation(manifest)


@pytest.mark.parametrize('change, match', [
    (lambda v: v['requests'].append({**v['requests'][-1], 'id': 'extra'}), 'at most its one request'),
    (lambda v: v['requests'][0].update(cost_usd='0'), 'carry its predecessor checkpoint'),
    (lambda v: v.update(additional_cap_usd='800'), 'changes the lineage caps'),
])
def test_a_settled_probe_ledger_must_carry_its_predecessor_and_one_request(prepared, change, match):
    manifest, path = successor(prepared, completed(prepared))
    _tamper(prepared, manifest, 'billing.json', change)
    with pytest.raises(BudgetStop, match=match):
        probe_predecessor.validate_link(manifest)


def test_an_unpinned_probe_link_is_refused(prepared):
    manifest, _ = successor(prepared, completed(prepared))
    del manifest['pinned_files'][str(prepared.root / 'probe' / 'result.json')]
    with pytest.raises(BudgetStop, match='registered input'):
        probe_predecessor.validate_link(manifest)


def test_a_reconciled_probe_is_continued_only_through_its_bridge_and_a_settled_one_without(prepared):
    manifest, _ = successor(prepared, refused(prepared))
    del manifest['budget']['continuation']['reconciliation']
    with pytest.raises(BudgetStop, match='checkpoint its settlement wrote'):
        probe_predecessor.validate_link(manifest)


def test_a_reconciled_checkpoint_not_the_one_the_result_names_is_refused(prepared):
    manifest, _ = successor(prepared, refused(prepared))
    target = prepared.root / 'probe' / 'reconciled_billing.json'
    save(target, {**r.read_json(target), 'note': 'changed'})
    manifest['budget']['continuation']['sha256'] = sha(target)
    repin(manifest)
    with pytest.raises(BudgetStop, match='checkpoint its settlement wrote'):
        r.validate_audit_reconciliation(manifest)


def test_a_settled_probe_is_not_continued_through_a_bridge(prepared):
    result = completed(prepared)
    manifest, _ = successor(prepared, result)
    out = prepared.root / 'probe'
    manifest['budget']['continuation']['reconciliation'] = {
        'source_registration': str(out / 'registration.json'), 'source_ledger': str(out / 'billing.json'),
        'receipt': str(out / 'result.json'), 'result': str(out / 'result.json')}
    repin(manifest)
    with pytest.raises(BudgetStop, match='own ledger, with no reconciliation'):
        probe_predecessor.validate_link(manifest)


@pytest.mark.parametrize('change, match', [
    (lambda v: v.update(kind='something_else'), 'did not follow an audit of this origin'),
    (lambda v: v.update(note='edited after the probe'), 'own predecessor changed'),
])
def test_the_probes_own_predecessor_must_be_an_unchanged_audit_of_the_origin(prepared, change, match):
    manifest, _ = successor(prepared, completed(prepared))
    source = r.read_json(prepared.source)
    change(source)
    save(prepared.source, source)
    repin(manifest)
    with pytest.raises(BudgetStop, match=match):
        probe_predecessor.validate_link(manifest)


def test_the_names_are_the_probes():
    assert (probe_predecessor.KIND, probe_predecessor.RESULT_KIND, probe_predecessor.ATTEMPT,
            probe_predecessor.DEBIT_KIND, probe_predecessor.HANDLER_RUNNING, probe_predecessor.AUDIT_KIND) == (
        probe.KIND, probe.RESULT_KIND, probe.ATTEMPT, probe.DEBIT_KIND, probe.HANDLER_RUNNING, probe.AUDIT_KIND)


def test_an_audit_continues_after_a_debit_settle_applied_once_the_probe_exited(prepared, monkeypatch):
    from test_transport_probe import _unfinished
    from decimal import Decimal
    _unfinished(monkeypatch)
    result = refused(prepared)
    assert result['settlement']['reason'] == probe.HANDLER_RUNNING and result['successor_continues_from'] is None
    # Before `settle`, the link has no settled checkpoint to hand on.
    manifest, _ = successor(prepared, {**result, 'successor_continues_from': str(prepared.root / 'probe' / 'billing.json'),
                                       'successor_cost_usd': '0'})
    with pytest.raises(BudgetStop, match='needs a person'):
        probe_predecessor.validate_link(manifest)
    settlement = probe.settle(prepared.registration, prepared.identity)
    cost = str(sum((Decimal(row['cost_usd']) for row in r.read_json(settlement['path'])['requests']), Decimal(0)))
    manifest, path = successor(prepared, {'successor_continues_from': settlement['path'], 'successor_cost_usd': cost})
    assert str(prepared.root / 'probe' / 'settlement_after_exit.json') in manifest['pinned_files']
    continue_after(prepared, manifest, path)
    # A settlement-after-exit that names another result is refused.
    after = prepared.root / 'probe' / 'settlement_after_exit.json'
    save(after, {**r.read_json(after), 'result_sha256': '0' * 64})
    repin(manifest)
    with pytest.raises(BudgetStop, match='names another result'):
        probe_predecessor.validate_link(manifest)


# --- the wiring, each through its real caller (#2506) ------------------------------------------

def test_the_sequence_guard_refuses_a_changed_settled_probe_link(prepared):
    manifest, path = successor(prepared, completed(prepared))
    _tamper(prepared, manifest, 'billing.json', lambda v: v['requests'][0].update(cost_usd='0'))
    save(path, manifest)
    before = prepared.state.read_bytes()
    with pytest.raises(BudgetStop, match='carry its predecessor checkpoint'):
        with r.sequence_guard(manifest, r.sha(path)):
            pass
    assert prepared.state.read_bytes() == before


@pytest.mark.parametrize('outcome', [completed, refused])
def test_the_registration_pins_every_file_of_the_probe_link(prepared, outcome):
    manifest, _ = successor(prepared, outcome(prepared))
    out = prepared.root / 'probe'
    expected = {out / 'registration.json', out / 'billing.json', out / 'result.json', prepared.source}
    if outcome is refused:
        expected |= {out / 'reconciled_billing.json', out / 'debit_receipt.json'}
    assert expected <= r.continuation_paths(manifest)


def test_the_settlement_after_exit_is_pinned_and_checked(prepared, monkeypatch):
    from test_transport_probe import _unfinished
    from decimal import Decimal
    _unfinished(monkeypatch)
    refused(prepared)
    settlement = probe.settle(prepared.registration, prepared.identity)
    cost = str(sum((Decimal(row['cost_usd']) for row in r.read_json(settlement['path'])['requests']), Decimal(0)))
    manifest, _ = successor(prepared, {'successor_continues_from': settlement['path'], 'successor_cost_usd': cost})
    after = prepared.root / 'probe' / 'settlement_after_exit.json'
    assert after in r.continuation_paths(manifest)
    save(after, {**r.read_json(after), 'closure_basis': 'edited'})
    with pytest.raises(BudgetStop, match='registered input'):
        probe_predecessor.validate_link(manifest)


@pytest.mark.parametrize('outcome', [refused])
def test_an_amendment_candidate_bridges_to_the_probes_own_result(prepared, outcome, tmp_path):
    """#2512: through the amendment candidate, which builds its bridge with the same
    continuation_bridge prepare() registers (#2640). A probe's result sits beside its
    registration; an audit's sits in its job's attempt directory."""
    from audit_controls.prepare import amendment_candidate
    result = outcome(prepared)
    origin = tmp_path / 'origin.json'
    save(origin, {'repository': str(prepared.root), 'budget': {'per_attempt_usd': '5',
                                                             'ledger_path': str(prepared.root / 'origin_billing.json')}})
    out = prepared.root / 'probe'
    candidate = amendment_candidate(origin, {'total_usd': '800'}, result['successor_continues_from'],
                                    source_registration=out / 'registration.json',
                                    reconciliation_receipt=out / 'debit_receipt.json')
    assert candidate['budget']['continuation']['reconciliation'] == {
        'source_registration': str(out / 'registration.json'), 'source_ledger': str(out / 'billing.json'),
        'receipt': str(out / 'debit_receipt.json'), 'result': str(out / 'result.json')}
    first = r.read_json(prepared.source)
    candidate = amendment_candidate(origin, {'total_usd': '800'}, result['successor_continues_from'],
                                    source_registration=prepared.source, reconciliation_receipt=out / 'debit_receipt.json')
    assert candidate['budget']['continuation']['reconciliation']['result'] == \
        str(Path(first['job']['attempt_dir']) / 'result.json')


# --- the probe link on a complete registration (#2509, #2512) ---------------------------------
# The synthetic probe lineage above is not a complete audit registration, so these prove the
# wiring on a real prepared audit: validate_registration and required_paths reach the probe
# link's check and pins. What those return for a probe is tested above.

from audit_controls.test_context_preparation import ancestry  # noqa: E402,F401  (fixture)


def test_validate_registration_checks_the_probe_link(ancestry, tmp_path, monkeypatch):
    """#2509: deleting the #2505 call in validate_registration fails this test."""
    from audit_controls import prepare
    path = prepare.prepare(**ancestry[0], destination=tmp_path / 'audit')
    seen = []

    def checked(manifest, *, require_pins=True):
        seen.append((manifest['budget']['continuation']['checkpoint'], require_pins))
        raise BudgetStop('probe link checked')
    monkeypatch.setattr(probe_predecessor, 'validate_predecessor', checked)
    with pytest.raises(BudgetStop, match='probe link checked'):
        r.validate_registration(path)
    assert seen == [(r.read_json(path)['budget']['continuation']['checkpoint'], True)]


def test_required_paths_pin_the_probe_link(ancestry, tmp_path, monkeypatch):
    """#2512: the registration's own pin set, not only continuation_paths, carries the link."""
    from audit_controls import prepare
    path = prepare.prepare(**ancestry[0], destination=tmp_path / 'audit')
    link = tmp_path / 'probe_link_file.json'
    link.write_text('{}')
    monkeypatch.setattr(probe_predecessor, 'paths', lambda manifest: {link})
    assert link in r.required_paths(r.read_json(path))


def test_a_validator_defect_is_named_with_its_error_and_place(prepared, monkeypatch):
    """#2514: still a BudgetStop, but it says which error was raised where, and its message."""
    manifest, _ = successor(prepared, completed(prepared))

    def defect(manifest, *, require_pins=True):
        return {}['a key the validator forgot']
    monkeypatch.setattr(probe_predecessor, '_validate_link', defect)
    with pytest.raises(BudgetStop, match=r"^probe predecessor is malformed or unavailable "
                       r"\(KeyError at test_audit_after_probe\.py:\d+: 'a key the validator forgot'\)$") as caught:
        probe_predecessor.validate_link(manifest)
    assert isinstance(caught.value.__cause__, KeyError)


@pytest.mark.parametrize('wrapper, patched, refusal', [
    ('paths', '_paths', 'audit predecessor evidence is malformed or unavailable'),
    ('validate_predecessor', 'predecessor_path', 'audit predecessor registration is malformed or unavailable'),
], ids=['paths', 'validate_predecessor'])
def test_each_wrapper_names_the_error_it_caught(prepared, monkeypatch, wrapper, patched, refusal):
    """#2642: the other two wrappers carry the error's class, place and message too."""
    manifest, _ = successor(prepared, completed(prepared))

    def defect(*args, **kwargs):
        raise KeyError('a key the wrapper forgot')
    monkeypatch.setattr(probe_predecessor, patched, defect)
    with pytest.raises(BudgetStop, match=rf"^{refusal} \(KeyError at test_audit_after_probe\.py:\d+: "
                       r"'a key the wrapper forgot'\)$") as caught:
        getattr(probe_predecessor, wrapper)(manifest)
    assert isinstance(caught.value.__cause__, KeyError)          # the original stays chained (#2660)


def test_a_library_frame_is_never_resolved_against_the_working_directory(tmp_path, monkeypatch):
    """#2659: a pseudo-filename frame (`<frozen ...>`) is not taken for the controls' own
    code when the working directory lies inside them, and a working directory that is
    gone does not make the refusal itself raise. The pseudo-filename frame is built here,
    so the test runs on every interpreter, not only where posixpath is frozen (#2672)."""
    library = compile('raise FileNotFoundError(2, "synthetic")', '<frozen synthetic>', 'exec')
    own_file = probe_predecessor._CONTROLS / 'synthetic_own.py'
    namespace = {'library': library}
    exec(compile('def read_missing():\n    exec(library)\n', str(own_file), 'exec'), namespace)
    try:
        namespace['read_missing']()
    except OSError as error:
        caught = error
    monkeypatch.chdir(probe_predecessor._CONTROLS)
    message = str(probe_predecessor._malformed('probe', caught))
    assert ' at synthetic_own.py:2 via <frozen synthetic>:1' in message, message
    gone = tmp_path / 'gone'; gone.mkdir(); monkeypatch.chdir(gone); gone.rmdir()
    refusal = probe_predecessor._malformed('probe', caught)
    assert isinstance(refusal, BudgetStop) and 'FileNotFoundError at synthetic_own.py:2' in str(refusal)


@pytest.mark.parametrize('filename', ['/controls/x\x00y.py', '/controls/\ud800.py'], ids=['nul', 'surrogate'])
def test_a_frame_whose_path_cannot_be_resolved_is_not_the_controls_own(filename):
    """#2673: an absolute filename that resolve() refuses counts as not own, rather than
    making the refusal raise inside the wrappers' handlers. No source lookup, so the
    frame is built on every interpreter (#2689)."""
    import traceback
    assert not probe_predecessor._own(traceback.FrameSummary(filename, 1, 'f', lookup_line=False))


def test_a_symlink_loop_frame_is_not_the_controls_own(monkeypatch):
    """#2690: resolve() raises RuntimeError on a symlink loop up to 3.12; that counts as
    not own too. Modelled on every interpreter."""
    import traceback
    def loop(self, strict=False):
        raise RuntimeError(f'Symlink loop from {self}')
    monkeypatch.setattr(Path, 'resolve', loop)
    assert not probe_predecessor._own(traceback.FrameSummary('/controls/a.py', 1, 'f', lookup_line=False))


def test_a_frame_imported_through_a_symlinked_path_is_the_controls_own(tmp_path):
    """#2690: a frame's filename keeps the spelling it was imported by; the controls
    imported through a symlink (macOS /tmp) are still their own."""
    import traceback
    alias = tmp_path / 'controls_alias'
    alias.symlink_to(probe_predecessor._CONTROLS, target_is_directory=True)
    frame = traceback.FrameSummary(str(alias / 'audit_controls' / 'probe_predecessor.py'), 1, 'f', lookup_line=False)
    assert probe_predecessor._own(frame)


def test_a_malformed_refusal_names_its_frame_without_reading_source():
    """#2689: _malformed never looks up source lines, so a frame whose filename linecache
    cannot stat still yields a named BudgetStop."""
    import linecache
    def refuse(*args, **kwargs):
        raise UnicodeEncodeError('utf-8', '\ud800', 0, 1, 'surrogates not allowed')
    try:
        {}['k']
    except KeyError as error:
        caught = error
    # linecache is patched only around the one call: pytest and the warnings
    # machinery read source through it too.
    saved = {name: getattr(linecache, name) for name in ('getline', 'updatecache', 'checkcache')}
    try:
        for name in saved:
            setattr(linecache, name, refuse)
        refusal = probe_predecessor._malformed('probe', caught)
    finally:
        for name, function in saved.items():
            setattr(linecache, name, function)
    assert isinstance(refusal, BudgetStop) and 'KeyError at test_audit_after_probe.py:' in str(refusal)


@pytest.mark.parametrize('spelling', ['probe', 'other/../probe', 'link'], ids=['relative', 'dotdot', 'symlink'])
def test_the_bridge_canonicalises_operator_paths(prepared, tmp_path, monkeypatch, spelling):
    """#2690, #2705: the CLI passes the source registration and receipt as typed; relative,
    `..` and symlinked spellings are all registered canonical, in every key of the bridge."""
    from audit_controls.prepare import continuation_bridge
    refused(prepared)
    out = prepared.root / 'probe'
    (out.parent / 'other').mkdir(exist_ok=True)
    if spelling == 'link':
        (out.parent / 'link').symlink_to(out, target_is_directory=True)
    monkeypatch.chdir(out.parent)
    bridge = continuation_bridge(f'{spelling}/registration.json', f'{spelling}/debit_receipt.json')
    probe_registration = json.loads((out / 'registration.json').read_text())
    assert bridge == {'source_registration': str(out / 'registration.json'),
                      'source_ledger': probe_registration['budget']['ledger_path'],
                      'receipt': str(out / 'debit_receipt.json'), 'result': str(out / 'result.json')}


def test_controls_imported_through_a_symlink_still_name_their_own_frame(tmp_path):
    """#2706: _CONTROLS is resolved, so controls imported through a symlinked spelling
    (macOS /tmp, a symlinked home) still find their own frame in a refusal."""
    import subprocess, sys
    alias = tmp_path / 'controls_alias'
    alias.symlink_to(probe_predecessor._CONTROLS, target_is_directory=True)
    repository = probe_predecessor._CONTROLS.parents[1]
    code = (
        "import sys\n"
        f"sys.path[:0] = [{str(alias)!r}, {str(alias / 'native_controls')!r}, {str(repository)!r}, "
        f"{str(repository / 'src')!r}]\n"
        "from audit_controls import probe_predecessor as p\n"
        f"manifest = {{'budget': {{'continuation': {{'checkpoint': {str(tmp_path / 'missing.json')!r}}}}}}}\n"
        "try:\n"
        "    p.validate_predecessor(manifest)\n"
        "except Exception as error:\n"
        "    print(p._CONTROLS == p._CONTROLS.resolve(), error)\n")
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith('True ') and ' at registration.py:' in result.stdout, result.stdout


def test_a_refusal_names_the_line_that_raised_in_a_frame_still_running():
    """#2707: the refusal names the line where the error passed through the wrapper's own
    frame, from the traceback, not the frame's current line (the handler's)."""
    import inspect
    lines, start = inspect.getsourcelines(probe_predecessor.validate_predecessor)
    raised = start + next(i for i, line in enumerate(lines) if "manifest['budget']['continuation']" in line)
    with pytest.raises(BudgetStop) as caught:
        probe_predecessor.validate_predecessor({})
    assert f'(KeyError at probe_predecessor.py:{raised}: ' in str(caught.value), str(caught.value)



def test_an_error_raised_in_a_library_is_located_in_the_controls_code(prepared):
    """#2641: a malformed probe file fails inside the JSON decoder; the refusal names the
    controls' own frame that read it, and the decoder after `via`."""
    manifest, _ = successor(prepared, completed(prepared))
    (prepared.root / 'probe' / 'registration.json').write_bytes(b'not json')
    with pytest.raises(BudgetStop, match=r"^probe predecessor is malformed or unavailable \(JSONDecodeError "
                       r"at registration\.py:\d+ via decoder\.py:\d+: Expecting value"):
        probe_predecessor.validate_link(manifest, require_pins=False)


def test_prepare_registers_the_bridge_to_the_probes_own_result(ancestry, tmp_path, monkeypatch):
    """#2640: prepare() builds the bridge it registers with continuation_bridge, the builder the
    amendment candidate uses, so the probe case tested there is the one registered. The probe
    link's own checks are stubbed here; they are tested above on a real probe lineage."""
    from audit_controls import prepare as audit_prepare
    args = ancestry[0]
    probe = tmp_path / 'probe'
    source = save(probe / 'registration.json', {'kind': probe_predecessor.KIND,
                                                'budget': {'ledger_path': str(probe / 'billing.json')}})
    save(probe / 'billing.json', {'synthetic': 'the probe ledger'})
    save(probe / 'result.json', {'synthetic': 'the probe result'})
    receipt = save(probe / 'debit_receipt.json', {'synthetic': 'the probe debit'})
    monkeypatch.setattr(probe_predecessor, 'validate_predecessor', lambda manifest, **_: None)
    monkeypatch.setattr(probe_predecessor, 'paths', lambda manifest: set())
    built, real = [], audit_prepare.continuation_bridge
    monkeypatch.setattr(audit_prepare, 'continuation_bridge', lambda *given: built.append(real(*given)) or built[-1])
    path = audit_prepare.prepare(**args, destination=tmp_path / 'after_probe',
                                 continuation_checkpoint=args['reconciled_checkpoint'],
                                 continuation_source_registration=source, continuation_reconciliation_receipt=receipt)
    registered = r.read_json(path)['budget']['continuation']['reconciliation']
    assert built == [registered] == [{'source_registration': str(source), 'source_ledger': str(probe / 'billing.json'),
                                      'receipt': str(receipt), 'result': str(probe / 'result.json')}]


def test_the_amendment_candidate_names_the_sequence_state_the_registration_will(tmp_path):
    from audit_controls.prepare import amendment_candidate
    ledger = save(tmp_path / 'origin' / 'billing.json', {'requests': [{'cost_usd': '1.5'}]})
    origin = save(tmp_path / 'origin' / 'registration.json',
                  {'budget': {'ledger_path': str(ledger), 'per_attempt_usd': '5'}})
    candidate = amendment_candidate(origin, {'total_usd': '600'}, ledger)
    assert candidate['sequence_state'] == str(ledger.with_name('audit_sequence.json'))
    assert candidate['budget']['continuation']['cost_usd'] == '1.5'
    # A relative origin ledger resolves against the origin's repository, as the registration's does.
    relative = save(tmp_path / 'origin' / 'relative.json',
                    {'repository': str(tmp_path / 'repo'), 'budget': {'ledger_path': 'runs/billing.json',
                                                                      'per_attempt_usd': '5'}})
    assert amendment_candidate(relative, {'total_usd': '600'}, ledger)['sequence_state'] == str(
        tmp_path / 'repo' / 'runs' / 'audit_sequence.json')


def _v1_on(reference, total='400'):
    """A v1 selection whose predecessor is `reference`; its other documents are never read here."""
    ref = {'path': str(reference), 'sha256': sha(reference)}
    other = lambda name: {'path': str(reference.parent / name), 'sha256': '0' * 64}
    return {'kind': 'additive_sequence_budget_v1', 'origin_registration': other('origin.json'),
            'predecessor_registration': ref, 'predecessor_ledger': other('ledger.json'),
            'predecessor_owner': other('owner.json'), 'authorization': other('authority.json'),
            'prior_total_usd': total, 'increase_usd': '200', 'total_usd': str(int(total) + 200),
            'default_attempt_usd': '5'}


@pytest.mark.parametrize('outcome', [completed, refused])
def test_an_amended_audit_may_name_the_probe_as_its_predecessor(prepared, outcome):
    manifest, _ = successor(prepared, outcome(prepared))
    registration = prepared.root / 'probe' / 'registration.json'
    candidate = {key: manifest[key] for key in ('kind', 'parent', 'budget', 'sequence_state')}
    candidate.update(budget_amendment=_v1_on(registration), pinned_files={})
    previous = r.read_json(manifest['budget']['continuation']['checkpoint'])
    assert r.validate_budget_amendment_predecessor(candidate, previous, require_pins=False) == registration
    # Naming the audit before the probe as the predecessor is refused.
    candidate['budget_amendment'] = _v1_on(prepared.source)
    with pytest.raises(BudgetStop, match='authorized predecessor'):
        r.validate_budget_amendment_predecessor(candidate, previous, require_pins=False)
    # A candidate that names no sequence state is refused, never a KeyError (#2504).
    del candidate['sequence_state']
    with pytest.raises(BudgetStop, match='no sequence state'):
        r.validate_budget_amendment_predecessor(candidate, previous, require_pins=False)


def test_a_malformed_probe_ledger_is_a_budget_stop(prepared):
    manifest, _ = successor(prepared, completed(prepared))
    (prepared.root / 'probe' / 'billing.json').write_text('[]\n')
    repin(manifest)
    with pytest.raises(BudgetStop, match='malformed'):
        probe_predecessor.validate_link(manifest)


def test_a_settlement_after_exit_without_a_deferred_settlement_is_refused(prepared):
    manifest, _ = successor(prepared, completed(prepared))
    save(prepared.root / 'probe' / 'settlement_after_exit.json', {'status': 'settled'})
    repin(manifest)
    with pytest.raises(BudgetStop, match='without a deferred settlement'):
        probe_predecessor.validate_link(manifest)


def test_a_malformed_settlement_after_exit_is_a_budget_stop(prepared, monkeypatch):
    from test_transport_probe import _unfinished
    from decimal import Decimal
    _unfinished(monkeypatch)
    refused(prepared)
    settlement = probe.settle(prepared.registration, prepared.identity)
    cost = str(sum((Decimal(row['cost_usd']) for row in r.read_json(settlement['path'])['requests']), Decimal(0)))
    manifest, _ = successor(prepared, {'successor_continues_from': settlement['path'], 'successor_cost_usd': cost})
    (prepared.root / 'probe' / 'settlement_after_exit.json').write_text('[]\n')
    repin(manifest)
    with pytest.raises(BudgetStop, match='settlement after exit is malformed'):
        probe_predecessor.validate_link(manifest)



def test_relabelling_the_probe_does_not_skip_its_link_check(prepared):
    """#2515: the predecessor's registration is bound to its checkpoint before its kind is read."""
    manifest, path = successor(prepared, completed(prepared))
    _tamper(prepared, manifest, 'billing.json', lambda v: v['requests'][0].update(cost_usd='0'))
    _tamper(prepared, manifest, 'registration.json', lambda v: v.update(kind='something_else'))
    save(path, manifest)
    before = prepared.state.read_bytes()
    with pytest.raises(BudgetStop, match='not the one its checkpoint names'):
        probe_predecessor.validate_predecessor(manifest)
    with pytest.raises(BudgetStop):
        with r.sequence_guard(manifest, r.sha(path)):
            pass
    assert prepared.state.read_bytes() == before


def test_a_bridge_source_relabelled_as_an_audit_is_a_budget_stop(prepared):
    """#2516: a relabelled reconciled probe has no job; refused, never a KeyError."""
    manifest, _ = successor(prepared, refused(prepared))
    _tamper(prepared, manifest, 'registration.json', lambda v: v.update(kind='d4d_native_audit_continuation'))
    with pytest.raises(BudgetStop, match='names no job'):
        r.validate_audit_reconciliation(manifest)
