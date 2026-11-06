"""#4354 U1 round 3, 2026-11-06: preserve exact acceptance outcomes.

Inputs: scratch logs/XML and source identities. Outputs: Round 3 report and
committable evidence JSON. STATUS is written separately after the local commit.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

from native_u1_round2_20261106 import ROOT, SCRATCH


def main():
    identities = json.loads((SCRATCH/'r3-identities.json').read_text())
    batches = json.loads((SCRATCH/'r3-batches.json').read_text())
    evidence = {'created_utc': datetime.now(timezone.utc).isoformat(),
                'identities': identities, 'batches': [], 'checks': []}
    evidence['quiet_windows'] = [json.loads(path.read_text())
        for path in sorted(SCRATCH.glob('r3-quiet-window-observation*.json'))]
    evidence['original_fixture_reproduction'] = json.loads((SCRATCH/'r3-original-fixture-error.json').read_text())
    for path in sorted(SCRATCH.glob('r3-*.log')):
        text = path.read_text()
        exit_lines = [line for line in text.splitlines() if line.startswith('U1_CHECK_EXIT=')]
        summaries = [line for line in text.splitlines() if re.search(r'\b\d+ (passed|failed|error|errors|tests collected).* in \d', line)]
        evidence['checks'].append({'log': path.name, 'exit': exit_lines[-1] if exit_lines else 'no terminal exit',
                                   'launch': json.loads(text.splitlines()[0]),
                                   'summary': summaries[-1].strip('= ') if summaries else None})
    retries_path = SCRATCH/'r3-retry-roster.json'
    retries = json.loads(retries_path.read_text()) if retries_path.exists() else []
    evidence['retry_attempts'] = retries
    for number, files in enumerate(batches, 1):
        path = SCRATCH/f'r3-batch-{number:02}.xml'
        row = {'batch': number, 'files': files, 'completed_xml': path.exists(), 'failures': []}
        paths = [path] if path.exists() else []
        attempts = [attempt for attempt in retries if attempt['batch'] == number]
        if attempts:
            latest = {attempt['file']: attempt for attempt in attempts}
            paths = [SCRATCH/(attempt['name']+'.xml') for attempt in latest.values()
                     if attempt['exit'] in (0, 1) and (SCRATCH/(attempt['name']+'.xml')).exists()]
            row['completed_xml'] = set(latest) == set(files) and len(paths) == len(files)
            row['completion_basis'] = 'fresh individual-file retries; original failed/interrupted attempt retained and superseded'
            row['retry_logs'] = [attempt['name']+'.log' for attempt in attempts]
        row['suites'] = []
        for path in paths:
            tree = ET.parse(path)
            row['suites'].extend(node.attrib for node in tree.iter('testsuite'))
            for node in tree.iter('testcase'):
                for kind in ('failure', 'error'):
                    for failure in node.findall(kind):
                        row['failures'].append({'node': node.attrib.get('classname', '') + '::' + node.attrib['name'],
                                                'kind': kind, 'message': failure.attrib.get('message'),
                                                'traceback': failure.text})
        evidence['batches'].append(row)
    evidence['roster_totals'] = {key: sum(int(suite.get(key, 0))
        for row in evidence['batches'] for suite in row.get('suites', []))
        for key in ('tests', 'failures', 'errors', 'skipped')}
    evidence['roster_totals']['passed'] = (evidence['roster_totals']['tests']
        - sum(evidence['roster_totals'][key] for key in ('failures', 'errors', 'skipped')))
    evidence['roster_totals']['files'] = sum(len(row['files']) for row in evidence['batches'])
    evidence['roster_totals']['completed_batches'] = sum(row['completed_xml'] for row in evidence['batches'])
    roster = [relative for row in evidence['batches'] for relative in row['files']]
    assert roster == (SCRATCH/'regression-roster.txt').read_text().splitlines()
    assert len(roster) == len(set(roster)) == 66
    out = ROOT/'scripts/adhoc/native_u1_packets/round3_evidence.json'
    out.write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence['roster_totals'], sort_keys=True))
    lines = ['\n\n## Round 3 — caller contracts, bounded scanner adaptation, regression batches\n',
        '**Acceptance status: BLOCKED.** The D76 inventory is repaired, but the scanner still '
        'requires the later native CLI consumer. No successful after-scan or no-new-findings claim is made.\n',
        'Work remains on `codex/native-u1-selector-20261106`, linear from `e0b868b0e`. '
        'Only non-protected files were edited. Four composed packet postimages and four protected '
        'worktree files/checkers were verified by `native_u1_round3_20261106.py identities`; hashes '
        'are in `scripts/adhoc/native_u1_packets/round3_evidence.json`. No fetch, push, gh, provider '
        'call or real native executable was used. No PR/issues were filed under the offline restriction.\n',
        '### Changes and retained limits\n',
        '- Six public native-render RunSpec helpers now state validated-caller preconditions, '
        'including construction-before-origin-capture and non-executing replay limits. The '
        'executable AST before/after is identical; proof and hashes are retained in '
        '`r3-executable-ast.json`. The six new dataclass fields and both registration axes are '
        'classified in the closed D76 roster. Native capture pins its own inputs; the legacy '
        'provenance spelling-policy predicate does not select the new native axis. That limitation '
        'is explicitly recorded, not changed through a documentation fix.\n',
        '- Scanner admission now requires the BC1 zero-axis exclusion and ignores only a genuine '
        'leading literal docstring. Its existing disabled-API native dispatch proof uses the same '
        'docstring handling. Phase assembly recognizes exactly the same-spec D76 guard with a '
        'unique unshadowed local definition, a structural guard contract rather than a general '
        'purity assertion. Positive API-scope derivation and hostile executable-prefix, missing-BC1, '
        'wrong-spec and added-statement controls are retained. No exception or model-facing list '
        'was added. The CLI-consumer requirement remains an explicit refusal.\n',
        '- The delegated scanner fixture now copies both native sources needed by the new '
        'shared-selector dispatch. The BC1 historical proposal test preserves its original manifest '
        'and requires the exact later U1 packet hash chain when the source has evolved. It neither '
        'restamps the historical proposal nor accepts arbitrary subsequent source.\n',
        '- The direct-registration fixture names its existing shell version stub '
        '`synthetic-runtime`, rather than `claude`. The offline guard is unchanged; no actual '
        'native runtime is run. This is an environment-compatible test fixture adjustment.\n',
        'Read-only local diff review found that re-running the contract producer could '
        'overwrite its original AST preimage evidence. R3-F1 is recorded here for the '
        'offline issue handoff and fixed by requiring the exact round-two source before '
        'editing. Final identity checks independently compare both ASTs to that commit. '
        'The unresolved CLI/source-closure dependency is R3-F2; it remains blocked rather '
        'than being hidden by a fallback. R3-F3: the final STATUS helper initially used '
        'a whole-file rewrite, risking loss of a concurrent lane append; it now requires '
        'codex to be the final section and appends directly. R3-F4: the original '
        '60-second creation monitor allowed the disclosed quiet-window overlaps. '
        'The replacement controller and postflight use one-second creation monitoring, while removal checks remain '
        'at least 60 seconds apart, and re-canaries the modified launcher. This does '
        'not retroactively validate any overlap or claim zero detection latency. '
        'No GitHub issue was created offline.\n',
        'R3-F5: splitting the roster exposed an inherited test-isolation defect in '
        '`test_wave7_5213_d76_legacy_registration.py::test_registered_legacy_builder_keeps_paths_at_corpus_root` '
        'for the direct builder. Its first error was `ModuleNotFoundError: No module named '
        "'prepare_direct'`. `runpy.run_path` does not install the script directory; the "
        'test had borrowed that path from unrelated module collection. The fixture now '
        'prepends the selected builder directory with monkeypatch, matching ordinary '
        'script invocation, without modifying the historical builder. The original '
        'batch-13 failure and a fresh file retry are both retained.\n',
        'R3-F6: final guards retain the deterministic-import-directory assertion failure. '
        'The composed discovery reports three extra directories: `notes/claudecode_direct`, '
        '`notes/matched_cborg_2026-09-13`, and its `native_controls` subdirectory. '
        'Both discovery controls pass on the M7 baseline, so this is not attributed '
        'to an inherited baseline failure. Static source inspection identifies the '
        'new renderer import of `native_execution_registration` (for `RUNTIME_KEYS` '
        'and `ROUTE`), which imports `native_attribution_controller` and '
        '`native_execution_authority`; those modules contain the three path additions. '
        'This remains a U1 integration finding: neither the existing closure assertion '
        'nor the required executable-AST equality was weakened to remove it. A later '
        'executable refactor needs a separate acceptance decision.\n',
        '### Retry-1 diagnosis and attribution\n',
        '`r2-api-regressions-retry1.log` contains only dots/F/E markers and termination (-15), '
        'with no node IDs or traceback summary. Exact attribution of its individual markers is '
        'therefore unavailable. The following named diagnoses use retry 2 and fresh targeted '
        'reproduction; they are not fabricated traceback recovery from retry 1.\n',
        '- `test_bc1_selection.py::test_proposal_is_exact_and_does_not_modify_protected_source`: '
        'historical whole-file postimage assertion conflicts with the additional native hook. '
        '**Packet-induced test incompatibility**, repaired with the exact proposal-chain check.\n',
        '- All 15 `test_bc1_g2_round2.py` setup errors share `entry_probe -> scopes(root)`: the '
        'fixture copies the modified shared selector but omits `native_shared_render.py`, which '
        'its static dispatch proof reads. **U1-induced fixture incompleteness**, repaired by '
        'copying the validator and contract sources. Node names from retry 2 are listed below.\n',
        '- `test_wave7_5213_d76_binding_records.py::test_direct_preparation_records_absolute_registered_inputs`: '
        'fresh first error is `RuntimeError: U1 offline: native/network executable denied`, from '
        '`prepare_direct.py:194` querying the synthetic stub named `claude`. **Environment/guard '
        'interaction**, repaired by the descriptive synthetic executable name; production and '
        'the guard are unchanged.\n',
        '- Retry-1 exit -15 was the recorded quiet-window interruption, not a test pass or a '
        'load-induced timeout. Retry-2 deadline expiry does not establish host load as its cause. '
        'No timeout is credited as a pass.\n',
        '```text\n']
    retry = (SCRATCH/'r2-api-regressions-retry2.log').read_text()
    lines.extend(line + '\n' for line in retry.splitlines() if re.search(r'\b(FAILED|ERROR) tests/', line))
    lines += ['```\n', 'Reconstructed original fixture first error: `'
              + evidence['original_fixture_reproduction']['error_type'] + ': '
              + evidence['original_fixture_reproduction']['first_error'] + '`. '
              'Full traceback and original fixture hash: `r3-original-fixture-error.json`.\n',
              '### Validation ledger\n',
              'Each pytest invocation uses Python 3.13.12, at most `-n 2`, a 3600-second '
              'deadline, credential-stripped environment and unchanged network/native audit guard. '
              'The canary used the same launcher and two-worker path; its nonempty log was '
              'checked before batch launch. It proves synthetic render/replay and persistence, '
              'not native execution, concurrency behavior or performance.\n',
              'Final specificity guards: **463 passed, 9 failed, 21 errors**. Seven '
              'failures and all 21 setup errors stop at the missing offline-render CLI '
              'consumer; the other failures are deterministic import-directory expansion '
              '(R3-F6) and absent `native_shared_stage`/`native_shared_receipts` closure '
              '(R3-F2). Both corresponding M7 discovery controls pass. The isolated '
              'M7 legacy-builder control reproduces the same `prepare_direct` error '
              '(12 passed, 1 failed); the repaired composed file passes all 13. '
              'The 10 final semantic scanner controls pass.\n',
              '| Log | Result |\n|---|---|\n']
    for row in evidence['checks']:
        lines.append(f"| `{row['log']}` | {row['summary'] or 'No pytest summary'}; {row['exit']} |\n")
    lines.append('\nRoster XML totals (skipped includes expected failures): `'
                 + json.dumps(evidence['roster_totals'], sort_keys=True) + '`. '
                 'The per-batch exit codes and logs remain authoritative for completeness.\n')
    lines += ['\n### Per-batch roster and first errors\n']
    for row in evidence['batches']:
        lines.append(f"\nBatch {row['batch']:02}: " + ', '.join('`'+p+'`' for p in row['files']) + '.\n')
        if not row['completed_xml']:
            lines.append('No completed XML; not accepted as a completed passing batch.\n')
        if row.get('retry_logs'):
            lines.append('Completion basis: ' + row['completion_basis'] + '. Logs: '
                         + ', '.join('`'+name+'`' for name in row['retry_logs']) + '.\n')
        for failure in row['failures']:
            lines.append(f"- `{failure['node']}`: {failure['kind']}: {failure['message']}\n")
    lines += ['\n### Quiet-window accounting\n',
        'U0 lock `cpu-neutral-01` began at 2026-11-06T06:25:31.563396Z, with '
        'expected end 07:00:01.563396Z. The already-running guard batch was stopped '
        'at its next 60-second poll, approximately 06:25:51.38Z: about 19.82 seconds '
        'of overlap, disclosed for the lead\'s timing-evidence disposition. Its '
        'exit -15 is not credited. The launcher waited in 60-second intervals '
        'before resuming; the lock was not removed or modified. Exact observed lock '
        'metadata is retained in `r3-quiet-window-observation.json`. The lock was absent '
        'before the batch canary launched at approximately 06:37:51.51Z.\n',
        'A second lock, `causal-control-01`, began at 07:34:42.542300Z with expected '
        'end 08:09:12.542300Z. Batch 08 stopped at approximately 07:35:31.92Z, '
        'about 49.37 seconds after lock creation. Its interrupted results are not '
        'credited; the fresh individual-file retries provide any subsequent completion '
        'evidence. The second lock metadata is retained in '
        '`r3-quiet-window-observation-2.json`. No other process or lock was changed.\n',
        'A third lock, `causal-treatment-01`, began at 07:50:23.329584Z with expected '
        'end 08:24:53.329584Z. Batch 09 stopped at approximately 07:50:31.98Z '
        '(about 8.65 seconds of overlap). Its original attempt is not credited. '
        'The waiting U1 controller PID 64091 was verified to have no children and '
        'terminated; no other session process was signalled. The replacement '
        'controller preserves the original roster in `r3-original-batches.json`, '
        'splits all unstarted files into individual batches, waits 60 seconds across '
        'the handoff, and re-canaries before proceeding.\n',
        'The fourth lock, `second-control-01`, began at 08:53:10.062887Z with '
        'expected end 09:27:40.062887Z. The one-second creation monitor stopped '
        '`r3-retry-batch-09-file-02-attempt-01` at approximately 08:53:10.41Z '
        '(about 0.35 seconds of overlap). That attempt is not credited; the retry '
        'loop preserves preceding completed files and retries this file under a '
        'new log after removal. This observed shorter response is not a claim of '
        'zero detection latency or acceptance of U0 timing evidence.\n',
        'The fifth lock, `second-treatment-01`, began at 09:05:12.008262Z with '
        'expected end 09:39:42.008262Z. Attempt 02 of the same file had begun '
        'during the brief lock-free gap and stopped at approximately 09:05:12.52Z '
        '(about 0.51 seconds of overlap). It is retained as incomplete and is '
        'not included in the accepted roster totals.\n',
        '\n### Scanner and handoff\n',
        'M7 retained baseline: 9 violations; `listed_not_derived` has 7 entries '
        '(audit_batches, audit_grammar, audit_omissions, evidence_assertions, grounding, scope, '
        'source_metadata). The after scanner exits 2, so neither findings nor '
        '`LISTED_NOT_DERIVED` can be compared. The explicit missing CLI-consumer refusal is '
        'not a ninth/tenth finding. Ignore-independent hidden-file-inclusive search under '
        '`src/data_sheets_schema` confirmed this U1 worktree has only the four U1 native shared '
        'modules, not the later stage/receipts/controller implementations. Rendering references '
        'to those later helpers does not establish their availability. Completing those other '
        'units or weakening the scanner was not smuggled into this repair.\n',
        'The task remains blocked on source-derived coverage of the complete native route. '
        'Integration, A21 rebuild, independent review and complete-path/native execution '
        'acceptance remain outside this local handoff. The lead must resolve the U1 versus '
        'later-unit scanner acceptance dependency. No merge or launch is authorized.\n']
    report = ROOT.parent/'plans/reviews/native_u1_2026-11-06.md'
    prior = report.read_text()
    assert '\n## Round 3 —' not in prior
    report.write_text(prior + ''.join(lines))
    assert report.stat().st_size > len(prior.encode()) and out.stat().st_size
    print(report)


def status():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).decode()
    assert not dirty, 'Commit the non-protected worktree result before final status.'
    report = ROOT.parent/'plans/reviews/native_u1_2026-11-06.md'
    assert '\n## Round 3 —' in report.read_text()
    path = ROOT.parent.parent/'data-sheets-schema/notes/coordination/STATUS.md'
    prior = path.read_text()
    marker = 'Native U1 round 3 local handoff'
    assert marker not in prior
    sections = list(re.finditer(r'^### codex\s*$', prior, re.MULTILINE))
    assert len(sections) == 1, 'Require one actual codex heading, not a prose reference.'
    section = sections[0].start()
    next_section = prior.find('\n### ', section + 1)
    assert next_section == -1, 'Codex must remain the final section for a safe append.'
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    entry = (f'\n- {timestamp} — {marker}: `{head[:9]}` on `codex/native-u1-selector-20261106`. '
             'D76 caller contracts/closed fields repaired with executable-AST equality; '
             '66-file roster: 1,569 passed, 1 expected failure, no failures/errors; '
             '23,206 collected; packet/fixture regressions diagnosed and repaired. Per-batch evidence '
             'in `d4d-executions/plans/reviews/native_u1_2026-11-06.md` Round 3. '
             'BLOCKED: scanner exits 2 at the missing later-unit native render CLI consumer; '
             'native stage/receipts closure and expanded deterministic import paths also remain; '
             'guards 463 passed/9 failed/21 errors, no no-new-findings claim. '
             'Protected worktree bytes unchanged, packets scratch-only, '
             'offline/no native executable. Quiet-window interruption and overlap disclosed. '
             'Next: lead resolves staged scanner acceptance and reviews remaining evidence. Stopped.\n')
    with report.open('a') as stream:
        stream.write(f'\nRound-three local commit: `{head}`. Work stops at this handoff.\n')
    with path.open('a') as stream:
        stream.write(entry)
    assert path.read_text().count(marker) == 1 and head in report.read_text()
    print(entry.strip())


if __name__ == '__main__':
    status() if sys.argv[1:] == ['status'] else main()
