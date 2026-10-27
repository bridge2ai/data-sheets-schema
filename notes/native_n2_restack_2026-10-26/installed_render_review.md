# Installed D38 full-render delta review

2026-10-27; refs #4354 and #5170. Codex internal review, independent of this
restack's implementation; not a Claude review or scientific sign-off.

**No additional undeclared scientific instruction or execution-policy change
was found in these complete rendered artifacts relative to `01969cbed`.** The
new text changes are the D38 `licence` → `license` spelling and paragraph
reflow, plus explicit fixture labels, dates, checkout/output paths and their
derived identity hashes. This is a bounded render conclusion; the two arms
still have the previously declared scientific and procedural differences.

The previous render used `01969cbed8eed93f420c640c1f1c306e5f58b033`; the installed
render used `f2dca0dd1f16769a10f65df96cb96caa2498a7cd`. Their original evidence
directories remain `/private/tmp/d4d-native-n2-parity-01969cbed/` and
`/private/tmp/d4d-n2-restack-installed-d38-20261026/`, respectively. Report
SHA256 values are `4860510d6dc18f112e09309c1d065059aa295c58f39c91681007d28b04cca921`
and `c18485bc72e1ce659625781ca83f1ffc17213101cd51fd3d313454c91d370771`.

| Complete instruction | Previous bytes / SHA256 | Installed bytes / SHA256 |
| --- | --- | --- |
| API25 | 87,577 / `2e8efbeb608959740cd80ecdcddee35e965928525fe4564046c68bb0d3314083` | 87,584 / `17de6599e503770e2a6e6a9ce4cf719c9db342f162d6f003df2efe53584c37a5` |
| Native26 | 131,271 / `e730d9fb95c7206fbe82b5e2e771290f8fcd38151d0c275b1f0ba2353a9a8520` | 132,263 / `cbc9ed139a885274f1aa4c97aa5830ffcc314a48b2e2f263254cc647b250794f` |

The [comparison helper](../../scripts/adhoc/review_native_n2_installed_render_20261026.py)
pins both reports, verifies every compared artifact against its report, and
rechecks input bytes after comparison. It parses every named native command
without executing it, expands the embedded recorder/registration JSON, and
retains complete text diffs and every changed structural leaf. Its pinned
parser is the retained 2026-10-25 structural-review helper. The [result](installed_render_deltas/structural_deltas.json)
has SHA256 `752cfeafa3826f5df709d4f99ab6f95a2280549ecba9deb910027305f59e7306`;
the new helper has SHA256
`41ec0bb64c380da226432f0454758b27d046c294c30bcfcfbcfa228576ec6e08`.

## Complete same-arm changes

- [API25: all four hunks](installed_render_deltas/current-api25-instruction.txt.diff)
  change the hypothetical run label, displayed generation date, three spellings
  of `licence`, and line wrapping in the last R9 paragraph. No report-contract,
  receipt-policy or other instruction change appears in this comparison.
- [Native26: all seven hunks](installed_render_deltas/current-native26-instruction.txt.diff)
  contain the same R9 edit, hypothetical label/date, the vocabulary/schema
  checkout paths, artifact/stage destinations and the commands/recorder metadata.
  The [prose view](installed_render_deltas/native-prose-only.diff) replaces only
  separately parsed commands and generation-context JSON with explicit markers;
  it is a review aid, not a normalized replacement for the full evidence.
- All 37 changed native command tokens are checkout/output path or label
  substitutions. There are no changed command roles, flags or fixed arguments.
  All 61 recorder-metadata leaf changes are relocated paths, label/date, the two
  D38 asset pins, and consequent descriptor/registration hashes or serialized
  lengths. Native bounds, runtime-declaration contents, pending receipt floor,
  draft-check allowance, source-input contents and schema/vocabulary hashes
  remain unchanged in these fixtures.
- The complete generation context has one changed leaf: vocabulary identity
  **path**, with its bytes/hash and text unchanged. The embedded API receipt
  registration has zero changed leaves. The saved API render spec has 16
  changed leaves: the same asset/path/label/date substitutions and consequent
  registration identity. The saved native spec has the same 61 changes as the
  embedded recorder metadata.

The installed checker reports real capture of 13 assets from the selected
checkout (10 ordinary, 3 module-adjacent), exact refusal for all three stale
asset cases, and unchanged source/input bytes. Current R9 is 4,433 bytes,
SHA256 `d9f7884a03f0480d1ab610118f32850e2d98008fcd67fb51a16a4b7b7ca79a4d`,
occurring exactly once in each arm. Both complete current uniform sections are
25,589 bytes with SHA256
`44a2a05b4e9d410d7628df57cfaeb9dedc532189199e6df85515569e33fec530`.
The [R9 diff](installed_render_deltas/reviewed-r9.txt.diff) and both uniform
diffs show the spelling/reflow change; equal section lengths do not imply
historical byte equality.

## Existing between-arm differences remain

The complete current API/native diff retains the same seven hunk headers as
the previous render. The [prior full classification](../native_n2_parity_delta_review_2026-10-25.md)
and [declared differences](../native_vs_api_generic_v10_declared_differences.md)
still apply: H1/H3/H6/H7 mix scientific presentation and execution procedure;
H2/H4/H5 concern presentation/assembly procedure. Specifically, API's explicit
flat-claims, supported-claim/source-status agreement, `unstated`/`revise` and
qualification guidance remains absent from native's corresponding top-level
report appendix. Native's existing related evidence rules do not make that
model-visible asymmetry disappear. API supplied-text execution, native tool
reads/stages, receipt policies, correction allowances and contextual exposure
also remain distinct.

This review found no *new* such asymmetry introduced by the restack. It does
not establish scientific equivalence, identical model behavior under spelling
or path changes, per-stage request parity, successful native execution, an
empirically chosen coverage floor, or launch acceptance. Both renders are
hypothetical fixtures with a pending floor. No provider, native binary, rendered
command or test was executed by this review; functional/runtime validation is
reported separately at its actual tested source head.

Reproduction (stdlib only; a fresh output directory is required):

```sh
python3 scripts/adhoc/review_native_n2_installed_render_20261026.py \
  --before /private/tmp/d4d-native-n2-parity-01969cbed \
  --after /private/tmp/d4d-n2-restack-installed-d38-20261026 \
  --output notes/native_n2_restack_2026-10-26/installed_render_deltas
```
