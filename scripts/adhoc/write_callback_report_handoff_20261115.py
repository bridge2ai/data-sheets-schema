"""Issue 6214, 2026-11-15: prepend reviewed continuation from saved test evidence."""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path.cwd()
scratch = root.parent / 'scratch-callback-teardown-20261115'
handoff = root.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-callback-teardown-20261115.md'
summary = json.loads((scratch / 'report-summary.json').read_text())
audit = json.loads((scratch / 'report-audit.json').read_text())
run = json.loads((scratch / 'report-required.json').read_text())
focused = json.loads((scratch / 'report-focused.json').read_text())
changed = subprocess.check_output(['git', 'status', '--short'], text=True)
(scratch / 'report-final-status.txt').write_text(changed)
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()

def link(path):
    path = path.resolve()
    assert path.exists(), path
    return '[' + path.name + '](' + str(path) + ')'

text = '''## Continuation: callback report lock bound

Implemented the report-path fix locally. `CallbackAdapter.report` now acquires the worker lock with `CALLBACK_TEARDOWN_SECONDS`, preserves an active original exception, and refuses through the existing failure path on timeout. It poisons the shared gate and roots the entire callback scope without invoking its exit, closing its stack, or revoking its loaders. Both complete and partial reports refuse reuse after timeout. Acquired-lock behavior is unchanged.

'''
text += 'Focused tests: ' + link(scratch / 'report-focused.log') + ' records ten passing tests, including five new report regressions. Required continuation suite: ' + json.dumps(summary['counts'], sort_keys=True) + '. Outer-bound result: ' + json.dumps({k: run[k] for k in ('code', 'timed_out', 'seconds')}) + '.\n\n'
text += '''The existing two-second teardown grace period applies to this final report-lock acquisition as well. It matches the classifier window; it does not change the observer or runtime acceptance windows. Timeout sets the adapter failure only when there is no earlier failure. The execution handler retains `first_error` and the sticky first stop and records `finalization failed`. No closed evidence fields were added.

Git add and commit both failed because the sandbox refused the worktree index lock. This is a filesystem sandbox refusal, not an automatic approval-review rejection. Per assignment, no escalation was attempted. The source remains uncommitted and the lead must commit it before reviewed-source integration checks can pass. Evidence: ''' + link(scratch / 'report-commit-attempt.txt') + '. Current branch head: `' + head + '`.\n\n'
text += 'Failure details are retained in ' + link(scratch / 'report-summary.json') + ' and ' + link(scratch / 'report-required.log') + '.\n\n'
for row in summary['failures']:
    detail = row['detail']
    text += '- `' + row['nodeid'] + '` (' + row['when'] + '): ' + ('reviewed-commit source refusal.' if 'reviewed commit' in detail else 'see saved traceback; not classified as a reviewed-commit refusal.') + '\n'
text += '''
Wait audit, including the adapter file outside the requested glob:

- `native_shared_callback_orchestration.py:204`: raw unbounded acquire in callback entry. No internal timeout. Its callers below run under controller deadlines, which bound the controller waiting but cannot stop the worker. Kept unchanged because this is callback entry, not main-thread finalization.
- `native_shared_callback_orchestration.py:308`: classifier lock context. The controller classifier window bounds acceptance, not the worker lifetime; no independent lock bound.
- `native_shared_callback_orchestration.py:314`: read-only classifier lock context. Called inside observation with the reentrant lock already held; the outer observer window bounds acceptance, not worker lifetime.
- `native_shared_controller_orchestration.py:423`: observer lock context. The controller observer window bounds acceptance, not worker lifetime; no independent lock bound.
- `native_shared_callback_orchestration.py:197`: explicit caller-supplied acquire timeout; the teardown call sites at lines 234 and 244 use the named bound. Scope contexts at lines 329 and 442 delegate to those bounded exits.
- `native_shared_controller_orchestration.py:588`: report acquire now uses that same named bound. This was the only additional unbounded worker-lock acquisition on the requested shutdown path.
- `native_execution_orchestration.py:412`: reservation journal context delegates to `native_capture_words.py:361`, whose flock is nonblocking and refuses contention. It is an admission path, before launch, not finalization.
- The AST inventory found no thread joins, event waits, or blocking queue gets in the requested callback files, execution orchestration, or stage package. Every get there is a mapping lookup. The adapter string joins are formatting, not thread waits. Each candidate, including mapping gets, has a file and line in the saved inventory.

The historical controller additionally uses nonblocking work-reply polling and a bounded worker join. Its worker is non-daemon. Therefore a permanently stuck worker can still prevent interpreter exit; this patch does not claim globally bounded process shutdown. Changing worker termination is outside this assignment's design.

'''
text += 'Audit evidence: ' + link(scratch / 'report-wait-sites.json') + ', ' + link(scratch / 'report-audit.json') + '. The audit script parses every file selected by filesystem glob/rglob, independently of ignore rules. Pin grep recursively included ignored and hidden files and excluded only Git metadata. No old-digest match was found. Path hits include the CI source list and an archival draft packet map with an already-stale source digest; neither is a static runtime pin requiring rotation. No pin edits are proposed. Old source digest: `' + audit['old'] + '`; proposed source digest: `' + audit['new'] + '`. Searches: ' + link(scratch / 'report-pin-path.txt') + ' and ' + link(scratch / 'report-pin-hash.txt') + '.\n\n'
text += '''Read-only review: examined the final production change and new regression file separately after implementation. No further defect requiring an in-scope fix was found. Remaining findings for the lead are the non-daemon-worker process-exit limit and the previously observed ignored generator-finalizer errors during interpreter shutdown. The focused log retains those diagnostics; in-process assertions establish scope survival after dropping adapter references and after worker release, but do not establish clean interpreter finalization. No real native binary or provider was invoked. The new tests use a controlled generator loader, not a full native launch. The earlier Read-test recommendation still applies unchanged. Scanner suites and full collection were not repeated for this continuation; their prior results remain below.

Reproduction uses the existing bounded runner with the assigned interpreter and worktree PYTHONPATH. The single timeout canary used the same runner and produced a passing test record before the focused and wider cohorts. The focused and required run JSON files contain the exact commands and bounds. All pytest temporary directories and evidence are in the assigned scratch directory.

'''
text += 'Uncommitted files for lead integration:\n\n'
for line in changed.splitlines():
    path = root / line[3:]
    text += '- ' + link(path) + '\n'
text += '\nThe handoff-writing and audit helpers are retained on this branch under `scripts/adhoc/`. No push, pull request, GitHub write, protected-file edit, or pin rotation was performed.\n\n---\n\n'
assert chr(64) not in text
old = handoff.read_text()
if old.startswith('## Continuation: callback report lock bound'):
    old = old.split('\n---\n\n', 1)[1]
handoff.write_text(text + old)
assert chr(64) not in handoff.read_text()
print(str(handoff))
print(hashlib.sha256(handoff.read_bytes()).hexdigest())
