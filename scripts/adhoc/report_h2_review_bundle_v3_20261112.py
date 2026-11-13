#!/usr/bin/env python3
"""Write the approved helper-2 bundle migration handoff, 2026-11-12.
Inputs: saved source/test audit JSON. Output: named report-worktree handoff.
No source, pin, provider, model, GitHub or native-command changes.
"""
from pathlib import Path
import hashlib
import json

E = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
R = E / 'codex-development-efficiency-20261111'
W = E / 'codex-native-launch-sequence-20261112'
S = E / 'scratch-h2-launch-sequence-20261112'
AUDIT = S / 'review-bundle-v3/audit.json'
def sha(raw): return hashlib.sha256(raw).hexdigest()
data = json.loads(AUDIT.read_bytes())
cohorts = {row['name']: row for row in data['cohorts']}
final = cohorts['v3-migration-final']['counts']
assert not data['status'].strip(), data['status']
assert final.get('failure', 0) == 0 and final.get('error', 0) == 0
lines = [
'# Helper 2: review bundle v3 and owner launch terms v2', '',
'Implemented the approved Part C migration on the assigned launch-sequence branch, in a separate local commit that can be dropped without Parts A/B. All ' + str(final['passed']) + ' final migration tests pass. Current capture, guard and execution entry points require the new pair; historical bundle-v2/terms-v1 records remain evidence-only with unchanged closed shapes. The broader regression run retains three previously reported failures: two capture-test assertions already repaired on the separate observer branch and the protected RunSpec constructor mismatch. No production pins were updated. This is engineering implementation, not owner ratification of amendment items (z) or (ad), and not launch approval.', '',
'## Local handoff', '',
'Worktree: `' + str(W) + '`. Branch: `' + data['branch'] + '`. Parent: `' + data['base'] + '`.', '',
*['- `' + row + '`' for row in data['commits']], '',
'The worktree is clean and `git diff --check` passes. The four protected files match both candidate `5d63d0a77dc43c064cfc2b376355f98009dd5b6e` and integrated main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`. The margin policy and all prompt, manifest, closure and scanner pins remain unchanged. The accepted launch-sequence source is unchanged; its SHA-256 remains `' + data['sequence_script_sha256'] + '`.', '',
'## Protocol and admission', '',
'- `d4d_native_execution_review_bundle_v3`, integer version 3, adds exactly `sequence_script_sha256`. It must be lowercase 64-character SHA-256 and equal `dependencies.base.package_sources["src/data_sheets_schema/native_launch_sequence.py"]`. Current mode rereads those source bytes through the existing source-authority verifier. Full registration and CI reconstruction remain separate required gates.',
'- `d4d_native_owner_launch_terms_v2`, integer version 2, adds exactly `account_quiet`, accepted only when it is JSON boolean true. It is the owner declaration that every session on the registered account stands down before capture through attempt end, including monitoring sessions. It is not authenticated telemetry.',
'- New bundle requires new terms; old bundle requires old terms. Unknown/mixed versions, missing or extra keys and non-boolean current-mode selectors refuse. Historical names and fixture builders remain stable; no missing field is defaulted into saved evidence.',
'- The private execution authorization reader decouples review version from authority version. CI, coded word and execution authority remain version 2. `admit` and live engine authorization explicitly request current validation; saved authorization replay uses historical mode.',
'- Current enforcement covers the native_generation capture/guard/record-word branch, capture_subscription, current-authority and all its activation/lease/guard callers, both direct capture readers when current is requested, subscription preflight/context/load-current, and execution authorization. Historical context and guard replay retain their old dispatch. Guard v2 continues to hash the complete owner statement, so its existing hash now binds account_quiet.',
'- `native_launch_review.validate_packet_script(packet_directory, registration_raw=..., review_bundle_raw=..., launch_word_raw=...)` validates a v3 bundle as retained evidence and independently hashes fixed `sequence-script.py`. It ignores sequence.json assertions. It checks only this script binding, not packet acceptance or execution success.', '',
'New invented fixtures live in `tests/utils/native_review_v3_fixtures.py`. Current capture/readback producers and the synthetic authority helper explicitly select that builder. Their script pin has the full registered source path and complete digest. Minimal parser/component registrations remain explicitly isolated fixtures, not full execution registrations. The original historical bundle builder, parser fixture, guard fixture and retained real-event fixture are byte-identical to the parent commit; the audit records these checks.', '',
'## Saved verification', '',
'Each cohort uses the existing isolated runner, private dependency environment, sibling scratch directory and OS network/native-execution denial. Origin and child-origin witnesses and cleanup results are retained. No real native_generation shell command, model/provider/native binary, private composition, push or GitHub write was used. Tests invoke CLI parsing/gates only with isolated prerequisites and refusal traps; capture tests run scripted local Python peers.', '',
'| Cohort | Passed | Failed | Errors | Skipped |',
'| --- | ---: | ---: | ---: | ---: |']
for name, row in cohorts.items():
    if 'counts' not in row: continue
    counts = row['counts']
    lines.append('| ' + name + ' | ' + ' | '.join(str(counts.get(key, 0)) for key in ('passed', 'failure', 'error', 'skipped')) + ' |')
