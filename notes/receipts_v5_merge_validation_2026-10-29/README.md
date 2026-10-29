# Receipts v5 merge fixes: N1, N3, N4

The subsequent R4/R6 follow-up is recorded in [r4_r6/README.md](r4_r6/README.md):
five causal tests pass, the selected acceptance suite has 899 passed / 19
skipped, and all four inertness slices were rebuilt and passed against A13.
The original N1/N3/N4 evidence below is retained unchanged except for the
R2 lifetime qualification and the updated proof reproduction instructions.

Offline remediation of claude's independent review of
`562ca36b29c907bd64f1a2ac63c70baf24d8e2cf`, dated 2026-10-29.
Acceptance source/test head: `955af2bfe` (the subsequent evidence commit changes
no executable production code or tests). The inertness replay started at
`4b87bf52d`; production bytes are identical at the acceptance head.

## Changes and causal evidence

| Finding | Change | Original code → fixed code |
| --- | --- | --- |
| N1 | `block_for` selects only the validated registration/provenance instrument, otherwise historical v3. Neither an artifact marker nor the environment selects v5. A conflicting or malformed marker is a `receipt_format_version_mismatch` finding. Claim sidecars require an explicit caller version for v5 fields. | `test_receipts_v5_merge_n1.py`: 28 failed / 6 controls passed → 34 passed. |
| N3 | `regex_count` retains the 200-character pattern bound, caps source text at 48 Ki characters, and compiles/counts in an isolated stdlib subprocess with a 250 ms timeout. While the parent lives, timeout kills and reaps the worker and refuses verification/coverage. Parent termination can orphan the worker (R2, independent re-review `receipts_v5_fixes_claude_rereview_2026-10-29.md`, §5); this remains an activation blocker. | `test_receipts_v5_merge_n3.py`: 4 failed / 5 controls passed → 9 passed. Includes `.*.*.*.*x` on 320 `a` characters through both verifier and snapshot-aware `check()`. |
| N4 | Pass the selected instrument to `_receipt_paths`; apply the non-string guard only to v5. Historical v3/v4 scalar coverage, D37 counters and completion planning are restored. | `test_receipts_v5_merge_n4.py`: 6 failed / 3 controls passed → 9 passed. |

The exact final causal tests were run against the original archived code:
**38 failed, 14 passed**. Against the fixed code all **52 passed**. The outer
four-second test deadline safely terminates the unfixed pathological regex.
The source changes do not alter N2, N5–N10 or N12–N17. Historical v3/v4 behavior,
including its existing limitations for malformed non-scalar snippets, remains
outside the v5-only guard.

## Acceptance and inertness

The original remediation's 15 modules plus the three new causal modules give
**894 passed, 19 skipped**, no failures, in one offline serial run. The skips
are the existing native-runtime-only cases. This is the selected 18-module
acceptance suite, not the entire repository suite. Original pytest invocations used
`--basetemp="$TMPDIR/codex-v5-pt"` and disabled pytest's cache provider.

`validation.json` and `inertness.json` hold the checked counts and SHA-256
identities. The proof reuses the reviewer's exact corpus and CHORUS slices;
the baseline code is verified against git commit `148c869dd`. As in that
review, checkout absolute paths are normalized to `<TREE>`, and the separate
transcript-derived receipt-origin block is omitted from the receipt probe.
No semantic fields are normalized. The original replay also matched the
reviewer's saved baseline bytes; the R6 replay checks their committed SHA-256
identities after recomputing A13 from git. CHORUS request bytes must match the
saved requests themselves.

All four comparisons passed with v5 off:

| Surface | Result against A13 |
| --- | --- |
| Corpus receipts, explicit v3/v4, D37, claims and uncovered leaves | 54 records: 48 checked, 36 snapshots, six identical snapshot refusals. Normalized bytes identical. |
| `report_claims` v7 and v8 | 335 records at each version, 325 checked; complete output byte-identical, including the ten unchecked records. |
| CHORUS v10, 2026-10-20a and 2026-10-22a | Requests byte-identical to A13 and the saved request files; results, receipt checks, claims and uncovered leaves identical. D37 remains 58/58 and 64/64. |
| generic_v10/A21, renderer 25 / shared generation v1 / playbook 2 / receipt completion 2 | Assembly SHA-256 unchanged: `9e59f3db581c168d397793848579c62a9462e8a2e4236101af05f48803baa90e`. |

Before the full replay, one usable receipt record and one report record were
run through the same launcher in both trees. All four non-empty persisted
artifacts were checked and matched. The first attempted receipt canary was an
expected unusable-snapshot refusal; the successful canary selected a known
checked record from the reviewer's saved baseline. These canaries establish
local imports, git-backed reads and output persistence, not provider behavior.

N11 remains a merge-order note: shared-generation v2 pins the changed source
bytes and its identity changes. The generic_v10/A21 tuple uses shared-generation
v1; its identity is checked separately. No `shared_generation.py` edit was made.

## Reproduction and retained artifacts

Scripts are committed in `scripts/adhoc/`:

- `validate_receipts_v5_merge_20261029.py`: bootstrap local dependencies with
  site startup disabled, strip provider credentials, deny Python network calls,
  and enforce the pytest scratch location.
- `prove_receipts_v5_inertness_20261029.py canary` then `full`: rebuild A13 with
  `git archive 148c869dd` into a fresh directory under `$TMPDIR` on every run;
  recover CHORUS canary inputs from local commit `5457b71b4`; replay serially
  and check the committed baseline hashes. Both phases run one receipt and
  one report canary in each tree before any full replay. New results go to
  `r4_r6/`, preserving the original evidence. No prior temporary tree is needed.
- `receipts_v5_merge_probes_20261029/`: the four adapted reviewer probes.
- `summarize_receipts_v5_merge_20261029.py`: assert causal transitions,
  acceptance counts, four equal comparisons and unchanged protected paths at
  the original remediation head. Use `validate_receipts_v5_r4_r6_20261029.py`
  for the R4/R6 follow-up.

Run each script with the local project virtualenv's Python and `-S -B`.
The committed XML, logs and JSON contain durable evidence; exact raw comparison
JSON remains locally under ignored `raw/`. No bulk evidence archive is added.
`review.md` records the separate adversarial review and resolved test-portability
finding. GitHub issue/PR creation was omitted under the explicit offline/no-gh
instruction. No network, provider call, push, merge, generation-stack change,
or edit to protected files, decision records, run directories, `data/ATTIC/`,
or `STATUS.md` occurred.
