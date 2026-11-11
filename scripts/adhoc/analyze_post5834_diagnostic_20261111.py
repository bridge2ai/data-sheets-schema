#!/usr/bin/env python3
"""Analyze retained post-#5834 and baseline monitoring diagnostics, 2026-11-11.

Inputs: frozen phase metrics, diagnostic/harness JSON, pytest XML, and source text.
Outputs: new lead tmp summary JSON and requested Markdown handoff. Stdlib only;
no native imports, tests, subprocesses, model calls, or input writes. The older
U3-K summarizer requires control/profile runs and cannot admit this pair of
monitoring runs with different source heads. This helper makes no speed claim.
"""
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT.parent / 'scratch-native-u1u3/u3m'
RUNS = {
    'baseline': ('wp1-3cc113e2606c-cpu-monitoring-e1-observer-baseline-20261111', 7351),
    'post5834': ('wp1-458887766eff-cpu-monitoring-post-5834-20261111', 34474),
}
NOTE = ROOT / 'notes/development_efficiency_20261111/handoffs/post5834-diagnostic-analysis.md'
SUMMARY = ROOT / 'tmp/post5834-analysis-20261111/summary.json'
FILES = {}


def raw(path):
    data = path.read_bytes()
    identity = {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    if str(path) in FILES and FILES[str(path)] != identity:
        raise ValueError('input changed: ' + str(path))
    FILES[str(path)] = identity
    return data


def load(path):
    return json.loads(raw(path))


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def duration(row, kind):
    value = row['inclusive_' + kind]
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('invalid completed duration')
    return value


def phase_summary(measurement, phase):
    start, stop = phase['first_call_row'], phase['last_call_row_exclusive']
    rows = measurement['calls'][start:stop]
    stacks, children, parents, roots = defaultdict(list), defaultdict(list), {}, []
    for index, row in enumerate(rows):
        if row['phase'] != phase['name'] or row['outcome'] == 'open':
            raise ValueError('nonterminal or crossing-phase observation')
        entered = row['entered_wall']
        exited = entered + duration(row, 'wall')
        duration(row, 'thread_cpu')
        stack = stacks[row['thread']]
        while stack and entered >= stack[-1][1]:
            stack.pop()
        if stack:
            parent, parent_end = stack[-1]
            if exited > parent_end + 1e-6:
                raise ValueError('observed intervals cross rather than nest')
            parents[index] = parent
            children[parent].append(index)
        else:
            roots.append(index)
        stack.append((index, exited))
    totals = {}
    for index, row in enumerate(rows):
        bucket = totals.setdefault(row['label'], {'calls': 0, 'inclusive_thread_cpu': 0.0,
            'inclusive_wall': 0.0, 'observed_residual_thread_cpu': 0.0, 'observed_residual_wall': 0.0})
        bucket['calls'] += 1
        for kind in ('thread_cpu', 'wall'):
            inclusive = duration(row, kind)
            residual = inclusive - sum(duration(rows[child], kind) for child in children[index])
            if residual < -1e-5:
                raise ValueError('negative observed residual')
            bucket['inclusive_' + kind] += inclusive
            bucket['observed_residual_' + kind] += max(0.0, residual)
    roster = [[r['label'], r['name'], r['first_line'], r['bytecode_sha256'], r['outcome']] for r in rows]
    roots_cpu = sum(duration(rows[index], 'thread_cpu') for index in roots)
    return {'name': phase['name'], 'outcome': phase['outcome'], 'error': phase['error'],
        'elapsed': phase['elapsed'], 'call_count': len(rows), 'counts': dict(Counter(r['label'] for r in rows)),
        'ordered_roster': roster, 'label_totals': totals,
        'unobserved_root_thread_cpu': phase['elapsed']['thread_cpu'] - roots_cpu,
        'parents_by_absolute_row': {str(start + child): start + parent for child, parent in parents.items()}}


def read_run(name, pid):
    directory = BASE / name
    measurement = load(directory / f'phase-metrics/{pid}-measurement.json')
    diagnostic = load(directory / f'phase-metrics/{pid}-diagnostic.json')
    harness = load(directory / 'wp1-harness.json')
    suite = ET.fromstring(raw(directory / 'pytest.xml')).find('testsuite')
    if measurement['mode'] != 'control' or measurement['open_call_rows'] != 0:
        raise ValueError('requires terminal control-mode observations')
    if not diagnostic['profile_stability']['stable'] or not diagnostic['profile_stability']['restored']:
        raise ValueError('observer guard not stable/restored')
    phases = {phase['name']: phase_summary(measurement, phase) for phase in measurement['phases']}
    captured = utc(diagnostic['capture_timestamp'])
    boundary_labels = {'controller_prewarm', 'accept_saved_capture', 'fresh_admission',
                       'freshness_check', 'freshness_before_dispatch', 'freshness_before_reservation',
                       'attempt_mkdir', 'controller_activate', 'execute_child'}
    boundaries = []
    for index, row in enumerate(measurement['calls']):
        if row['phase'] == 'launch' and row['label'] in boundary_labels:
            boundaries.append({**row, 'row': index,
                'capture_age_at_entry_seconds': (utc(row['entered_utc']) - captured).total_seconds()})
    return {'source_commit': harness['source_commit'], 'interpreter': harness['interpreter'],
        'diagnostic': diagnostic, 'phases': phases, 'boundaries': boundaries,
        'pytest': dict(suite.attrib), 'directory': str(directory)}


def main():
    if NOTE.exists() or SUMMARY.exists():
        raise ValueError('refusing to overwrite existing analysis')
    runs = {key: read_run(*specification) for key, specification in RUNS.items()}
    before, after = runs['baseline'], runs['post5834']
    source = BASE / ('worktree-' + after['source_commit'][:12])
    for name in ('native_subscription_admission.py', 'native_subscription_guard_v2.py',
                 'native_execution_orchestration.py', 'native_shared_execution_orchestration.py'):
        raw(source / 'src/data_sheets_schema' / name)
    comparison = {'same_source': before['source_commit'] == after['source_commit'],
        'same_interpreter': before['interpreter'] == after['interpreter'],
        'phases': {}}
    for phase in ('fixture', 'launch'):
        a, b = before['phases'][phase], after['phases'][phase]
        comparison['phases'][phase] = {
            'same_ordered_roster': a['ordered_roster'] == b['ordered_roster'],
            'count_changes': {label: [a['counts'].get(label, 0), b['counts'].get(label, 0)]
                for label in sorted(set(a['counts']) | set(b['counts']))
                if a['counts'].get(label, 0) != b['counts'].get(label, 0)}}
    launch_rows = after['boundaries']
    acceptance = next(r for r in launch_rows if r['name'] == 'accept_current_selection')
    prewarm = next(r for r in launch_rows if r['label'] == 'controller_prewarm')
    admission = next(r for r in launch_rows if r['label'] == 'fresh_admission')
    fresh = [r for r in launch_rows if r['label'] == 'freshness_check']
    diag = after['diagnostic']
    parent_map = after['phases']['launch']['parents_by_absolute_row']
    exception_chain = []
    cursor = fresh[-1]['row']
    measurement = load(Path(after['directory']) / 'phase-metrics/34474-measurement.json')
    while True:
        row = measurement['calls'][cursor]
        exception_chain.append({'row': cursor, 'label': row['label'], 'name': row['name'],
                               'outcome': row['outcome'], 'file': row['file'], 'line': row['first_line']})
        if str(cursor) not in parent_map:
            break
        cursor = parent_map[str(cursor)]
    result = {'runs': runs, 'comparison': comparison, 'refusal_observed_ancestor_chain': exception_chain,
        'policy': 'Different heads/host conditions and rosters: descriptive timings only, no causal speed claim. '
                  'Observed residual subtracts only immediate monitored children on the same thread; '
                  'it includes uninstrumented descendants and is not full profiler self time. '
                  'Inclusive label totals overlap across labels and possibly within recursive labels; do not sum them.'}
    lines = ['# Post-#5834 native diagnostic analysis', '',
        '**The import-binding blocker is passed, but current capture acceptance still fails before reservation.** '
        'WP2 preflight passed, fresh execution admission and controller prewarm returned, and '
        '`accept_current_selection` was entered but never returned a guard. Optimizing only work after '
        'successful acceptance cannot resolve this earlier failure.', '',
        f"Post-fix source `{after['source_commit']}`, PID34474: saved pytest XML reports "
        f"{after['pytest']['tests']} test, {after['pytest']['failures']} failures, {after['pytest']['errors']} errors, "
        f"{after['pytest']['skipped']} skips, {after['pytest']['time']} seconds. The passing diagnostic records "
        '`genuine_refusal`, not a successful launch. Attempt/evidence are absent; no reservation boundary, '
        'controller activation or child execution was observed. Guard stable/restored, zero open rows; '
        'all timing/freshness qualification flags remain false. Final outer/config cleanup belongs to the native owner '
        'and is not certified by this analysis.', '', '## Refusal boundary', '',
        f"The preserved capture timestamp is `{diag['capture_timestamp']}`; maximum age is "
        f"{diag['capture_age_limit_seconds']} seconds with a {diag['capture_margin_seconds']}-second reservation margin.", '',
        '| Boundary | UTC entry | Capture age at entry (s) | Observed outcome |', '|---|---|---:|---|']
    for title, row in [('Preflight freshness', fresh[0]), ('Fresh execution admission', admission),
                       ('Controller prewarm', prewarm), ('Current capture acceptance', acceptance),
                       ('Final acceptance freshness', fresh[-1])]:
        lines.append(f"| {title} (row{row['row']}) | {row['entered_utc']} | "
                     f"{row['capture_age_at_entry_seconds']:.3f} | {row['outcome']} |")
    lines += ['', f"Observed exception ancestry: `{' → '.join(r['name'] for r in reversed(exception_chain))}`. "
        'The pinned source fills in the unmonitored call from `load_current` through `load_guard` and '
        '`SubscriptionGuard.__init__` to `before_dispatch(check_only=True)` and `_fresh`. The saved capture is '
        f"already {acceptance['capture_age_at_entry_seconds']:.3f} seconds old when acceptance begins; "
        f"acceptance then consumes {acceptance['inclusive_thread_cpu']:.3f} thread-CPU / "
        f"{acceptance['inclusive_wall']:.3f} wall seconds before refusing. It does not reach "
        '`before_reservation` or attempt mkdir. The 210-second latest margin-preserving point also precedes '
        'controller prewarm entry.', '',
        'Source anchors at the post-fix commit: `native_shared_execution_orchestration.py:123` '
        '(mandatory preflight before engine); `native_execution_orchestration.py:363` '
        '(controller prewarm), `:366` (acceptance), `:379` (lease), `:385` (reservation freshness), '
        '`native_subscription_admission.py:158` (load_current), '
        '`native_subscription_guard_v2.py:398` (constructor freshness), `:429` (age refusal).', '',
        '## Descriptive phase comparison', '',
        f"Baseline monitoring source `{before['source_commit']}`, PID7351. Both have the same interpreter identity, "
        'but the source heads, call rosters and host conditions differ. These figures do not establish a causal '
        'WP3 speedup or wall-time improvement. Explicit fixture and launch phases do not overlap; pytest wrapper '
        'and nested function durations must not be added to them.', '',
        '| Phase | Baseline calls | Post-fix calls | Baseline process CPU (s) | Post-fix process CPU (s) | Baseline wall (s) | Post-fix wall (s) |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for phase in ('fixture', 'launch'):
        a, b = before['phases'][phase], after['phases'][phase]
        lines.append(f"| {phase} | {a['call_count']} | {b['call_count']} | {a['elapsed']['process_cpu']:.3f} | "
                     f"{b['elapsed']['process_cpu']:.3f} | {a['elapsed']['wall_monotonic']:.3f} | {b['elapsed']['wall_monotonic']:.3f} |")
    lines += ['', 'Changed call counts (baseline → post-fix; all other label counts unchanged):']
    for phase, changes in comparison['phases'].items():
        text = '; '.join(f"`{label}` {count[0]} → {count[1]}" for label, count in changes['count_changes'].items())
        lines.append(f'- {phase}: {text}.')
    lines += ['', '## Dominant recorded work', '',
        'The next table ranks post-fix **observed residual thread CPU**: each call interval minus its immediate '
        'monitored children, inferred from same-thread nested monotonic intervals. This avoids double counting '
        'within the observed tree, but still includes uninstrumented descendants; it is not true function self CPU. '
        'Inclusive totals are shown separately and overlap. No full cProfile data exists in these control-mode records.', '',
        '| Phase / label | Calls | Baseline residual thread CPU (s) | Post-fix residual thread CPU (s) | Post-fix inclusive thread CPU (s) |',
        '|---|---:|---:|---:|---:|']
    for phase in ('fixture', 'launch'):
        a, b = before['phases'][phase]['label_totals'], after['phases'][phase]['label_totals']
        for label, total in sorted(b.items(), key=lambda item: -item[1]['observed_residual_thread_cpu'])[:5]:
            lines.append(f"| {phase} / {label} | {total['calls']} | "
                         f"{a.get(label, {}).get('observed_residual_thread_cpu', 0):.3f} | "
                         f"{total['observed_residual_thread_cpu']:.3f} | {total['inclusive_thread_cpu']:.3f} |")
    lines += ['', f"Controller prewarm alone returned after {prewarm['coarse_elapsed']['process_cpu']:.3f} process-CPU / "
        f"{prewarm['coarse_elapsed']['wall_monotonic']:.3f} wall seconds. Registration/schema verification calls are nested "
        'inside several enclosing boundaries; their inclusive totals are not independent phase costs.', '',
        'The next development target must address measured work before successful current-capture acceptance while '
        'preserving the original capture timestamp and fresh checks. A post-acceptance redesign may address a later '
        'boundary, but this run has not reached that boundary and cannot validate that benefit.', '',
        '## Provenance and limits', '',
        f"Produced by `scripts/adhoc/{Path(__file__).name}` using only saved inputs. Detailed call counts, ordered "
        f"rosters, observed-tree parent indices and hashes are retained in `{SUMMARY.relative_to(ROOT)}`. "
        'The JSON summary retains original local source paths. No input evidence is rewritten. This analysis '
        'does not certify outer cleanup, quiet-host performance, accepted reservation or model generation.', '',
        '| Input | SHA256 |', '|---|---|']
    for path, identity in FILES.items():
        lines.append(f"| `{path}` | `{identity['sha256']}` |")
    for path in list(FILES):
        raw(Path(path))
    result['input_files'] = list(FILES.values())
    result['helper_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    NOTE.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    with NOTE.open('x') as stream:
        stream.write('\n'.join(lines) + '\n')
    print(json.dumps({'note': str(NOTE), 'summary': str(SUMMARY),
        'acceptance_age_seconds': acceptance['capture_age_at_entry_seconds'],
        'source_heads_differ': not comparison['same_source']}))


if __name__ == '__main__':
    main()
