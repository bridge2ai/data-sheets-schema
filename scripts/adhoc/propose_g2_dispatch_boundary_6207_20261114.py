#!/usr/bin/env python3
"""Produce the review-only dispatch-boundary proposal for issue 6207, 2026-11-14.

Inputs: committed current guard, engine, pinned transport and manifests; saved
issue in sibling scratch-g2-20261114/baseline. Outputs: unified diff, original
and proposed source snapshots, pin proposal and test plan in sibling scratch.
Never applies the diff, rotates pins, imports project modules or runs tests.
Run only after the actual G2 fixes have been committed and source is stable.
"""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
OUTPUT = SCRATCH / 'proposal-6207'
GUARD = 'src/data_sheets_schema/native_subscription_guard_v2.py'
ENGINE = 'src/data_sheets_schema/native_execution_orchestration.py'
TRANSPORT = 'notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py'
MANIFESTS = tuple('src/data_sheets_schema/native_controller_sources_v' + str(v) + '.json'
                  for v in (1, 2))


GUARD_MEMORY = '''    def _dispatch_memory_authority(self):
        """Immutable values only: never reconstruct authority or read a path."""
        if (any(type(value) is not bytes for value in
                (self._raw, self._registration, self._runtime_raw, self._word_raw, self._owner_raw))
                or type(self._expected) is not str
                or type(self._windows) is not dict or type(self._record_only) is not dict):
            raise ValueError("subscription captured authority changed before process dispatch")
        return (self._raw, self._expected, self._registration, self._runtime_raw,
                self._word_raw, self._owner_raw, self._dispatched_at, self._dispatch_time_bound,
                canonical(self._windows), canonical(self._record_only))

'''

GUARD_BEFORE_DISPATCH = '''    def before_dispatch(self, *, check_only=False):
        if type(check_only) is not bool:
            raise ValueError("subscription dispatch selection must be boolean")
        bound, consumed_at, stamp = self._fresh()
        if not check_only:
            self._dispatched = True
            self._dispatched_at = stamp
            # Capture validated temporal scalars while the admission alarm is
            # armed. The final hook must not call _static or resolve paths.
            self._dispatch_time_bound = (consumed_at, bound["captured"], bound["max_age"],
                tuple(row["resets_at"] for row in bound["readings"].values()))
            self._dispatch_authority = self._dispatch_memory_authority()
            self._dispatch_path = self._path
            self._dispatch_clock = self._clock

    def before_process_dispatch(self, *, refusal=None):
        """One final memory/clock check after admission cleanup, before Popen.

        A caller's authority refusal can only stop this attempt. It cannot
        skip any guard check or permit retry after a refused final boundary.
        """
        if self._dispatch_checked is not False:
            if self._stop is None:
                self._stop = "subscription process dispatch check already attempted"
            raise ValueError(self._stop)
        self._dispatch_checked = True
        try:
            if self._stop is not None:
                raise ValueError(self._stop)
            if refusal is not None:
                if type(refusal) is not str or not refusal:
                    raise ValueError("subscription final dispatch refusal is malformed")
                raise ValueError(refusal)
            if self._dispatched is not True or self._dispatch_time_bound is None:
                raise ValueError("subscription process dispatch requires consumed admission")
            if self._observation_started or type(self._count) is not int or self._count != 0:
                raise ValueError("subscription process dispatch follows an observation")
            if (self._path is not self._dispatch_path or self._clock is not self._dispatch_clock
                    or self._dispatch_memory_authority() != self._dispatch_authority):
                raise ValueError("subscription captured authority changed before process dispatch")
            consumed_at, captured_at, max_age, resets = self._dispatch_time_bound
            now = self._clock()
            if type(now) not in (int, float) or not math.isfinite(now):
                raise ValueError("subscription guard clock is invalid")
            try:
                stamp = datetime.fromtimestamp(now, timezone.utc).isoformat().replace("+00:00", "Z")
                now = _timestamp(stamp, "dispatch time")
            except (ValueError, OverflowError, OSError) as exc:
                raise ValueError("subscription guard clock is invalid") from exc
            if now < consumed_at:
                raise ValueError("subscription guard clock moved backward before process dispatch")
            if not 0 <= now - captured_at <= max_age:
                raise ValueError("subscription observation is stale or future-dated")
            if any(reset <= now for reset in resets):
                raise ValueError("subscription window reset since observation")
        except (ValueError, TypeError, OverflowError, OSError, RecursionError) as exc:
            if self._stop is None:
                self._stop = str(exc)
            raise ValueError(self._stop) from exc
        # A refused final check retains the earlier valid timestamp and the
        # immutable consumed marker. Only successful revalidation replaces it.
        self._dispatched_at = stamp

'''


