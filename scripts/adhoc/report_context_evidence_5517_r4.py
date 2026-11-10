"""#5517 Round 4 handoff, 2026-11-08.
Inputs: committed HEAD, scratch audit and test XML/logs. Outputs: append-only
Round 4 review report and exactly one entry under shared STATUS ### codex.
"""
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-codex-5517'
REPORT = ROOT.parent / 'plans/reviews/codex_5517_2026-11-08.md'
STATUS = ROOT.parent.parent / 'data-sheets-schema/notes/coordination/STATUS.md'
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
audit = json.loads((SCRATCH / 'r4-audit.json').read_text())
results = []
for mode in ('canary', 'literal', 'focused', 'evaluation'):
    label = mode + '-r4'
    assert (SCRATCH / (label + '.log')).stat().st_size
    suite = ET.parse(SCRATCH / (label + '.xml')).getroot().find('testsuite')
    assert all(suite.get(key) == '0' for key in ('failures', 'errors', 'skipped'))
    results.append(f'{label}: {suite.get("tests")} passed')
summary = '; '.join(results)
report = REPORT.read_text()
status = STATUS.read_text()
marker = '**#5517 Round 4 / D104 complete; stopped.**'
assert '\n## Round 4' not in report and marker not in status
assert status.count('### codex\n') == 1
section = f'''
## Round 4 — D104

Local commit `{head}` on `codex/5517-context-evidence-20261108`, parent `4527a94705f90f5c413babb344e55b875f65dbbd`; no push.

AI-READI `processing_software` remains `true` and is now quoted, with no `needs_owner` metadata: "{audit['quote']}". Verified verbatim at `data/preprocessed/concatenated/AI_READI_preprocessed.txt:4367` and within c018, with both bundle and chunk SHA256 checked against the manifest. Strict inventory: **41 quoted, 1 absence-supported, 0 needs_owner**. All applicability values and D52 strings are preserved.

D102 live AI-READI normalized pin: `{audit['old_pin']}` → `{audit['new_pin']}`. Only that hash in the live decision table changed; historical registrations and protected files are untouched.

Validation: **{summary}**, zero failures/errors/skips. Canary log and XML were inspected before the three suites; it proved the same launcher, environment, two-worker execution and artifact persistence. Each run used absolute worktree `PYTHONPATH`, scratch-only TMPDIR/basetemp, disabled bytecode/cache and the existing 3600-second process-group supervisor. Quiet lock checked before and during execution; no interruptions. Evidence: `{SCRATCH}/r4-audit.json` and `*-r4.log` / `*-r4.xml`. No native agent executable, network/provider call, fetch, push or gh; no new top-level execution directory.

Separate read-only review checked the full bounded diff and helper provenance: exact owner quotation, unchanged true value, removed unresolved state, stricter inventory, single live-pin rotation and no protected/historical changes. No new actionable finding. Helpers: `scripts/adhoc/context_evidence_5517_r4.py` and `scripts/adhoc/report_context_evidence_5517_r4.py`. The initial STATUS read was overbroad and truncated; targeted reads recovered the owner decisions. An unnecessary instruction-file search across the executions directory completed without edits; subsequent reads were bounded. No PR or integration attempted under the explicit offline/no-push instruction. Exactly one STATUS entry follows; stopped.
'''
stamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
entry = f'- {stamp} — {marker} Local commit `{head}`, no push. AI-READI processing_software stays true with the exact c018/4367 REDCap quotation; inventory 41 quoted / 1 absence-supported / 0 needs_owner. AI-READI live pin rotated under D102; historical/protected files unchanged. {summary}; zero failures/errors/skips. Report: `d4d-executions/plans/reviews/codex_5517_2026-11-08.md`, Round 4. Evidence solely in `scratch-codex-5517`; offline, quiet-lock/3600-second/two-worker rules observed, no native executable. Stopped.\n'
REPORT.write_text(report + section)
assert REPORT.read_text() == report + section
updated = status.replace('### codex\n', '### codex\n\n' + entry, 1)
STATUS.write_text(updated)
assert STATUS.read_text() == updated and updated.count(marker) == 1
print(head + '\n' + summary + '\nReport and exactly one STATUS entry verified.')