lines += ['',
'Counts are per saved cohort, not a sum of distinct tests. Each exact command, JUnit, log, origin witness and cleanup outcome is under `' + str(S / 'tests') + '/<cohort>/`; their hashes are in the audit.', '',
'The one-test canary proved new-pair current acceptance and old-pair evidence-only dispatch before the larger runs. Final mutation coverage includes unknown/mixed versions, absent/extra keys, bad/uppercase/wrong/missing registered digests, changed source and packet bytes, quiet false/null/one/string, current API/CLI refusals before effects, independent CI/word versions, and complete historical guard replay before/after owner-term mutation. Incomplete historical evidence still reports unverified.', '',
'Iteration findings are retained: v3-entry used an incomplete guard shape and stopped before the intended bundle gate; the fixture now supplies the exact closed selection shape. The first added guard replay assertion incorrectly expected incomplete evidence to pass; the repaired fixture exercises actual dispatch and a complete event transcript for positive replay, and separately asserts incomplete evidence remains unverified. These were test setup mistakes; no production check was weakened.', '',
'Inherited broad-suite findings:', '',
'- `test_read_capture_for_event_rechecks_authority_after_slot_scan_without_repeating_full_verified`: direct read produces verified/outer-claims, not the test\'s inner-claims label. The accepted observer repair is `37a4aa5d0ab07ed270ef6211f35e7a377e2472b6`.',
'- `test_read_capture_for_event_refuses_mutations_between_outer_authority_and_inner_slot_recheck[review_document]`: pinned review mutation correctly refuses before the recheck marker. The same accepted observer repair corrects this assertion without changing production ordering.',
'- `test_genuine_registration_read_capture_for_event_rechecks_live_selection_and_stage_root`: fixture setup stops at protected RunSpec rejecting native_shared_generation_version. No full-chain registration or native launch is established by these component passes. The lead must compose the separately authorized work and rerun that integration gate.', '',
'No unrelated repairs or pin updates were folded into this migration. Findings are recorded locally because this assignment forbids GitHub writes.', '',
'## Pin and derived-identity impact; nothing restamped', '',
'The following six production source entries change relative to the accepted Part B parent. The complete before/after SHA-256 and byte sizes are in audit.json:', '',
'| Package source | Before SHA-256 | After SHA-256 |',
'| --- | --- | --- |']
for row in data['source_changes']:
    lines.append('| `' + row['path'] + '` | `' + row['before_sha256'] + '` | `' + row['after_sha256'] + '` |')
