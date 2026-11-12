#!/usr/bin/env python3
"""Compile helper-2 sequence review and proposed schema migration, 2026-11-12.
Inputs: assigned source worktree, untouched agy draft, local Git, saved JUnit.
Outputs: scratch audit/search evidence and the requested lead handoff.
No native command, model, provider, network, pin update or GitHub write.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET

E = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
ROOT = E / 'codex-native-launch-sequence-20261112'
ORIGINAL = E / 'agy-native-launch-sequence-20261112'
REPORT = E / 'codex-development-efficiency-20261111'
SCRATCH = E / 'scratch-h2-launch-sequence-20261112'
BASE = '5d63d0a77dc43c064cfc2b376355f98009dd5b6e'
DRAFT = 'd07eccefb59938f8b625498247259f17e5c155ec'
MAIN = '7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1'
SOURCE = 'src/data_sheets_schema/native_launch_sequence.py'
TEST = 'tests/test_native_launch_sequence.py'
PROTECTED = ['src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json']

def sha(raw): return hashlib.sha256(raw).hexdigest()
def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', '-C', str(ROOT), *args])
def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
def save(name, value):
    path = SCRATCH / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    return path

originals = []
for path in (SOURCE, TEST):
    received = git('show', DRAFT + ':' + path)
    assert received == (ORIGINAL / path).read_bytes()
    originals.append({'path': path, 'draft_sha256': sha(received), 'current_sha256': sha((ROOT / path).read_bytes()),
                      'original_unchanged': True})
protected = []
for path in PROTECTED:
    raw = (ROOT / path).read_bytes()
    assert raw == git('show', BASE + ':' + path) == git('show', MAIN + ':' + path)
    protected.append({'path': path, 'sha256': sha(raw)})
# Part C remains exactly the candidate; no changed version or closed key set.
for path in ('src/data_sheets_schema/native_launch_review.py',
             'src/data_sheets_schema/native_execution_registration_v2.py',
             'src/data_sheets_schema/native_subscription_admission.py'):
    assert (ROOT / path).read_bytes() == git('show', BASE + ':' + path)
searches = []
patterns = {'sequence-references': 'native_launch_sequence',
    'part-c-closed-shapes': 'TERMS_KEYS|d4d_native_execution_review_bundle_v2|d4d_native_owner_launch_terms_v1|sequence_script_sha256|account_quiet',
    'part-c-consumers': 'validate_bundle\\(|validate_terms\\(|native_launch_review|review\\.KIND|review\\.TERMS_KIND',
    'draft-source-pin': sha(git('show', DRAFT + ':' + SOURCE)),
    'review-source-pin': sha((ROOT / 'src/data_sheets_schema/native_launch_review.py').read_bytes()),
    'local-instructions': '^',
}
for name, pattern in patterns.items():
    command = ['rg', '--no-ignore', '--hidden', '-n', '-g', '!.git']
    if name == 'local-instructions': command += ['-g', 'AGENTS.md']
    command += [pattern, '.']
    result = subprocess.run(command, cwd=ROOT, capture_output=True)
    assert result.returncode in (0, 1), result.stderr
    path = SCRATCH / (name + '.txt')
    path.write_bytes(result.stdout)
    searches.append({'command': command, 'returncode': result.returncode, 'path': str(path),
                     'sha256': sha(result.stdout), 'bytes': len(result.stdout)})
cohorts = []
for directory in sorted((SCRATCH / 'tests').iterdir()):
    outcome = json.loads((directory / 'outcome.json').read_bytes())
    assert outcome['cleanup_verified'] is True
    root = ET.fromstring((directory / 'pytest.xml').read_bytes())
    counts = Counter()
    for case in root.iter('testcase'):
        counts[next((key for key in ('failure', 'error', 'skipped') if case.find(key) is not None), 'passed')] += 1
    cohorts.append({'name': directory.name, 'counts': dict(counts), 'outcome': outcome,
        'files': {name: sha((directory / name).read_bytes()) for name in
                  ('pytest.log', 'pytest.xml', 'pytest-command.json', 'network.json', 'origins-before.json', 'outcome.json')}})
status = git('status', '--short').decode()
assert not status.strip(), status
check = git('diff', '--check', BASE, 'HEAD').decode()
commits = git('log', '--reverse', '--format=%H %s', BASE + '..HEAD').decode().strip().splitlines()
assert len(commits) == 3
pins = {str(path.relative_to(ROOT)): sha(path.read_bytes())
        for path in sorted((ROOT / 'src/data_sheets_schema').rglob('*'))
        if path.is_file() and path.suffix in ('.py', '.yaml', '.json')}
base_pins = {path: digest for path, digest in pins.items() if path != SOURCE}
draft_pins = {**base_pins, SOURCE: originals[0]['draft_sha256']}
data = {'base': BASE, 'head': git('rev-parse', 'HEAD').decode().strip(), 'commits': commits,
        'originals': originals, 'protected': protected, 'status': status, 'diff_check': check,
        'diff_stat': git('diff', '--stat', BASE, 'HEAD').decode(), 'searches': searches, 'cohorts': cohorts,
        'static_package_map_sha256': {'candidate': sha(canonical(base_pins)), 'draft': sha(canonical(draft_pins)),
                                      'final': sha(canonical(pins))},
        'scope': 'Static source-map hashes only, not new registration or approval.',
        'report_script': {'path': str(Path(__file__).resolve()), 'sha256': sha(Path(__file__).read_bytes())}}
audit = save('h2-launch-sequence-audit.json', data)
lines = [
'# Helper 2: launch sequence and review-bundle proposal', '',
'Parts A and B are complete and locally committed. The draft inherited environment/module selection, accepted incomplete success responses and unverified result hashes, and omitted script retention and delegated time bounds. The repaired script runs exactly capture, guard on that new capture, then launch; it stops on a failed command, malformed or incomplete result, hash mismatch, changed input, or delegated-time refusal. All final offline tests pass. Part C is deliberately not implemented: the smallest key additions would change the meanings of the existing closed bundle v2 and owner-terms v1 schemas, and the execution reader currently ties the review version to authority version 2. The required versioned proposal and consumer migration are below.', '',
'No real native_generation subcommand, native binary, model, provider, push, pull request or GitHub write occurred. The agy originals and protected files are unchanged. The sequence does not authenticate the owner, account quietness, starter independence or host state, and this unratified amendment is not launch permission.', '',
'## Commits and review', '',
*['- ' + item for item in commits], '',
'These preserve the unreviewed agy helper-2 draft, the Part A repairs, and Part B separately. There is no Part C implementation commit. The branch is `codex/native-launch-sequence-20261112`, worktree `' + str(ROOT) + '`. The working tree is clean and the full candidate-to-head diff passes `git diff --check`.', '',
'The assignment source was read against N1 draft v10 at `127cc0bd69d73fcd21d94978bf5e0ee60e0e950c`, including D12, B4, the event order, items z/aa/ad and prerequisites 4/10. N1.5 still says the script writes its hash; N1.9 item 10 and this assignment explicitly require saved bytes with the reviewer recomputing the hash. The implementation follows the latter, without self-reported script-hash evidence.', '',
'## Draft findings and fixes', '',
'- LS-F1: inherited environment and `-m` module resolution let PYTHONPATH or the current directory select the implementation. The original subprocess test positively asserted that behavior. The child now uses an explicit source root derived from the running file, isolated Python startup, a fixed environment and fixed cwd. An actual subprocess test copies only the sequence, pure wire helper and a fake native_generation into a temporary test package; it proves ambient PYTHONPATH and a secret sentinel do not reach the fake child. No real native command is used.',
'- LS-F2: command identity, guard output path and launch success fields were optional. A nonempty arbitrary launch result could be called completed. They are now mandatory, with exact command/path, final state and boolean runtime-gate success checks.',
'- LS-F3: manifest paths and digest strings were forwarded without checking actual saved files. Capture output now must name a newly produced allowed slot under the exact word digest and its manifest hash must match. Guard path and lowercase SHA-256 must match the saved guard. The real guard command still owns full capture/current-claim validation; any refusal there stops before launch.',
'- LS-F4: stdout was accumulated in memory, stderr was dropped, and outputs were only created after the child. Both streams are now exclusively created before spawning, flushed and fsynced, with command argv/start/end/return code recorded. Stdout is bounded before parsing. Raw output, stderr and arbitrary exception text are not printed to the terminal. Streaming output avoids unbounded in-memory capture, but it is not a disk quota or a new process deadline; the underlying commands retain their own limits.',
'- LS-F5: concurrent invocations could both pass packet preflight and start a capture before either wrote its output. An exclusive sequence-start.json claim now prevents a second start sharing that packet. Existing targets, including dangling symlinks, are never overwritten.',
'- LS-F6: the draft required the capture root to exist even though the capture producer can create it, and applied the small default wire-file bound to all inputs. A canonical absent capture root is now allowed; input reads use the front door command-output bound. Inputs are retained and checked again between commands, including the capture manifest before launch.',
'- LS-F7: no own-script byte retention or delegated-time checks. Part B implements both as described below.', '',
'Checked and found sound in the draft: the command order and flag mapping; no retry/resume/skip path; nonzero exits stop before the next command; ordinary malformed/duplicate JSON refusal; exclusive final-file writes; and the need to inspect launch results because the front door can return exit zero with a failed attempt. Those properties remain covered. The read-only review did not change files while reviewing. Findings are recorded here rather than sent to GitHub, as the assignment forbids GitHub writes.', '',
'## Part B behavior', '',
'At startup the packet gets sequence-start.json and an exclusive sequence-script.py copy of the running file before any subcommand. sequence.json names the copied path but contains no claimed script SHA-256. The reviewer must recompute it from those saved bytes.', '',
'Optional flags are `--direction-recorded-at` and `--host-confirmed-at`. Both must be supplied together as YYYY-MM-DDTHH:MM:SSZ, optionally with one to six fractional-second digits. Offsets, spaces, date-only strings, invalid dates and leap-second strings refuse. Start must be no earlier than either timestamp and no more than 1800 seconds after either. Both endpoints are included. The checks run at entry and again immediately before capture, preventing preflight time from crossing the limit. The two supplied timestamps, started_at and delegation_checked_at are saved in sequence.json. With neither flag the owner-start path has no delegated time limit. A timestamp refusal dispatches no command.', '',
'Tests cover the exact boundary, one second outside each bound separately, each future timestamp, each missing counterpart, malformed timestamps, elapsed preflight, no-time owner start, and saved source bytes present before every command. These are declared timestamps, not proof that an owner gave a direction or confirmed the host. Reuse of a direction in a different packet is not authenticated or tracked by this script; the recorded-direction and operator duties remain lead/owner checks.', '',
'## Saved offline tests', '',
'| Cohort | Passed | Failed | Errors | Skipped |', '| --- | ---: | ---: | ---: | ---: |']
for row in cohorts:
    lines.append('| ' + row['name'] + ' | ' + ' | '.join(str(row['counts'].get(key, 0)) for key in
        ('passed', 'failure', 'error', 'skipped')) + ' |')
lines.extend(['', 'Counts come from saved JUnit and overlap across reruns. Evidence root: `' + str(SCRATCH / 'tests') + '`. Each run retained command/log/JUnit, origin witnesses, network-denial witness and verified cleanup. The canary exercised the same runner and file-persistence path before the whole cohort. No full suite, scanner clearance, real CLI capture or launch acceptance is claimed.', '',
'## Part C: stop condition and exact proposal', '',
'The assignment says to stop before implementation if the change alters an existing version meaning or needs an unresolved choice. Adding required keys directly would alter native_launch_review.py TERMS_KEYS for d4d_native_owner_launch_terms_v1/version 1 and the exact bundle key set for d4d_native_execution_review_bundle_v2/version 2. Making them optional would instead leave old evidence admissible as current, which the assignment forbids. Moreover native_execution_registration_v2._authorizations currently checks every review/CI/word record.version against the single execution VERSION=2 before selecting the bundle reader. A new review version cannot pass that unchanged reader. I stopped before changing any of these schemas or readers.', '',
'Recommended migration for the lead to approve:', '',
'1. Introduce `d4d_native_execution_review_bundle_v3`, version integer 3, with the existing bundle fields plus exactly `sequence_script_sha256`: a string matching lowercase [0-9a-f]{64}. Require it to equal the registered dependency package_sources entry for src/data_sheets_schema/native_launch_sequence.py. During current admission, also verify the actual registered script bytes through the source-authority check. At saved packet review, hash sequence-script.py independently and compare to this bundle key; never use a hash asserted by sequence.json. No new path key or self-referential hash inside the script is needed.',
'2. Introduce `d4d_native_owner_launch_terms_v2`, version integer 2, with the prior terms plus exactly `account_quiet`: JSON boolean true, tested by identity rather than truthiness. It means the owner confirms every session drawing on the registered account stands down from before capture until attempt end and none monitors it. False, null, 1, strings or absence refuse current admission. This is a declared owner confirmation, not telemetry or an authenticated account observation.',
'3. Keep the historical bundle-v2 and terms-v1 readers byte-shape compatible, without defaulting or adding missing fields on readback. Add explicit current/history dispatch: new bundle-v3 requires terms-v2, and historical bundle-v2 requires terms-v1. Current capture, current guard preparation and current launch must require the new pair; read_final and historical guard/snapshot/transcript replay must retain the old pair as evidence only. The authority, CI and coded word stay version 2; decouple only the review-version branch in _authorizations instead of globally changing VERSION.',
'4. Current enforcement must cover native_generation capture/guard entry, native_subscription_capture.capture_subscription and _current_authority, native_subscription_admission.preflight_current_selection and context(current=True), and execution authorization. Historical capture readers and context(current=False) pass the historical mode. Guard v2 continues to hash the complete owner statement and dispatch validate_terms by the explicit statement version; its historical snapshot replay must not silently bless old terms as current.',
'5. Preserve fixed historical fixtures, add new-version fixtures with the full registered script pin, and add mutation tests for unknown/mixed versions, missing/extra keys, uppercase or wrong digest, source/packet byte mutation, non-boolean quiet values, and all current entry points refusing the historical pair. Test historical readback both before and after mutation without synthesizing approval.', '',
'The required lead choice is the explicit migration of the review and owner-terms schemas independently of execution authority, rather than reinterpreting version 2/version 1. No Part C keys or schema versions were implemented, so the script hash does not yet have an accepted place in the live review bundle. The two capabilities remain gated on N1 ratification and this migration.', '',
'## Part C source inventory and pin impact', '',
'The complete ignore-independent, hidden-file-inclusive searches are saved in the audit and scratch text files. They cover the whole assigned worktree, excluding only the Git pointer. The closed key sets are defined in native_launch_review.py; construction is in tests/utils/native_u4b_fixtures.py bundle_for. tests/utils/native_synthetic_evidence.py consumes that builder. Direct shape/version/readback coverage includes test_native_launch_review.py, test_native_u4b_a4_review.py, test_native_u4b_a3_policy.py, test_native_subscription_guard_v2.py and the capture/admission/reservation/readback cohorts. The saved search lists every matching call site, including validate_bundle and validate_terms consumers.', '',
'The scanner references native_launch_review in the integrated registration import contract; no direct literal pin of its current complete bytes or of the draft sequence bytes was found in the worktree. No source-manifest entry directly names the new sequence. The scanner was not run or repinned; new command-dispatch code still needs the lead scanner review. No protected boundary-contract identity names either changed sequence function, and the offline discovery test finds no new RunSpec boundary from the sequence module.', '',
'Actual identity changes from Parts A/B:', '',
'- The package source roster gains src/data_sheets_schema/native_launch_sequence.py. Its final SHA-256 is `' + originals[0]['current_sha256'] + '`. The received draft SHA-256 was `' + originals[0]['draft_sha256'] + '`.',
'- dependencies.base.package_sources, its containing dependency identity/hash, source_commit, and verified consumer identities that include the new source change. Static candidate/draft/final package-map hashes are retained in the audit JSON.',
'- The permission production_sources list includes every nonempty Python package member, so its roster, byte counts, production SHA-256, permission expectation/probe bindings and registration bindings change. Downstream review/word/capture/guard/run bindings must be freshly derived by the lead; none was updated here.',
'- Part C would additionally change native_launch_review and its current-admission/version-dispatch consumers and fixtures, with the same transitive identity effects plus new bundle/owner-statement and review_sha256/owner_statement_sha256 values. Those are proposed effects only; those production files are unchanged.', '',
'All four protected files remain equal to the candidate and integrated main `' + MAIN + '`, as computed in the audit. No prompt, source-manifest, scanner or closure pin was updated.', '',
'## Handoff artifacts', '',
'Audit: `' + str(audit) + '`, SHA-256 `' + sha(audit.read_bytes()) + '`.', '',
'Uncommitted report helper retained for the lead: `' + str(Path(__file__).resolve()) + '`, SHA-256 `' + sha(Path(__file__).read_bytes()) + '`. The runner and Part B edit helper are committed in the assigned worktree under scripts/adhoc. Original agy file hashes and equality to the received-draft commit are saved in the audit.', '',
'Work stops for the lead at the Part C schema/version decision. No production launch, publication or implicit owner approval is requested or claimed.'])
body = '\n'.join(lines) + '\n'
assert chr(64) not in body
handoff = REPORT / 'notes/development_efficiency_20261111/handoffs/codex-h2-launch-sequence-20261112.md'
handoff.write_text(body)
assert handoff.stat().st_size
print(json.dumps({'handoff': str(handoff), 'sha256': sha(handoff.read_bytes()),
                  'audit': str(audit), 'audit_sha256': sha(audit.read_bytes()),
                  'cohorts': {row['name']: row['counts'] for row in cohorts}}, indent=2))
