# Byte-exact round-3 reviewer witnesses for round-4 task 9

This bundle copies the witnesses selected by the two review reports and their
saved serial queues. `manifest.json` binds the original full paths, copied
bytes, reports, queue sources, local import closure and generated target lists.
No witness is edited, imported or executed by the copy helper. Original scratch
files remain untouched. This is preparation, not test or acceptance evidence.

Run each `targets/*.json` through the existing pinned review runner with
`--targets-json`, from its final archive, with at most two workers. Keep separate
processes for the two reviewers: they use bare `round2_binding_source` and
`round2_recorder_source` imports. Pytest's normal prepend import mode admits the
sibling copied helpers. Those helpers have historical test functions but are
dependencies only, not extra test targets. The final archive's `tests.*`
fixtures and production modules remain the runtime inputs, not copied old
implementations. Their preparation-time hashes are informational; the runner's
final source snapshot is authoritative. No new test counts are claimed until
collection under that final source.

## Interpret the original outcomes literally

- Codex's two public `build_phase` witnesses and two native registration cases
  should now refuse before reads/authority; the committed round-4 regressions
  independently assert that behavior.
- Claude's nested in-place edit should record `asserted`, the current bundle
  digest and unverified input gaps. Its unchanged nested control can verify the
  bundle against the bound chunk digest, while source/chunk sidecar gaps remain.
  Root-relative rendering stays asserted. The original witness only prints
  these facts and can pass even after a CLI error. The new committed recorder
  regressions provide assertions; a probe pass alone does not prove the flip.
- Cross-corpus records remain caller-asserted; they do not establish consumption
  of the old corpus. Passing observations are not added to acceptance counts.
- The retained locator regex can expect a later authority diagnostic instead
  of the earlier D76 refusal. The old fake-create defect assertion should fail
  after the repaired guard. The original `dataclasses.replace(init=False)`
  expectation is interpreter-sensitive; a separate portable probe is retained.
  Do not change an original witness or count unreachable assertions as passed.
- Registry forgery intentionally rewrites private internals and remains outside
  the invariant's hostile-Python guarantee. Allocator loops that never observe
  reuse are inconclusive on reuse even if their other assertions pass.

## Capture and SG2 limitations

The unchanged runner captures passing stdout without enabling passing-test JUnit
logs. Its phase ledger therefore cannot establish printed wording flips. Use
the committed round-4 assertion tests and retained output records for those
claims; if observations are separately logged, identify that execution rather
than pretending it came from an unlogged passing phase.

`claude/sg2_child_preconditions.py` is a standalone diagnostic, not a pytest test.
It accepts CHECKOUT, NON_GIT_COPY and FRESH_TEMP arguments and creates only its
temporary Git repository. It demonstrates `d76_suite_common.source()` review
attestation preconditions, which intentionally remain strict. Its statement
that ordinary SG2 tests inherit those preconditions is historical after round 4.
Keep it unchanged and report that limit. Do not call its absence of test cases a
successful replay, or invoke a new adapter with an obsolete `--layout` command.
Ordinary dirty-checkout and non-Git SG2 acceptance must instead use the final
generic utility and all three actual SG2 test nodes, with review attestation
explicitly off. The current strict review adapter is a separate opt-in path.

The reports' ordinary D76/SG2, run-lock and native-launch test references point
to committed repository tests. They are not copied into this bundle; task 9's
separate D76/ordering/journal coverage owns those tests. Historical queue scripts
are hashed as selection evidence, never executed by this bundler. Unused
`test_r2_classification_proof.py` is not included: Claude's report-selected
round-3 replacement is `test_r3_classification_proof.py`.