ENGINE_MEMORY = '''def _dispatch_memory_authority(value, authorization, selected, observation, policy,
                               registration_raw, started_raw):
    """Snapshot captured values without opening, resolving or verifying paths."""
    raw = authorization['raw']
    if (type(raw) is not dict
            or any(type(name) is not str or type(body) is not bytes for name, body in raw.items())):
        raise ValueError('native captured authority bytes changed before process dispatch')
    # Canonical bytes detach every nested mutable mapping/list; object identity
    # alone would miss an in-place change between admission and process spawn.
    return (c.canonical(value),
        c.canonical({name: item for name, item in authorization.items() if name != 'raw'}),
        tuple(sorted(raw.items())), c.canonical(selected), c.canonical(observation),
        c.canonical(policy), registration_raw, started_raw)


'''


ENGINE_FINAL = '''                def dispatch_check():
                    refusal = None
                    try:
                        if dispatch_authority is None or _dispatch_memory_authority(
                                value, authorization, selected, observation, adapter.policy,
                                registration_raw, started_raw) != dispatch_authority:
                            raise ValueError('native captured authority changed before process dispatch')
                        if proxy.closed or proxy.failed.is_set():
                            raise ValueError('native admission is closed before process dispatch')
                    except ValueError as exc:
                        refusal = str(exc)
                    except (TypeError, KeyError, RecursionError):
                        refusal = 'native captured authority is malformed before process dispatch'
                    try:
                        # The guard latches this attempt even when the captured
                        # caller authority has changed. No restored value retries.
                        launch_guard.before_process_dispatch(refusal=refusal)
                    except ValueError as exc:
                        reason = 'subscription guard: ' + str(exc)
                        stopped(reason)
                        raise controls['run_native_canary'].BudgetStop(reason) from exc
'''