lines += ['',
'- These entries move `dependencies.base.package_sources` and its containing dependency identity/digest, source commit, verified module/consumer identities and file pin maps that include them. The static full-package-map digest changes from `' + data['static_package_map_sha256']['before'] + '` to `' + data['static_package_map_sha256']['after'] + '`. These are inventory calculations, not newly minted authority.',
'- `_production_sources` includes these nonempty Python modules, so their source hashes/byte lengths and the permission `production_sha256` change. Permission expectations, observation/probe bindings containing those expectations, preparation/composition/execution registration and their embedded raw-byte hashes must be freshly derived. The registration-addition commit proof and its author-date validity binding must be regenerated for a new registration; no historical proof can be restamped.',
'- Review-bundle bytes/hash and owner-statement bytes/hash change; the new sequence_script_sha256 field binds the unchanged accepted script digest. CI evidence must bind the new source/dependency/registration/tested-commit identity, and the coded word must bind the new review/CI/probe bytes. Workflow file digests change only if workflow bytes independently change; this patch does not change them.',
'- The word digest changes capture journal event links, word-specific directory names, capture reservation/claim and capture manifest bindings. Guard registration/runtime/word/owner-statement hashes and its enclosing SHA change as those inputs change. Attempt start/final authority maps, retained metadata, replay references and packet input identities must follow the newly derived bytes. No saved historical attempt is rewritten.',
'- The fixed controller source manifest and its literal CONTROLLER_SOURCES_SHA256 are not changed by these six files alone; they describe their own historical controller closure. No blanket authority-version rotation is needed. Authority/CI/word/guard versions remain 2; capture-request protocol remains 3. The margin constant, schemas, prompts and protected RunSpec-boundary contract remain untouched.', '',
'Ignored- and hidden-file-inclusive searches over the entire assigned worktree (excluding only its Git pointer) are saved for consumers and prior-source/sequence digest references. This is the search scope used for direct-pin conclusions; exact results and exit codes are in audit.json. No matching declaration or historical record was rewritten.', '',
'## Artifacts and limits', '',
'Audit: `' + str(AUDIT) + '`, SHA-256 `' + sha(AUDIT.read_bytes()) + '`.', '',
'All edit/fixture/audit helper scripts are retained and committed under the assigned worktree\'s scripts/adhoc. This report helper is retained uncommitted for the lead at `' + str(Path(__file__).resolve()) + '`, SHA-256 `' + sha(Path(__file__).read_bytes()) + '`.', '',
'Part 1 remains separate: `codex-h2-native-eligibility-audit-20261112.md`, SHA-256 `4b42694ab342dbdcf2d9f0db0faf3bffe5a015bf87968cb669aee19d25b0c3db`. No eligibility snapshot code was implemented.', '',
'Work stops here for lead composition and review. Owner ratification, production pins, full-chain acceptance and any actual launch remain outstanding; this handoff does not request or imply those actions.']
body = '\n'.join(lines) + '\n'
assert chr(64) not in body
path = R / 'notes/development_efficiency_20261111/handoffs/codex-h2-review-bundle-v3-20261112.md'
path.write_text(body)
assert path.stat().st_size
print(json.dumps({'handoff': str(path), 'sha256': sha(path.read_bytes())}, indent=2))

# Fold the final compatibility check and the scanner's pre-scan refusal into
# the same artifact; only the final printed SHA identifies the delivered file.
authority = cohorts['v3-authority-final']['counts']
assert not authority.get('failure', 0) and not authority.get('error', 0)
capture = cohorts['v3-current-capture']['counts']
assert not capture.get('failure', 0) and not capture.get('error', 0)
scanner_log = (S / 'tests/v3-scanner/pytest.log').read_text().strip()
scanner = cohorts['v3-scanner']['outcome']
extra = [
'## Final review and remaining verification limits', '',
'The final authority cohort passes ' + str(authority['passed']) + ' tests, including the entire 45-test migration suite, unchanged approval-only parser refusals, CI checks and addendum authorization tests. It follows the final diagnostic-compatibility fix; the earlier broad cohorts preceded that small fix. The current capture/word/guard/reservation cohort passes ' + str(capture['passed']) + ' tests. No production changes followed these final applicable checks.', '',
'A separate read-only diff review checked default historical mode versus explicit current callers, closed version pairs, script source/packet bindings, quiet boolean identity, and preservation of saved guard hashing. It found one compatibility detail: the initial version decoupling moved the historical approval-only wrong-version error to a later branch. That was corrected by selecting version 3 only for the new review kind; every other old review, CI and word still requires version 2. The unchanged historical parser tests now pass. No additional unresolved migration defect was identified in this pass.', '',
'The specificity scanner exited ' + str(scanner['returncode']) + ' before producing its report: `' + scanner_log + '`. Its log, exact command, origin witnesses and cleanup outcome are saved. The scan did not happen; this is not a passing scan. The inspected scanner branch derives the native route from the protected API runner; that runner, native_shared_render and the scanner are unchanged by this migration. No route, closure or scanner pin was changed to bypass this gate.', '',
'Historical byte-shape compatibility does not waive the existing original-source, retained-runtime, document and registration-commit proof requirements. No historical registration is relabeled as current authority in the new checkout.', '',
]
body = path.read_text().replace('## Pin and derived-identity impact; nothing restamped\n',
    '\n'.join(extra) + '## Pin and derived-identity impact; nothing restamped\n')
assert chr(64) not in body
path.write_text(body)
print(json.dumps({'final_handoff': str(path), 'sha256': sha(path.read_bytes())}, indent=2))
