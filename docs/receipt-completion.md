# Offline receipt completion

This is the deterministic prerequisite for [#3314](https://github.com/bridge2ai/data-sheets-schema/issues/3314)
and [#3315](https://github.com/bridge2ai/data-sheets-schema/issues/3315), under
[#2926](https://github.com/bridge2ai/data-sheets-schema/issues/2926). It prepares
requests and checks saved answers. It makes no model calls and changes no input
files. It does not establish semantic support or empirical improvement.

## Instrument boundary

`receipts.check(..., instrument_version=4)` retains v3 coverage, aggregate
diagnostics and gates. It adds `snippets.by_origin` for `phase1`, `rereceipt`, and
`unknown`, each with integer `total`, `no_value_overlap`, `entry_single_leaf`,
and `unattesting` counts. Only an absent marker uses the historical phase-1
convention; malformed or unknown explicit markers remain visible. These markers
are accounting metadata, not independent evidence of authorship or support.
The default checker and historical disk checks continue to use v3. Disk checks
for an explicitly registered [receipt-completion runtime condition](receipt-completion-runtime.md)
select v4 and its registered coverage policy. Historical blocks are not silently
rewritten or relabeled.

`apply_rereceipt(..., instrument_version=4)` adds `origin: rereceipt` only to a
new pair accepted by the existing snippet/path validator. An identical existing
pair is never relabeled; retrying the same additions does not duplicate pairs.
Missing or duplicate chunk entries and `duplicate_of` chunks still reject the
answer. A verified addition to `nothing_relevant` or `redundant_with` changes it
to `extracted`, retaining the previous status and its reason/references in
`rereceipt_prior`. The v4 checker counts these recorded reversals separately;
malformed prior metadata is reported separately. A reversal never adds a new
reviewed chunk. These counters and anti-padding screens are nonterminal.
The v4 merger rejects a negative-status chunk already carrying an `extracted`
or `rereceipt_prior` key, including empty or malformed values. Correcting that
contradictory entry would overwrite its evidence; rejection preserves the
entry exactly and leaves the requested path uncovered. Other valid answers
in the response can still be merged. Historical v3 merge behavior is unchanged.

Renderer 24 is an **API-only, offline preparation boundary**, not an executable
or registered generation condition. Its assembly digest binds the new receipt
instruction, header, policy and v4 instrument. Renderers 1–23 retain their exact
previous assembly digests. `build_rereceipt` accepts only the last `full` or
`full_readdress` request plus its entire assistant response; it retains the
conversation and cached prefix and appends every uncovered leaf. It refuses
audit/report/reconcile requests. `execute` and `_execute` refuse renderer 24
before provider access.

## Preparing and checking an offline inventory

Use a phase-1 full snapshot after any re-addressing, its corresponding receipt,
the exact bundle/chunk manifest, and the selected merged full schema. Do not
substitute a reconciled final record or a current bundle for recorded bytes.
For historical inspection, recover/materialize recorded inputs into a separate
temporary directory using the existing provenance/snapshot recovery facilities;
retain their commit/hash basis. Never rewrite originals to make hashes match.

`rereceipt.Inputs` holds immutable copies of all five inputs. It refuses duplicate
YAML keys, a receipt/bundle MD5 disagreement and a manifest that cannot reproduce
the canonical chunks under its recorded rule. SHA-256 identities cover every
raw input, the request contract and the explicit output-token cap. It pins the
supplied schema; **record validation against that schema remains a separate
required check**. Receipt coverage continues to use the existing populated-leaf
and exemption logic, rather than a new denominator.

From the repository, using independently materialized paths:

```bash
python -m data_sheets_schema.rereceipt \
  --record /tmp/receipt-inputs/full-phase1.yaml \
  --receipt /tmp/receipt-inputs/coverage_receipt.yaml \
  --manifest /tmp/receipt-inputs/chunks.yaml \
  --bundle /tmp/receipt-inputs/bundle.txt \
  --schema /tmp/receipt-inputs/full-schema.yaml \
  --max-output-tokens 12000 > /tmp/receipt-inventory.yaml
```

The illustrative cap is not a registered or measured recommendation. The
operator must provide it explicitly. No path list is truncated to fit it.

For a saved YAML answer of the form `rereceipt: [...]`, repeat the same command
with `--answers /tmp/answers.yaml --inventory /tmp/receipt-inventory.yaml` and
redirect to a **different** temporary report. The saved inventory is required
when checking answers; any changed input, cap or contract is refused. The CLI
prints YAML to stdout and writes no input or provenance files. The Python API
can instead retain the same immutable `Inputs` object; when reloading bytes,
pass the saved `input_identity` as `complete(..., expected_identity=...)`.

Every requested path receives one receipt action or one typed unsupported
action with a reason. Duplicate answers are rejected together. The report
distinguishes rejected **answers** from rejected **paths**, unanswered paths,
accepted actions, additions, status reversals, and never-receipted leaves before
and after. Extra or malformed answers prevent `answers_complete`. That state
means only that every path received one accepted action; all-unsupported can be
answers-complete with no coverage improvement. Unsupported claims remain in
the record and in `still_uncovered_paths`, with separate
`unsupported_audit_candidates`. A verified quotation can still fail semantic
support; neither the state nor zero deterministic defects certifies it.

## Runtime integration and remaining work

The [registered receipt-completion runtime](receipt-completion-runtime.md)
implements the continuation, durable phase usage and failure accounting,
audit carry, and shared strict CLI/canary coverage gate under an explicit
`receipt_completion_version=1` API renderer-8 condition. It preserves the
successful full output when the follow-up fails. This runtime is separate
from renderer 24's offline-only boundary described above; historical/default
requests and gates remain unchanged.

[#2926](https://github.com/bridge2ai/data-sheets-schema/issues/2926) remains open
for owner-selected registration inputs and empirical acceptance: explicit
output/request caps, context capacity and its basis, model, route and spending
budget; separately authorized CHORUS and AI_READI canaries; and a coverage floor
calibrated from their post-turn results. Those pilots must report before/after
never-receipted counts, new-receipt attestation diagnostics, audit findings and
added cost. A pending diagnostic floor never passes the strict coverage gate
or authorizes fanout. No values or run authorization are supplied by this
offline guide.

The [restore-only removal-repair runtime](removal-repair-v1.md) implements the
record-side restoration alternative for
[#2923](https://github.com/bridge2ai/data-sheets-schema/issues/2923), selected by
`removal_repair_version=1` on API renderer 8. It reuses the removal classifier,
requires restoration of unfounded removals, and cannot be satisfied by report
dispositions alone. It does not add evidence-backed audit amendments or certify
the source truth of restored values. Independent source curation, native/direct
or later-renderer extensions, and empirical acceptance of a fresh condition
remain separate work. The original #2923 software and replay criteria are
[complete](https://github.com/bridge2ai/data-sheets-schema/issues/2923#issuecomment-5965432187).

Existing v1/v2/v3 instruments, historical registrations and the held audit28
corpus remain unchanged. Neither receipt completion nor removal repair reopens
a generation stopped by terminal source/evidence failure. Offline fixtures and
replay do not establish empirical calibration or authorize paid execution.