TEST_PLAN = {
    'issue': 6207,
    'status': 'planned, not executed; proposal is not applied',
    'environment': {
        'interpreter': '/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python',
        'cwd': str(ROOT), 'PYTHONPATH': str(ROOT / 'src'), 'PYTHONDONTWRITEBYTECODE': '1',
        'outputs': 'fresh directories below sibling scratch-g2-20261114; never inside a worktree',
    },
    'required_regressions': [
        {'scope': 'guard component', 'file': 'tests/test_native_subscription_guard_v2.py',
         'cases': [
             'Consume once under the ordinary file-checking path; advance the clock and verify final success updates dispatched_at.',
             'Advance beyond captured_at plus max_age or to a reset epoch after consumption; final check refuses with its concrete reason, preserves the earlier valid stamp and consumed state, and cannot retry after restoring the clock.',
             'Clock is bool, NaN, infinity, out-of-range epoch, or backward relative to consumption: fail closed without replacing the prior valid stamp.',
             'Refuse final check before consumption, duplicate final check after success, existing sticky stop, and both rate-limit and non-rate observations before final check.',
             'Change each captured guard byte string, expected hash, path reference, clock reference or nested window mapping after consumption; refuse without re-reading or resolving any path.',
             'After consumption replace _fresh, _static, read_regular, Path.resolve and filesystem entry points with failures; final success and time-refusal paths must use none of them.',
             'A caller-supplied authority refusal consumes the final-check opportunity and remains the sticky stop after inputs are restored.',
         ]},
        {'scope': 'pinned transport ordering', 'file': 'tests/test_native_admission_timer.py',
         'cases': [
             'Use a fake admission.armed context that advances time on teardown. verify_dispatch runs after teardown and before dispatch elapsed_ns, admission.check and Popen.',
             'Final hook BudgetStop prevents Popen, retains its reason and earlier admission artifacts, and cannot relabel the failure as admitted.',
             'A late admission timeout still prevents Popen after a successful final hook. Child deadline origin remains after hook work.',
             'Historical callers omitting the optional hook retain their existing path; shared-v2 callers always supply it.',
         ]},
        {'scope': 'shared-v2 integration', 'file': 'tests/test_native_shared_execution_failure.py',
         'cases': [
             'Advance across freshness expiry/reset during power probing; consumption refuses before activation writes any stage evidence and no Popen occurs.',
             'Advance across freshness expiry/reset during activation after successful consumption; final hook refuses, retains spent stage evidence and the consumed marker, and no Popen occurs.',
             'Advance across freshness expiry/reset while writing the consumed marker and during alarm teardown; final hook refuses and no Popen occurs.',
             'Mutate nested value/runtime, authorization records/raw/inputs, selected composition, runtime observation or adapter policy during activation, marker writing or alarm teardown without replacing the outer mapping; final hook refuses via immutable value comparison.',
             'A refused final check preserves subscription-dispatched.json bytes and the earlier valid dispatched_at, and failed final readback retains the concrete first_stop.',
             'Successful final check is reflected in the saved subscription snapshot; no marker rewrite or post-alarm disk read/write occurs in the hook.',
         ]},
    ],
    'complete_files_after_approval': [
        'tests/test_native_subscription_guard_v2.py', 'tests/test_native_admission_timer.py',
        'tests/test_native_attempt_deadline.py', 'tests/test_native_admission_failure.py',
        'tests/test_native_shared_execution_failure.py', 'tests/test_native_execution_engine.py',
        'tests/test_native_failure_publication.py', 'tests/test_native_host_power.py',
    ],
    'remaining_limit': 'The hook and Popen are separate instructions. Scheduling or suspension can occur after the final clock check and before the child starts. This proposal narrows and observes the final parent-side boundary; it does not make it atomic. Stronger child-start authority requires a separate design and evidence contract.',
}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('proposal anchor is not unique: ' + repr(old))
    return source.replace(old, new, 1)


def replace_function(source, name, replacement, *, class_name=None):
    tree = ast.parse(source)
    owner = tree
    if class_name is not None:
        owner, = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name]
    node, = [node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == name]
    lines = source.splitlines(keepends=True)
    return ''.join(lines[:node.lineno - 1]) + replacement.rstrip() + '\n' + ''.join(lines[node.end_lineno:])


def guard_candidate(source):
    source = once(source,
        '"_clock", "_path", "_dispatched", "_dispatched_at", "_stop", "_count", "_windows", "_record_only")',
        '"_clock", "_path", "_dispatched", "_dispatched_at", "_stop", "_count", "_windows", "_record_only",\n'
        '                 "_dispatch_time_bound", "_dispatch_authority", "_dispatch_path", "_dispatch_clock",\n'
        '                 "_dispatch_checked", "_observation_started")')
    source = once(source, '        self._dispatched_at = None\n',
        '        self._dispatched_at = None\n'
        '        self._dispatch_time_bound = self._dispatch_authority = None\n'
        '        self._dispatch_path = self._dispatch_clock = None\n'
        '        self._dispatch_checked = self._observation_started = False\n')
    source = replace_function(source, 'before_dispatch', GUARD_MEMORY + GUARD_BEFORE_DISPATCH,
                              class_name='SubscriptionGuard')
    return once(source, '    def observe(self, event):\n',
        '    def observe(self, event):\n'
        '        self._observation_started = True\n')


def transport_candidate(source):
    source = once(source,
        '                  command_policy=None, phase_spec=None, command_classifier=None, event_observer=None):\n',
        '                  command_policy=None, phase_spec=None, command_classifier=None, event_observer=None,\n'
        '                  verify_dispatch=None):\n')
    return once(source,
        '            # Dispatch origin includes process creation but excludes admission.\n',
        '            if verify_dispatch is not None:\n'
        '                verify_dispatch()\n'
        '            # Dispatch origin includes process creation but excludes admission.\n')


