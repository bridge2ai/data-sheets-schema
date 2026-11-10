#!/usr/bin/env python3
"""Purpose: audit historical D4D stage timestamps for the 2026-11-10 ETA request.

Inputs: primary checkout, sibling d4d-executions reports, coordination log.
Outputs: JSON and TSV evidence in the specified output directory.
Serves: generation ETA analysis (PR pending); 2026-11-10.
Reads ignored/untracked files explicitly, without Git search filtering. File
birth/mtime are observations, not proof of task start or successful completion.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import statistics
import subprocess
from pathlib import Path


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    repo = args.repo.resolve()
    execution = repo.parent / 'd4d-executions'
    tracked = set(subprocess.check_output(
        ['git', '-C', str(repo), 'ls-files', '-z']).decode().split('\0'))
    paths = set()
    for pattern in ('*native*u3*', '*native*u[014567]*', '*u3*deadline*', '*u3*cpu*'):
        paths.update((repo / 'notes/coordination').glob(pattern))
    for pattern in ('native_u*.md', 'budget_reconciliation*.md'):
        paths.update((execution / 'plans/reviews').glob(pattern))
    rows = []
    for path in sorted(paths):
        if not path.is_file():
            continue
        s = path.stat()
        relative = path.relative_to(repo).as_posix() if path.is_relative_to(repo) else None
        rows.append(dict(path=str(path), size=s.st_size,
                         birth_utc=iso(s.st_birthtime) if hasattr(s, 'st_birthtime') else None,
                         modified_utc=iso(s.st_mtime),
                         primary_git_status=('tracked' if relative in tracked else 'untracked_or_ignored')
                         if relative else 'sibling_execution_artifact',
                         sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    status_path = repo / 'notes/coordination/STATUS.md'
    status = status_path.read_text()
    events = []
    for n, line in enumerate(status.splitlines(), 1):
        if re.match(r'\s*- .*2026-11-(0[6-9]|10)', line) and re.search(r'\bU[0-7](?:\b|[a-z])', line, re.I):
            events.append(dict(line=n, text=line))
    # Explicit stage pairs; report modification may include later addenda.
    pairs = []
    for stage, prompt, report in [
        ('F', '2026-11-09-codex-native-u3f.md', 'native_u3f_2026-11-09.md'),
        ('F2', '2026-11-09-codex-native-u3f2.md', 'native_u3f2_2026-11-09.md'),
        ('G', '2026-11-09-codex-native-u3g.md', 'native_u3g_2026-11-09.md'),
        ('H', '2026-11-09-codex-native-u3h.md', 'native_u3h_2026-11-09.md'),
        ('I', '2026-11-09-codex-native-u3i.md', None),
        ('J', '2026-11-09-codex-native-u3j.md', 'native_u3j_2026-11-09.md'),
        ('J2', '2026-11-09-codex-native-u3j2.md', 'native_u3j_2026-11-09.md'),
        ('K', '2026-11-09-codex-native-u3k.md', 'native_u3k_2026-11-09.md'),
    ]:
        a = repo / 'notes/coordination' / prompt
        b = execution / 'plans/reviews' / report if report else None
        if a.exists():
            item = dict(stage=stage, assignment_birth=iso(a.stat().st_birthtime),
                        assignment_modified=iso(a.stat().st_mtime))
            if b and b.exists():
                item.update(report_birth=iso(b.stat().st_birthtime), report_modified=iso(b.stat().st_mtime),
                            assignment_birth_to_latest_report_hours=(b.stat().st_mtime-a.stat().st_birthtime)/3600)
            pairs.append(item)
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    handoffs = []
    for stage, text in [('F', 'U3-F offline repair handoff'),
                        ('F2', 'U3-F2 review repairs'), ('G', 'U3-G complete locally'),
                        ('I', 'U3-I complete;'), ('J', 'U3-J stopped on'),
                        ('J2', 'U3-J2 implementation and offline validation')]:
        matches = [e for e in events if text in e['text']]
        if len(matches) != 1:
            raise ValueError((stage, len(matches)))
        e = matches[0]
        stamp = re.search(r'2026-\d\d-\d\dT\d\d:\d\d(?::\d\d)?Z', e['text']).group()
        pair = next(r for r in pairs if r['stage'] == stage)
        hours = (dt.datetime.fromisoformat(stamp.replace('Z', '+00:00')) -
                 dt.datetime.fromisoformat(pair['assignment_birth'])).total_seconds()/3600
        handoffs.append(dict(stage=stage, assignment_birth=pair['assignment_birth'],
                             handoff_utc=stamp, elapsed_hours=hours, source_status_line=e['line']))
    # Exclude rapid stop/refusal J and small harness repair I from broad-round sample.
    sample = [r['elapsed_hours'] for r in handoffs if r['stage'] in ('F', 'F2', 'G', 'J2')]
    review_delays = []
    for stage, impl, review in [
        ('F', 'native_u3f_2026-11-09.md', 'native_u3f_claude_review_2026-11-09.md'),
        ('F2', 'native_u3f2_2026-11-09.md', 'native_u3f2_claude_recheck_2026-11-09.md'),
        ('G', 'native_u3g_2026-11-09.md', 'native_u3g_claude_review_2026-11-09.md')]:
        a, b = [execution / 'plans/reviews' / name for name in (impl, review)]
        review_delays.append(dict(stage=stage, implementation_modified=iso(a.stat().st_mtime),
                                 review_modified=iso(b.stat().st_mtime),
                                 gap_hours=(b.stat().st_mtime-a.stat().st_mtime)/3600))
    summary = dict(handoffs=handoffs, broad_round_sample_n=len(sample),
                   broad_round_min_hours=min(sample), broad_round_median_hours=statistics.median(sample),
                   broad_round_max_hours=max(sample), review_delays=review_delays,
                   limitation='Convenience sample of handoffs, including unresolved outcomes; not time-to-success or independent trials.')
    (out / 'timestamps.json').write_text(json.dumps(dict(
        observed_utc=iso(dt.datetime.now(dt.timezone.utc).timestamp()),
        scope='Explicit globs in primary notes/coordination and sibling plans/reviews; ignores not applied; not a whole-disk inventory.',
        files=rows, stage_pairs=pairs, status_events=events, summary=summary), indent=2) + '\n')
    (out / 'timestamps.tsv').write_text('birth_utc\tmodified_utc\tgit_status\tpath\n' + ''.join(
        f"{r['birth_utc']}\t{r['modified_utc']}\t{r['primary_git_status']}\t{r['path']}\n" for r in rows))
    print(json.dumps(dict(files=len(rows), events=len(events), summary=summary), indent=2))


if __name__ == '__main__':
    main()
