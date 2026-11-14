"""U3-E 2026-11-08 final local handoff evidence.
Inputs: retained final summaries, report and committed tree; outputs: final
report/PR draft and identity/review evidence. Does not write STATUS or publish.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-native-u1u3'
REPORT = ROOT.parent / 'plans/reviews/native_u1u3_assembly_2026-11-08.md'
D = 'ff3aaaddba5754e6624f0c435397403f29505459'
def git(*args):
    return subprocess.check_output(['git', '-c', 'core.fsmonitor=false', *args], cwd=ROOT, text=True).strip()
def main():
    if sys.argv[1] == 'preflight':
        for path in (ROOT / 'scripts/adhoc').glob('*u1u3*20261108.py'):
            ast.parse(path.read_text(), filename=str(path))
        ast.parse((ROOT / 'scripts/adhoc/u3e_parity_plugin_20261108.py').read_text())
        print('Helper syntax parsed without imports or bytecode writes')
        return
    assert sys.argv[1] == 'report'
    assert not git('status', '--porcelain')
    head = git('rev-parse', 'HEAD')
    delta = git('diff', '--name-only', D, head).splitlines()
    assert delta and all(path.startswith('scripts/adhoc/') for path in delta)
    identity = {'head': head, 'branch': git('branch', '--show-current'), 'final_D': D,
                'changed_from_D': delta, 'production_tests_scanner_unchanged': True}
    (OUT / 'final-identity.json').write_text(json.dumps(identity, indent=2) + '\n')
    rows = json.loads((OUT / 'validation-summary.json').read_text())
    coverage = json.loads((OUT / 'coverage-reconciliation.json').read_text())
    parity_path = OUT / 'api-render-parity.json'
    parity = json.loads(parity_path.read_text()) if parity_path.exists() else []
    parity_text = str(sum(row['equal'] for row in parity)) + '/14 exact instruction artifacts equal' if len(parity) == 14 else 'Artifact parity did not complete; retained outputs are not parity acceptance.'
    packet_path = OUT / 'packet-api-render-parity.json'
    packet_parity = json.loads(packet_path.read_text()) if packet_path.exists() else []
    packet_text = str(sum(row['equal'] for row in packet_parity)) + '/14 exact instruction artifacts equal with all four packets installed in scratch' if len(packet_parity) == 14 else 'Composed packet artifact parity did not complete.'
    old = REPORT.read_text()
    (OUT / 'report-before-final.md').write_text(old)
    old = old.replace('Work in progress: this report is not an acceptance or completion claim. Final validation results will be recorded below before the single STATUS handoff.',
        'Offline assembly and evidence handoff complete; integration acceptance is BLOCKED. The desired all-green packet composition was not achieved. No push or native launch occurred.')
    old = old.replace('## Validation in progress', '## Validation and retained interruptions')
    final = '\n## Final frozen handoff\n\n'
    final += 'Branch `' + identity['branch'] + '`, local HEAD `' + head + '`. All helper source is committed locally. Only assembly helpers differ from final D10; production, tests and scanner remain identical. No schema 3.2.0 integration, protected packet installation, network, push or CI occurred. The exact source commit for every invocation is retained in its plan and final ledger; helper-only later commits do not change tested production bytes.\n\n'
    final += 'Saved main versus unpatched candidate: ' + parity_text + '. Saved main versus packet composition: ' + packet_text + '. See `scratch-native-u1u3/api-render-parity.json`, `packet-api-render-parity.json` and retained raw files; no normalization was used.\n\n'
    final += 'Coverage: ' + str(coverage['collected_unique_nodes']) + ' unique collected nodes, ' + str(coverage['planned_collected_nodes']) + ' planned affected nodes, ' + str(coverage['candidate_observed_unique_nodes']) + ' unique candidate nodes observed in completed XML. Uncovered planned nodes: ' + str(len(coverage['uncovered_planned_nodes'])) + '. Unexecuted repository nodes: ' + str(len(coverage['unexecuted_repository_nodes'])) + '. Full exact lists and mixed outcomes are in `coverage-reconciliation.json`; execution coverage includes failures/errors/skips and is not a passing count. Interrupted runs without XML receive no credit. Partitioned coverage does not establish original same-process ordering.\n\n'
    final += 'Every failing, errored and skipped observation is listed by exact pytest node in `scratch-native-u1u3/exact-nonpasses.md` and `exact-node-ledger.json`, with full traces in retained XML. The final per-run wall times and counts follow; all host loads and source roots/commits are in `validation-summary.json`, and immediate-run file digests in `evidence-hashes.json`. Blank/incomplete counts are not passes.\n\n'
    final += (OUT / 'validation-table.md').read_text()
    final += '\n### Additional findings and attribution\n\nThe two legacy recorder deadline failures are distinct from the two declared public-completion blockers: `tests/test_native_attribution_results.py::test_actual_completed_recorder_retains_live_file_requirements[hardlink]` and `tests/test_native_attribution_results.py::test_actual_correction_and_recorder_saved_trace[recorder]`. Baseline comparisons retain the same selected deadlines. Timing differences under different host loads do not establish causality. The census helper initially failed under two workers because its bootstrap evidence lookup assumes a serial basetemp layout; the serial recheck preserves the original failed evidence. Schema subprocess failures and the eight launcher failures are environment checks, not waived acceptance gates.\n\n'
    for name in ('census-serial-recheck', 'baseline-legacy-deadlines', 'baseline-schema', 'baseline-specificity', 'packet-specificity-hooks', 'final-sg2-none', 'final-sg2-explicit', 'final-sg2-conventional'):
        matches = [row for row in rows if row['run'] == name]
        final += '- `' + name + '`: ' + (json.dumps(matches[0]['counts'], sort_keys=True) + '; ' + str(round(matches[0]['seconds'], 2)) + ' supervised seconds; cleanup ' + str(matches[0]['cleanup_verified']) if matches else 'not completed') + '.\n'
    final += '\n### Read-only review and issue handoff\n\nAssembly review checks preserved merge ancestry, all overlapping-file resolutions, exact packet pre/postimages, unchanged scanner/checker, helper-only delta, source-stability witnesses and non-passing evidence. Findings remain local because network and gh are forbidden. Future online issue records must separately track U3E-R1 scanner container derivation; R2 inherited patch whitespace (preserve frozen bytes); R3 supervisor overrun; R4a CLI constructor/contract/runtime derivation and obsolete negative test; R4b missing D76 boundary declarations; R4c runtime RunSpec witness; R5 isolated launcher/schema tooling; R6 legacy recorder deadlines; R7 census harness layout. No finding was silently fixed in production or dropped. No remote issue identifier is claimed.\n\nOwner approval of the exact protected bundle, later schema-release integration, source/identity refresh, sound scanner and D76 repairs, complete affected validation/normal CI and independent review remain required. P3-4 is partial; the two public-completion deadline blockers remain. No engineering, performance, scientific or native admission acceptance is claimed.\n'
    REPORT.write_text(old + final)
    draft = OUT / 'pr-body.md'
    body = draft.read_text() + '\nFinal local assembly HEAD: ' + head + '. Unpatched candidate: ' + parity_text + '. Packet composition: ' + packet_text + '. Final counts, SG2 results and exact nonpasses are in the assembly report and retained ledger. The branch remains blocked for integration acceptance.\n'
    assert '@' not in body
    draft.write_text(body)
    assert REPORT.stat().st_size > 0 and draft.stat().st_size > 0
    evidence = [REPORT, draft, OUT / 'final-identity.json']
    evidence += [p for p in (OUT / 'scanner-runs.json', OUT / 'baseline-scanner.json', OUT / 'packet-parity-composition/composition.json', parity_path, packet_path, OUT / 'baseline-parity-repaired-manifest.json') if p.is_file()]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence}
    (OUT / 'handoff-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(json.dumps(identity, indent=2))
if __name__ == '__main__':
    main()