def engine_candidate(source):
    # This generator intentionally requires the committed 6218 ordering.
    launch = '                def launch_check():\n'
    source = once(source, launch,
        '                dispatch_authority = None\n' + launch +
        '                    nonlocal dispatch_authority\n')
    source = once(source, 'def _admit_subscription_guard(guard, attempt, file, write):\n',
                  ENGINE_MEMORY + 'def _admit_subscription_guard(guard, attempt, file, write):\n')
    identity_checked = "                        raise ValueError('native admission is closed or consumed identity changed')\n"
    source = once(source, identity_checked, identity_checked +
        '                    dispatch_authority = _dispatch_memory_authority(\n'
        '                        value, authorization, selected, observation, adapter.policy,\n'
        '                        registration_raw, started_raw)\n')
    source = once(source,
        '                    # A final check at actual Popen remains the separate 6207 gap.\n',
        '                    # Final temporal revalidation follows activation and alarm teardown.\n')
    anchor = '                    contract.activate_before_dispatch(adapter, started_raw)\n'
    source = once(source, anchor, anchor + ENGINE_FINAL)
    source = once(source,
        '                    deadline_seconds=value[\'runtime\'][\'deadline_seconds\'], verify_launch=launch_check,\n',
        '                    deadline_seconds=value[\'runtime\'][\'deadline_seconds\'], verify_launch=launch_check,\n'
        '                    verify_dispatch=dispatch_check,\n')
    node, = [node for node in ast.walk(ast.parse(source))
             if isinstance(node, ast.FunctionDef) and node.name == 'launch_check']
    segment = ast.get_source_segment(source, node)
    assert segment.index('host_power.dispatch_power()') < segment.index('_admit_subscription_guard')
    assert segment.index('_admit_subscription_guard') < segment.index('contract.activate_before_dispatch')
    assert segment.index('_dispatch_memory_authority') < segment.index('_require_launch_profile')
    return source


def verify_proposal_shape(candidates):
    trees = {name: ast.parse(raw, filename=name) for name, raw in candidates.items()}
    guard_class, = [node for node in trees[GUARD].body
                   if isinstance(node, ast.ClassDef) and node.name == 'SubscriptionGuard']
    final, = [node for node in guard_class.body
              if isinstance(node, ast.FunctionDef) and node.name == 'before_process_dispatch']
    calls = [node.func for node in ast.walk(final) if isinstance(node, ast.Call)]
    forbidden = {'_fresh', '_static', 'read_regular', 'open', 'resolve', '_admission', 'snapshot'}
    assert not any((isinstance(call, ast.Name) and call.id in forbidden)
                   or (isinstance(call, ast.Attribute) and call.attr in forbidden) for call in calls)
    transport = candidates[TRANSPORT].decode()
    hook = transport.index('                verify_dispatch()\n')
    assert transport.index('                verify_launch()') < hook < transport.index('            dispatch_ns = elapsed_ns()')
    assert candidates[ENGINE].count(b'verify_dispatch=dispatch_check') == 1


