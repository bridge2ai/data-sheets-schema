# Complete named-commit package source proof

[#4704](https://github.com/bridge2ai/data-sheets-schema/issues/4704) addresses a missing completeness check in `native_execution_authority.require_committed`. The previous proof queried only paths discovered in the current package directory. After deletion of an already imported source file, a fresh identity could omit that member while retaining the same Git commit and matching every remaining blob. Source review identified that path. The new fixture-owned test now confirms the already imported module remains cached, its file disappears from fresh discovery, and the corrected proof refuses the missing committed member. The predecessor implementation was not rerun.

The new proof reads the named commit's recursive package tree using local `git ls-tree -r -t -z`, the existing sanitized Git environment, and a finite timeout. Literal NUL-delimited paths are checked before comparing the exact `.py`/`.yaml`/`.json` roster with `package_sources`. Duplicate, malformed and out-of-package paths refuse. Package directory boundaries must be trees; Gitlinks refuse without traversal. In-domain source files must be regular blob modes `100644` or `100755`. Ordinary assets remain outside the domain, and a directory ending in `.py` remains a directory. CR/LF-bearing source names explicitly refuse because the subsequent unchanged object-proof protocol uses line-delimited queries; spaces, tabs and UTF-8 names are preserved.

Missing and extra package members refuse before the existing per-blob SHA256 proof. Equal names with changed bytes still fail that proof. The index is not the committed-roster authority. New commits legitimately removing a source member change the expected roster. Identity construction, source discovery, v1 registration shape, frozen controller bytes and launch limits remain unchanged.

Both Git object commands explicitly disable replacement objects ([#4705](https://github.com/bridge2ai/data-sheets-schema/issues/4705)). Otherwise a local replacement commit could substitute a shorter tree under the original declared commit ID, or a replacement blob could substitute different source bytes. Two additional copied-repository controls retain those replacement refs and verify that the exact original tree/blob still governs the proof.

The focused tests created copied, fixture-owned Git repositories and used the actual authority in bounded ordinary Python children. Controls retained an initial valid proof, then covered deletion of an already imported module, missing resources, untracked/ignored/staged additions, index-only deletion, a committed deletion, changed bytes, executable and symlink modes, opaque Gitlinks, literal filenames and hostile Git overrides. The replacement controls first demonstrated ordinary Git's substitution, then verified the corrected proof refuses the original-tree/blob mismatch. A separate pure parser matrix checked malformed tree records. No shared source file was deleted or hardlinked into these fixtures.

The serialized run at commit `a92b71159ed315bfd1391f1de5f87ffa5f2d648d`, tree `6f7172913b2c5a35d32084ace867794acb811e7d`, passed **40 tests**: 38 dedicated source-proof controls and the two existing `correction` / `no_correction` closed-consumer cases. There were no failures, errors or skips. JUnit records 305.935 seconds; the terminal reports 306.03 seconds and no warnings. The coordinator wrapper's elapsed time is recorded separately in [validation.json](validation.json).

The test selection was:

```text
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=src:.:notes/matched_cborg_2026-09-13:notes/matched_cborg_2026-09-13/native_controls \
$VALIDATION_PYTHON -B -m pytest tests/test_native_source_roster.py \
  tests/test_native_execution.py::test_actual_closed_consumer_real_helpers_complete \
  -q -p no:cacheprovider --basetemp=$EVIDENCE_DIR/native-source-roster-pytest-01 \
  --junitxml=$EVIDENCE_DIR/native-source-roster-tests-01.xml
```

Before/after checkout inventories were byte-identical: 9,364 regular files totaling 450,453,050 bytes. The walk included hidden and ignored files and excluded only the top-level `.git`; it recorded file modes and would retain symlink targets/modes, but did not inventory directory modes. Every current inventory entry was independently rehashed and compared before these note edits. The unchanged frozen-controller manifest and its 12 dependency files also match the base and tested Git blobs. The validation record pins 31 selected source/test/declaration/dependency files and eight external evidence artifacts. These selected pins are not an exhaustive imported-runtime attestation.

The existing closed consumers use fabricated permission, review, CI, owner and authentication observations, ordinary Python peers and genuine local generation helpers. No real native executable, provider campaign or 900-second acceptance run occurred. Complete committed file evidence is not authentication of cached Python bytecode, execution permission, scientific approval or successful native acceptance. The private owner-profile integration and existing native acceptance failures remain separate.
