# Selected N2 result archive helper

Refs #4354. The helper and its synthetic tests were committed as
`a8fc242b29f533ac0323d568d93da89746840245` on the inactive
`codex/n2-public-driver-20261027` branch. No production code, final-restack
worktree, active native/legacy result directory or existing run artifact was
modified. Only synthetic completed evidence was used for validation.

[`archive_n2_restack_validation_20261027.py`](../scripts/adhoc/archive_n2_restack_validation_20261027.py)
accepts repeated explicit `--evidence` directories and one fresh absolute
`--output` directory. It selects JSON, log and XML files at each root and in
its `neutral/` and `omission/` stage directories, including ignored files.
Each run receives a separate compressed archive and exact byte/mode inventory.
The helper verifies the archive roundtrip and rereads all selected originals.
Symlink boundaries, nonregular selected files, reused destinations, overlap with
inputs and concurrent selected-file changes refuse. A failed preservation attempt
keeps its partial archive and does not write a success manifest.

**This is not a complete synthetic-case archive.** `cases/`, caches and other
directories remain external; their contents are not traversed or attested.
The manifest lists exclusions. File bytes/modes are preserved; archive timestamps
are normalized and directory metadata is omitted. Inputs must be completed and
quiescent before invocation; the helper does not stop or inspect running jobs.

Original outcome/summary bytes are preserved verbatim. Classification records
reported exit/status without recomputing or endorsing historical pass totals.
JUnit entries are reported only by identity/error/skip/unmarked shape, with no
aggregate pass claim. Missing, unreadable, bootstrap-only or interrupted results
remain unverified; an unmarked or anonymous XML entry is never promoted to a pass.

Independent internal static review found no blocker. The focused synthetic suite
passed **8 tests**, zero failures/errors/skips, **0.07 s**, at the committed head.
It covers exact binary log/mode preservation, stage selection, interrupted XML
with an anonymous entry, the synthetic historical `passed:611` reporting error,
excluded case/cache directories, symlink/nested/existing-output refusal,
concurrent mutation and incomplete XML. The initial and final tracked source
remained clean before evidence copies were added.

A separate CLI invocation used `python -S -P -B` on the completed synthetic
fixture created by the passing test. It archived four selected files, retained
the original nonzero exit summary exactly, recorded the anonymous XML entry,
and verified all selected bytes/modes and rereads. The archive is **309 bytes**;
its [manifest](native_n2_archive_20261027/manifest.json) and
[archive](native_n2_archive_20261027/run-01.tar.gz) are retained unchanged.
This selfcheck does not establish anything about actual N2 test outcomes.

| Evidence | SHA256 |
| --- | --- |
| [Test log](native_n2_archive_20261027/d4d-n2-archive-tests-20261027.log) | `bb631ccc7cf28af0b01a3ded9258ef87308ed2a2ea9efbea9528c23ed57c218a` |
| [JUnit](native_n2_archive_20261027/d4d-n2-archive-tests-20261027.xml) | `c7572caa213df93557f94c8f4c42a311707b08b22d53004dc1eae9564cb62748` |
| [CLI log](native_n2_archive_20261027/d4d-n2-archive-cli-selfcheck-20261027.log) | `b7f98489d6f8945758c33fb7e4f815aae79ffdd2cfa09d17c18208011395881e` |
| [CLI manifest](native_n2_archive_20261027/manifest.json) | `9fb25ebaf4621dbfde0051ddd768e0e72ce8232022951c7a473561475ad0c57a` |
| [CLI archive](native_n2_archive_20261027/run-01.tar.gz) | `5efa9a9c54dcd913fd148b6c3c666d2a650dfb5b11827f3d3565a44a3e4b216b` |

The helper SHA256 is
`58ed839ba30d30f1089741c0e233fba01477bade741ea6a0a3b8a6a59284f187`;
the test SHA256 is
`67ce7418953bba73d66b6d8e0e809dbc49a7d48240b0e8e291d4ee8948580e73`.

The focused test used the primary checkout's absolute `.venv/bin/python`,
`PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, and this inactive
worktree's `src` and root on `PYTHONPATH`, with provider-key variables unset:

```text
python -m pytest -q -p no:cacheprovider
  --basetemp=/private/tmp/d4d-n2-archive-tests-20261027
  --junitxml=/private/tmp/d4d-n2-archive-tests-20261027.xml
  tests/test_archive_n2_restack_validation_20261027.py
```

The CLI selfcheck, using the same absolute interpreter, was:

```sh
python -S -P -B scripts/adhoc/archive_n2_restack_validation_20261027.py \
  --evidence /private/tmp/d4d-n2-archive-tests-20261027/test_archive_preserves_interru0/source \
  --output /private/tmp/d4d-n2-archive-cli-selfcheck-20261027
```

For a new invocation, provide only completed result directories and a fresh
destination. The original synthetic inputs and all selfcheck outputs remain
under `/private/tmp`; the evidence commit adds copies and this note only.
