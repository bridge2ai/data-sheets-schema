"""Issue 6214, 2026-11-15: write verified handoff from saved checks and audit."""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path.cwd()
scratch = root.parent / 'scratch-callback-teardown-20261115'
handoff = root.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-callback-teardown-20261115.md'
summary = json.loads((scratch / 'summary.json').read_text())
audit = json.loads((scratch / 'audit.json').read_text())
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
status = subprocess.check_output(['git', 'status', '--porcelain'], text=True)
(scratch / 'final-git-status.txt').write_text(status)
files = [line[3:] for line in status.splitlines()]
for filename in files:
    assert (root / filename).is_file(), filename
source = root / audit['source']
assert hashlib.sha256(source.read_bytes()).hexdigest() == audit['new']
assert not audit['hash_references']
for name in ('final-required', 'final-collection', 'final-canary'):
    assert name in summary['runs'], name
required = summary['runs']['final-required']
collection = summary['runs']['final-collection']

def link(path, title=None):
    path = Path(path)
    assert path.exists(), path
    return '[' + (title or path.name) + '](' + str(path) + ')'

counts = summary['totals']
validation = (str(counts.get('call:passed', 0)) + ' passed calls, '
    + str(counts.get('call:failed', 0)) + ' failed calls, '
    + str(counts.get('setup:failed', 0)) + ' setup errors; '
    + str(sum(summary['remaining_by_file'].values())) + ' cases without a completed report.')
lines = [
'Implemented locally, uncommitted because the sandbox refused the index lock: the lead’s bounded-wait, fail-closed design for callback scope teardown. The named bound is `CALLBACK_TEARDOWN_SECONDS = 2.0`. A timed-out scope is poisoned, its stack is retained for process lifetime, and subsequent callback entry and semantic reuse refuse. An already-propagating exception remains primary, with the timeout refusal chained beneath it.',
'',
'Focused validation: five tests passed; both real source-loader witnesses passed their in-process lifetime assertions. Combined required-suite recorded outcomes: ' + validation,
'Collection: ' + '; '.join(collection['summary_lines']) + '. The three FAIRSCAPE collection errors are the expected missing submodule imports.',
'',
'Pin proposal: no static pin rotation. Ignore-independent recursive grep, including hidden and ignored files and excluding Git metadata, found no reference to the old source digest. The source is still subject to runtime reviewed-commit verification; the lead must commit the change before those integration fixtures can pass. No pin, scanner, controller manifest, runtime profile, synthetic peer or protected file was edited.',
'',
'Read-test recommendation: separate focused denial and saved-denial replay coverage from the full successful-completion scenario, and put the latter in a dedicated native completion lane. No change was made to the denial test.',
'',
'The two-second teardown grace period matches the existing classifier window. The observer window remains 120 seconds and the runtime callback window remains 125 seconds. Acquired-lock exit and exception suppression retain their previous behavior. Timeout does not close the stack, revoke carriers, remove admission ledgers or unwind the retained loaders. Stacks are rooted in a private list on `sys`, so unloading an orchestration module cannot collect them. No worker-release callback closes a poisoned stack.',
'',
'The existing finalization exception handler in ' + link(root / 'src/data_sheets_schema/native_execution_orchestration.py') + ' records `finalization failed` through `stopped` and the existing first-stop failure path. No closed evidence shape was extended. On the exception path the original exception stays primary; the bound is available on its chained cause.',
'',
'Validation evidence: ' + link(scratch / 'summary.json') + ', ' + link(scratch / 'final-required.reports.jsonl') + ', ' + link(scratch / 'final-required.log') + ', ' + link(scratch / 'final-collection.log') + ', ' + link(scratch / 'loader-probes.json') + '. Each run’s command, outer bound outcome and elapsed time are in its adjacent run JSON. Tests used the assigned project interpreter, this worktree’s source, scratch basetemps and no more than four xdist workers. The initial required-suite run hit its 600-second bound; the initial collection run hit its 180-second bound. Both are retained and are not represented as complete runs.',
'',
'The final full cohort reached its 1,800-second outer bound. Only unfinished node IDs were selected for a separate 900-second continuation. This is combined coverage from bounded runs, not an uninterrupted green suite. Continuation evidence: ' + link(scratch / 'remaining-plan.json') + ', ' + link(scratch / 'remaining-required.json') + ', ' + (link(scratch / 'remaining-required.reports.jsonl') if (scratch / 'remaining-required.reports.jsonl').exists() else 'no completed continuation reports') + ', ' + link(scratch / 'remaining-required.log') + '.',
'',
'Combined required-suite outcomes by file, generated from saved per-test records:',
'']
for filename, counts in sorted(summary['by_file'].items()):
    lines.append('- ' + link(root / filename) + ': ' + ', '.join(str(value) + ' ' + key for key, value in sorted(counts.items())) + '.')