def main():
    issue = SCRATCH / 'baseline/issue-6207.json'
    assert json.loads(issue.read_text())['issue']['number'] == 6207
    assert not OUTPUT.exists(), 'retain earlier proposal; use a separately reviewed new destination'
    paths = (GUARD, ENGINE, TRANSPORT, *MANIFESTS)
    assert not git('status', '--porcelain', '--', *paths), 'commit actual source fixes before generating'
    head = git('rev-parse', 'HEAD').decode().strip()
    originals = {name: (ROOT / name).read_bytes() for name in paths}
    candidates = {
        GUARD: guard_candidate(originals[GUARD].decode()).encode(),
        ENGINE: engine_candidate(originals[ENGINE].decode()).encode(),
        TRANSPORT: transport_candidate(originals[TRANSPORT].decode()).encode(),
    }
    verify_proposal_shape(candidates)
    pin_proposals = []
    for name in MANIFESTS:
        manifest = json.loads(originals[name])
        entry = manifest['modules']['run_native_canary']
        assert entry['path'] == TRANSPORT and entry['sha256'] == sha(originals[TRANSPORT])
        pin_proposals.append({'manifest': pin(ROOT / name), 'module': 'run_native_canary',
            'source': TRANSPORT, 'old_sha256': entry['sha256'],
            'proposed_sha256': sha(candidates[TRANSPORT]), 'applied': False,
            'source_commit': 'Requires a separate approved controller source commit; no value invented.'})
    patch = ''.join(''.join(difflib.unified_diff(
        originals[name].decode().splitlines(keepends=True), proposed.decode().splitlines(keepends=True),
        fromfile='a/' + name, tofile='b/' + name)) for name, proposed in candidates.items()).encode()
    assert patch and all((ROOT / name).read_bytes() == raw for name, raw in originals.items())
    assert git('rev-parse', 'HEAD').decode().strip() == head
    OUTPUT.mkdir()
    for category, contents in (('original', originals), ('candidate', candidates)):
        for name, raw in contents.items():
            path = OUTPUT / category / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            assert path.read_bytes() == raw
    patch_path = OUTPUT / 'dispatch-boundary.patch'
    patch_path.write_bytes(patch)
    command = ['git', 'apply', '--check', str(patch_path)]
    checked = subprocess.run(command, cwd=ROOT, capture_output=True, check=False)
    check_path = OUTPUT / 'apply-check.json'
    check_path.write_text(json.dumps({'command': command, 'cwd': str(ROOT),
        'returncode': checked.returncode, 'stdout': checked.stdout.decode(),
        'stderr': checked.stderr.decode()}, indent=2) + '\n')
    assert checked.returncode == 0, 'review-only diff does not apply to this source snapshot'
    assert all((ROOT / name).read_bytes() == raw for name, raw in originals.items())
    assert git('rev-parse', 'HEAD').decode().strip() == head
    plan_path = OUTPUT / 'test-plan.json'
    plan_path.write_text(json.dumps(TEST_PLAN, indent=2) + '\n')
    metadata = {
        'issue': 6207, 'answer': 'Not fixed: implementation-ready review-only proposal; approval and validation required.',
        'head': head, 'branch': git('branch', '--show-current').decode().strip(),
        'applied': False, 'pin_rotation_applied': False, 'tests_run': False,
        'issue_evidence': pin(issue), 'generator': pin(Path(__file__).resolve()),
        'patch': pin(patch_path), 'apply_check': pin(check_path), 'test_plan': pin(plan_path),
        'syntax': 'All three candidate Python sources parsed with ast.parse; no candidate code imported or executed.',
        'sources': [{'path': name, 'current': pin(ROOT / name),
            'original_snapshot': pin(OUTPUT / 'original' / name),
            'candidate_snapshot': pin(OUTPUT / 'candidate' / name)} for name in candidates],
        'pin_proposals': pin_proposals,
        'unchanged': 'Current production, tests, controller manifests and prompt pins are not written by this generator.',
        'boundary': 'Admission reads, reconstruction, activation, power probing and immutable marker writes stay under the existing alarm. Final verification uses detached memory values and the actual dispatch clock after alarm teardown, then the transport checks its own deadline before Popen.',
        'refusal': 'Final attempts are one-shot. A failure retains the earlier valid dispatch timestamp, immutable consumed marker and first stop; restoring inputs or clock does not permit retry.',
        'activation_order': 'Profile and power checks precede guard consumption; consumption precedes activation stage writes. This preserves the G2-REVIEW-6218-F1 correction. Expiry during activation is refused by the new final hook with consumed stage evidence retained.',
        'remaining_limit': TEST_PLAN['remaining_limit'],
    }
    metadata_path = OUTPUT / 'proposal.json'
    metadata_path.write_text(json.dumps(metadata, indent=2) + '\n')
    for path in (patch_path, check_path, plan_path, metadata_path):
        assert path.is_file() and path.stat().st_size > 0
    print(json.dumps({'proposal': pin(metadata_path), 'patch': pin(patch_path), 'applied': False}))


if __name__ == '__main__':
    main()
