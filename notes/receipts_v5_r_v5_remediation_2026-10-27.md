# Receipts v5 R_V5 remediation — Wave 3

Completed offline on 2026-10-28 UTC (2026-10-27 PDT). Base:
`662b5c4c8dfe75c4c698f0d4a3ab261cdc42ddb2`; branch
`codex/receipts-v5-r-v5-fix-20261027`. Final tested production/test head:
**`851e7cc84562319e1de60cee6a4099b6106c43a7`**. Subsequent delivery commits
archive this evidence/report and remove one trailing blank line in a review test.
No executable code or assertions changed after validation; final base-to-head
`git diff --check` passes. Nothing was pushed or activated.

## Findings addressed

| Finding | Result |
| --- | --- |
| F1 | Unit conversions require the signed source quantity/unit in the referenced chunk or verbatim snippet. Hash targets honor tool/args target and refuse conflicting targets. Counts/hashes use exact result and scalar equality, with no substring or tolerance credit. Nonfinite, boolean, malformed and overflowing numeric inputs are refused. |
| F2 | Only SUPPORT/PARTIAL grant affirmative v5 coverage. NEUTRAL stays in polarity diagnostics; unknown/malformed polarity never defaults to SUPPORT for credit. |
| F3 | Tool diagnostics and D37 use the original snapshot, including completed rereceipts. Final coverage recomputes independently and follows member identities for both destination and record-tool input paths. Stale tools produce a final-record mismatch finding without changing snapshot coverage. |
| F4 | `block_for` opts into v5 for typed document marker 5 or environment value `RECEIPTS_V5_INSTRUMENT=1`. Without opt-in, old v3/default and registered v4 behavior remain. Explicit v5 completion planning uses the same polarity/tool attestation rules. Exact-v5 verified tools satisfy the canary nonvacuity check. A synthetic disk/bundle/manifest-to-canary test covers this route. |
| F5 | All watermark-enabled report checks identify instrument v9, including callers otherwise requesting v7. |
| F6 | The fast diagnostic no longer accepts one shared number as a whole contradictory count/date/unit claim. Conservative single-quantity checks and bounded number-word grammar support million compounds and zero, refusing ambiguous phrases. This is still a diagnostic, not semantic proof. |
| F7 | Malformed/unclosed/empty explicit watermark markers produce findings. JSON Pointer empty keys are preserved; fenced examples are excluded with offsets retained. |
| F8 | Historical v3/v4 inverted claims retain `{chunk, snippet}` entries. V5 optional fields appear only with explicit v5 selection; explicitly pinned v4 ignores ambient v5 opt-in. |
| F9 | Transformation verification recomputes exact integer counter maps. The bounded declarative executor validates supported expressions, operations, classes, slots and schema identities rather than ignoring changed semantics. Tool origin keys bind snippet plus full tool payload in a typed key; default snippet keys/digests stay unchanged. Tool-origin reports identify v7; legacy reports remain v6. |

Additional integration fixes preserve snippets when verifying snippet-target rereceipts,
distinguish neutral from affirmative duplicate receipts, and prevent identity remapping
from repairing malformed tool arguments. No changes to protected generation code,
prompts, canonical hashes, existing run directories or data/ATTIC were required.

## Frozen verification

Final single run at `851e7cc84562319e1de60cee6a4099b6106c43a7`:
**842 passed, 19 skipped, zero failures**, 61.18s pytest / 65.27s driver.
The 19 skips are existing API parameter combinations whose terminal/deadline and
native-controller behavior applies only to the native runtime; none of the five
required modules or new regressions skipped. This is functional evidence, not an
idle-host performance benchmark.

| Module | Passed |
| --- | ---: |
| test_review_receipts_v5_20261026 | 32 |
| test_receipts_v5_upgrade | 11 |
| test_receipts | 50 |
| test_report_claims | 113 |
| test_derive_core | 7 |
| test_wave3_receipt_integration | 14 |
| test_wave3_receipts_core | 42 |
| test_wave3_watermark_transform | 45 |
| test_receipt_origin | 230 |
| test_receipt_origin_captured | 24 |
| test_receipt_rereceipt | 58 |
| test_receipt_completion_policy | 67 |
| test_rereceipt_completion | 69 |
| test_canary_gate | 35 |
| test_canary_controller_receipts | 45 |

The 32 original review cases are copied unchanged: all 22 formerly failing cases
and ten positive tool controls pass. Their SHA-256 is
`c4da648d3b756e8f37ba0d44cd0503d3a52af55230d01a00b368c1e523f8478e`.
The corpus tests compare legacy v3/v4 counters and floors read-only; existing
records/provenance remain unchanged.

`scripts/adhoc/validate_wave3_20261027.py` and its committed common helper record
exact tracked source/modes before/after, loaded project/test origins, selected
modules, command, clean head, protected-path diff, logs and identified JUnit cases.
The physical Python 3.13 venv is started with `-S -P -B`, no .pth execution or
pytest plugin autoload; credentials are removed. Python audit hooks refuse network
and live CLI commands. These hooks are not an OS sandbox for arbitrary subprocesses;
selected tests use synthetic deliveries. Third-party package bytes are not attested.
Final source and import checks passed.

Raw final results: `/private/tmp/d4d-wave3-rv5-final-all-20261027`.
Final outcome SHA-256:
`6db401c098635f30afd5e424e49f5751d74b82a87822264ab22cbbabe899e302`.
Durable archive: `notes/receipts_v5_r_v5_validation_2026-10-27/`; manifest SHA-256:
`bda23272f570816304459da13b3eb459eb5f41dd0f839d9cc71ddee2961d4a7b`.
The archive helper verifies selected JSON/log/XML byte/mode round trips; synthetic
case directories remain external.

Earlier evidence is retained: 302 passes at d64a761a3; 313 focused passes at
30a25af97; and its compatibility run with 509 passes, 19 failures, 19 skips.
Eighteen failures exposed the changed default-version keyword breaking legacy
wrappers; the final fix preserves the old invocation. The remaining test still
called version 5 unsupported even though the target base already implements it;
its negative control now uses unsupported version 6. None of these failed runs
is presented as a pass. An independent read-only reviewer found no remaining
blocking finding in F1–F9 at final tested head after reviewing the last correction.

## Activation and interpretation boundaries

Native D38 at `be0bd05821256212e89e4d011ba6b30a780e299b` still explicitly calls
check/apply with version 4 and records version 4. Its default uncovered helper
remains unaffected by v5 environment opt-in. No native restack or live launch was
performed here. API/native registered receipt-completion protocols remain v4;
the checker/sidecar opt-in is not proof of a fully registered v5 generation arm.

V5 remains shadow/explicit opt-in, not a campaign acceptance migration. Receipt
coverage and fast entailment do not establish scientific support. The existing
rule excluding paths absent from the original snapshot is retained. Transformation
verification covers the implemented derivations, digests and counters; it is not
a general LinkML-Map interpreter or verification of every descriptive metadata
field. Installed-wheel mapping resources/dependency policy, hard runtime bounds
for model-supplied regexes, and the design's evidence-source example/vocabulary
alignment remain separate pre-activation follow-ups from the original review.

No provider, live binary, network, GitHub write, push or merge occurred.