lines += ['', 'Findings and limits:', '',
'- The integration failures naming the changed callback source are reviewed-commit refusals: its working bytes differ from the current commit. The sandbox refused both add and commit with an index-lock permission error. ' + link(scratch / 'commit-attempt.txt') + ' records the commands and refusal. Per assignment, the files remain uncommitted; no check was weakened and no escalation was attempted.',
'- `CallbackAdapter.report` still takes the worker lock without a bound before reaching scope teardown. Thus this change fixes `_locked_stack`, but does not establish a global shutdown bound for a stuck worker. The lead should address that separate reporting path before claiming end-to-end bounded shutdown.',
'- Both real-loader witness processes exited successfully and retained their loader through worker release. During interpreter shutdown they emitted ignored generator-finalizer errors after interpreter globals had been cleared. These are preserved in the witness stderr. No clean Python-finalization claim is made, and no unsafe late cleanup was added.',
'- The local read-only review identified two issues: a poisoned scope could enter its body, and retention depended on a module binding. Both were fixed after review. Remaining findings are recorded for the lead in ' + link(scratch / 'review-findings.json') + '. The assignment prohibits filing GitHub issues from this helper.',
'',
'The Read case in ' + link(root / 'tests/test_native_shared_denials.py') + ' asserts that the not-prescribed denial is followed by passing runtime gates and `completed_pending_independent_review`, that `read_final` exactly reproduces the live result, and that the forbidden file does not exist. The first two completion assertions, plus replay of that completed result, require the full workflow as currently written. Denial classification, denial replay and absence of forbidden file access do not inherently require all generation stages. The same file already has focused saved-denial tests that forbid target resolution and reading.',
'',
'Its current lane is `ordinary`, through ' + link(root / 'utils/pytest_shard.py') + '. ' + link(root / '.github/workflows/main.yaml') + ' gives ordinary shards 45 minutes on pull requests and 60 minutes otherwise, with up to four workers. The synthetic attempt deadline is 7,200 seconds, excluding preparation. The supplied diagnosis recorded more than an hour on a loaded host; the timings ledger has no completed entry for this new Read case, so a quiet-host CI cost is not established. This helper did not run the denial workflow.',
'',
'Pin audit: ' + link(scratch / 'audit.json') + ', ' + link(scratch / 'pin-path-search.txt') + ', ' + link(scratch / 'pin-hash-search.txt') + '. Source digest before: `' + audit['old'] + '`. Proposed source digest: `' + audit['new'] + '`. No file/constant/old/new static-pin replacement is proposed because neither the source name nor its old digest identified a static pin.',
'',
'Branch `codex/callback-teardown-20261115` remains at `' + head + '`. Uncommitted files for the lead:', '']
for filename in files:
    lines.append('- ' + link(root / filename))
lines += ['', 'No native binary, provider call, GitHub write, push, merge or protected-file edit was performed. The lead owns integration and publication.', '']
raw = '\n'.join(lines)
assert chr(64) not in raw
handoff.write_text(raw)
assert handoff.read_text() == raw
print(json.dumps(dict(handoff=str(handoff), sha256=hashlib.sha256(raw.encode()).hexdigest(), head=head, source_old=audit['old'], source_new=audit['new']), indent=2))
