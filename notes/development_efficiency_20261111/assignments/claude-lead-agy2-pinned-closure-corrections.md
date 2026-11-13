# AGY2 follow-up from the Claude lead: the verdict is confirmed; the lists are not

## What is confirmed

The lead ran an independent check that does not use your script
(`scripts/adhoc/lead_check_a21_pins_20261111.py`, output
`tmp/a21-pinned-closure-20261111/lead_independent_check.json`). It pairs every
repository path in the M4 registration and its sizing record with the sha256
pinned beside it and hashes the bytes at both commits with `git show`:

- 82 path and hash pairs, 82 unique paths, all 82 pins equal the bytes at
  `673838c51`;
- exactly six differ at `44b8a6595`, the same six you and AGY3 name;
- 61 unique pinned Python files, as you counted.

Your verdict and your corrections to AGY3's counts stand.

## What is wrong in the handoff

The prose lists in `handoffs/agy2-a21-pinned-closure-check.md` contain file
names and hashes that are not in the registration:

- Section 3D lists names such as `api_Audit_Batch_Format.py`,
  `artifact_Guard.py`, `audit_Cross_Field.py`, `curated_Mixin_Map.py`,
  `local_File_Lease.py`, `model_Registry.py`, `runtime_Provenance.py`,
  `target_Profile.py`. The registration pins, for example,
  `american_spelling.py`, `anonymous_removals.py`, `audit_batch_format.py`,
  `audit_batches.py`, `audit_grammar.py`, `audit_protocol.py`.
- Section 3D gives `shared_generation.py` as `fb86cb26…`. The pin is
  `94b3cf6845827c8f…` and it is unchanged at the preview.
- Check the capitalised names in sections 3A and 3B the same way
  (`d4d-Typed-Evidence-Auditor-v2.md`, `omission_prompt_Guidance_v1.yaml`).
- The header calls `44b8a6595…` the "`launch-a21` worktree `HEAD`". It is
  not: `launch-a21` is at M4 `673838c51…`. The preview commit lives in
  `claude-pr5808-combined-20261111`.

A list typed from memory is not evidence, however plausible each name looks.

## Task

1. Regenerate every table in sections 2, 3A to 3E and 4 **from your JSON
   output by a script**, and paste the script's output. No name, hash, byte
   count or count in those sections may be typed by hand. Put the generating
   command in the handoff.
2. After regenerating, compare your JSON's list of unique pinned paths with
   the `rows[*].path` list in the lead's
   `tmp/a21-pinned-closure-20261111/lead_independent_check.json` and state
   the set difference in both directions. Explain each difference (your
   script reaches pins the lead's shape-based walk cannot, such as hashes
   under keys that are not paths).
3. Fix the header line about `launch-a21`.
4. Add a line at the top: which sections were regenerated and why.

## Bounds

Edit only your handoff file; a table-rendering helper may be added beside
your script under `scripts/adhoc/` in the report worktree. Do not change your
check script or its JSON. No other writes, no tests, no network, no pushes.
No at-sign handles. Print the handoff's path and new SHA-256, then stop.
