# Held-out audit ground truth (#2921)

This directory holds independent review observations of frozen originals. Each
one records a defect a reviewer found in one exact `original_full`. They are
used only to measure what a Phase 3 source audit of that original missed:

```bash
d4d evaluate audit-recall --ground-truth data/audit_ground_truth/<FILE>.yaml \
    --audit <run>/evidence/audit.json --original <run>/original_full.yaml \
    [--audit … --original … ] [--replicate rep1 …] [--arm direct] [--output report.json] [--json]
```

The command is offline. It makes no model call and runs no source check. The
code is `src/data_sheets_schema/audit_recall.py`.

**This directory has no entries yet.** The format, loader and report are
tested only on synthetic, neutral fixtures (`tests/test_audit_recall.py`).
Seeding real entries is a separate curator change. The candidate sources are
the v10z seven observations, the v10x/v10y independent reviews and a fresh
held-out review of the direct v1–v3 originals. That change also has to settle
where the private originals the entries pin are kept.

## Held out means held out

The observations are *held out of the audit model's instruction*
(`notes/native_audit_continuation_plan_2026-09-18.md`). The audit duties
already forbid held-out diagnoses and reviewer files
(`audit_batch_context.COMMON_DUTIES`). Nothing that can reach a generation or
audit model may name this directory or quote an observation. That covers
condition prompts, playbooks, agent definitions, rendered audit contexts,
output contracts, a registration's inputs and a launch message. Do not add
these files to any registered input list.

The native file policy checks instruction conformance. It is not an OS
filesystem sandbox, so absence from the instructions is the guard.
`tests/test_audit_recall_leak.py` scans the instruction surfaces and the
registered native inputs for this directory's name and for every observation
committed here. It fails on a match, and it fails when a committed file here
does not load. A report from the command carries entry ids, kinds and
pointers. It never carries observation text or any of the audit's prose.

## File format (`audit_ground_truth_v1`)

The JSON Schema is `ground_truth.schema.json`, rendered from
`audit_recall.ground_truth_schema()`, and a test holds the two equal. Files
are YAML or JSON. Duplicate and merge keys are refused, and dates are read as
written.

```yaml
format: audit_ground_truth_v1
project: EXAMPLE                     # one project per file
description: optional prose about the reviewed set
entries:
  - id: example-001                  # unique in the file
    target_original_full_sha256: <64 hex>   # the exact original_full bytes observed
    paths: [/maintainers/0/name]      # JSON Pointers into that original, one or more
    kind: role_placement              # closed list below
    governing_source:
      bundle_sha256: <64 hex>         # the bundle the lines are numbered in
      source: example_row1.txt        # the bundle's FILE: name, and/or
      chunk: c004                     # the chunk manifest id
      lines: [120, 128]               # first and last line, 1-based, inclusive
    observation: A short statement of the defect.
    reviewer_role: independent reviewer
    reviewed_on: 2026-09-18
    provenance_note: notes/<note recording the review>.md
    held_out: true
```

An entry that lacks a field, or carries one that is not declared, is refused
with every problem named. The same applies to `held_out` other than `true`, a
pointer with a bad `~` escape, a date that is not on the calendar, lines out
of order, an absolute or `..` note path, and a duplicated id. Entries pin
originals by hash and never edit them.

The pinned sha256 values make the numbers reproducible. An entry scores only
against the exact original it names. `bundle_sha256` fixes the line numbers,
because bundles drift (#452).

**`kind` is provisional** (#2921 owner decision 2). It takes the issue's seven
values plus `other` and `omission` (#2930):

`role_placement`, `status_scope`, `date_scope`, `absence_or_self_narration`,
`quotation_fidelity`, `identifier_count`, `attribution`, `omission`, `other`.

It must equal the audit grammar's finding `kind` enum once that lands. The
grammar change edits `audit_grammar.py`, `audit_batches.py` and
`audit_batch_format.py`, which audit28's finalization compares by hash. It
waits until audit28 closes and comes with a new protocol version.

## What the report counts

The audit must pass `audit_grammar.check`, which is run read-only. Its
`source_review.sha256` must equal the sha256 of the `--original` bytes.
Either failure is refused, not scored.

Only entries whose `target_original_full_sha256` is that sha256 apply. An
original that no entry names has **0 applicable entries and recall n/a, not
0**.

**Hit rule `pointer_cover_v1`. It is provisional and requires owner sign-off
before any report on real audits is quoted** (#2921 owner decision 4). A
ground-truth path is *hit* when the audit names that pointer, or an ancestor
of it on JSON Pointer segments, in one of three ways:

- a `source_review` row carrying a `revise` claim;
- a finding `review_paths` entry;
- a finding `remove_relationship.path`.

A flag strictly below the path is reported as `flagged_below` and is not a
hit. Supported rows, metadata rows and findings that name no pointer are never
hits. The last case is how an omission finding with only `slot` text is
counted today, and the owner may choose otherwise.

A miss is classified in this order:

1. `judged_supported`: a supported row at, above or (with no flag below) below
   the path.
2. `flagged_below`.
3. `metadata_only`.
4. `not_reviewed`.

`misses_judged_supported` lists the first class. Each path also says whether
it `resolves_in_original` to a populated value or a container of one. An
omission's path may not resolve.

Recall is reported per kind and in total over paths, with the denominators
beside it. A zero denominator reads `n/a`. Entry-level counts
(`all_paths_hit`, `some_paths_hit`, `no_path_hit`) are shown beside the
path-level numbers, because an entry located at two paths and flagged at one
leaves the other unfixed. Replicates are reported side by side and never
pooled.

`review_candidates` lists audit flags that no hit used. **They are candidates
for review, not false positives.** The reviewed set is small and says nothing
about what it did not review. `inside_entries` names any entry whose path
contains the flag.

The report pins its own sha256 and the hit rule, the grammar instrument and
its sha256, and the ground-truth file's sha256. It also pins, for each
replicate, the audit's and the original's sha256 and the arm and replicate
labels as given. It states that the result covers one project and a small
reviewed set, not general audit quality.
