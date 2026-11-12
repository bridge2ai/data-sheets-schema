# Lead review: agy4 native latency implementation plan

Reviewed 2026-11-10 UTC, read-only against plan SHA-256
`7cddbdab212fc70dbccec74fa6d73b94ebf9065beb69ac241cbb87299e131b22`.
Plan: `notes/reviews/native_latency_implementation_plan_2026-11-10.md`.

**Verdict: changes required; not authorized for implementation.** The useful
direction is a smaller prerequisite-driven development loop. The proposed
implementation is not reliable: its evidence tables contain incorrect values,
its alleged observer hot spot is absent, and its cache design omits existing
identity guarantees. No implementation or test campaign was performed in review.
Two independent read-only checks corroborated the evidence and design findings.

## Findings to record as GitHub issues

### NL-1 — P1: Rebuild the evidence ledger from actual artifacts

Plan lines 9, 18, 52–60 and tables 3A/3B report incorrect full commit IDs,
artifact hashes, baseline timings and source locations. For example:

- Actual baseline commit is `a2241d4c67b17149e3baf2eeb41be4ebf3d9bde7`, not
  `a2241d4c6fa413e11cf07db59b999c5f2f95fc4b`.
- Actual initial cache commit is `03426fd33821508e79b0c84b4180f293ef4fa397`.
- `baseline-profile-summary.json` SHA-256 is
  `14bd79d6a8f7c7d6ad03cbc047ec6ab5e6b063abc48354c30ae227e58422b486`, not
  the cited `b2390517...`.
- `public-pair-grouped-summary.json` SHA-256 is
  `d72b3faface41226cc1cb5ee6cb5f5982b1f11e9986bcf2a8ccc26bc81cf6f8d`, not
  `fe4a51f0...`.
- The baseline report records control/profile supervisor wall times
  **359.662584 / 1060.041808 seconds**, not the plan's 705.23 / 683.48.
- `make_case` is in `tests/test_native_shared_execution.py`, not
  `tests/native_shared_fixture.py`.
- The first claim-audit row attributes a U3-A–J2/PR-duration assertion to the
  input document that the input does not contain.

Sources: retained `d4d-executions/scratch-native-u1u3/u3k/` artifacts and
`plans/reviews/native_u3k_2026-11-09.md` baseline measurement table. The baseline
diagnostic omits the legacy public observer and stops at a different boundary;
it cannot establish the plan's claimed treatment effect against public tests.
Required revision: a compact, reproducibly checked ledger with source path,
full hash, exact field, units, observation mode and failure boundary. Remove
claims that cannot be recovered. Do not invent replacement measurements.

### NL-2 — P2: Correct scanner regression attribution before planning repairs

Lines 21–23, 170 and P0 attribute all 13 U4b failures to K's cache commit and
propose removing duplicate D114 text as the remedy. The authoritative K report
explicitly states that **12 scanner failures match the retained U3-J2 class**:
ten unsupported-producer failures and two historical insertion selectors. Only
the thirteenth is the new pre-engine refusal-order failure. Text-count repair
alone does not establish scanner derivation correctness.

Required revision: separate inherited failures from the new ordering change,
and leave scanner/D128 repair with U3-L. Preserve semantics and approved finite
differences; no promise that deduplicating a literal fixes all 12 failures.

### NL-3 — P1: The proposed observer optimization targets nonexistent code

Lines 171 and 273–284 claim `observe_consumer_calls` calls `os.path.realpath`
for every Python call, then predict 15–30% savings by adding a name filter.
The inspected `tests/utils/native_shared_consumer_scope.py:35–49` **already**
filters event and function name before examining the filename, and uses only
`rsplit`/`removesuffix`. It does not call `realpath` there. This is a false
mechanism, not a demonstrated optimization opportunity.

Required revision: put a matched observer-cost diagnostic first. Preserve
forbidden-call and injected-refusal coverage, including source-loaded code
objects. Define how equivalent assertions remain checked in both diagnostic
arms; a faster run with an observer simply removed is not acceptance evidence.

### NL-4 — P1: Cache proposal targets nonexistent interfaces and omits guarantees

P1 references `native_shared_authority.py`, `cached_schema_derivation`,
`source_state_token()` and a ContextVar cache that do not match the inspected
implementation. Ignore-independent searches of the current source locate the
actual `launch_derivations` in `native_execution_authority_v2.py:469`.
Its scope is reentrant/main-thread, retains only schema metadata, and explicitly
grants no verification authority. The domain binds full package-source pins,
executing source identity, physical root, interpreter and dependency state.
The actual selection cache also binds the ordered imported schema closure.

The proposed two-root-digest cache key (line 227) is not a proof that imported
schema declarations/bytes, root-relative interpretation and dependency identity
remain equivalent. Lines 237–248 propose reusing returned `.verified()` results
after an unspecified file fingerprint, without a complete read-set, live
in-memory dependency, clock/state or consumer-contract proof. Deep copying a
previously accepted result does not supply those proofs.

Required revision: remove this as an approved architecture. Map actual data
dependencies and existing guards first. Propose at most a bounded experiment
on immutable derivations with unchanged refusal behavior. Admission verdicts,
freshness and journal/one-use decisions remain live. Any larger snapshot design
requires a separate reviewed contract, not an implicit implementation step.

### NL-5 — P2: Fixture copying needs a path/identity proof

Lines 267–270 propose copying a module-scoped authority template into each new
test directory. The real fixture binds paths, registration/composition hashes,
attempt/evidence identities and authority. A copied directory is not necessarily
a valid new fixture: embedded references can still point to the template.

Required revision: inventory those bindings and retain a fresh cold-path test.
Only identify path-independent immutable inputs as reuse candidates until an
equivalence/relocation proof exists. Do not promise drop-in `copytree` reuse.

### NL-6 — P2: Validation commands must name actual tests and artifacts

Lines 320/331 name nonexistent public test nodes. The actual tests are:

- `tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion`
- `tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses`

Other claimed test counts, switches and output fields also need verification
against the actual harness; a proposed feature must be labeled proposed, not
presented as an executable command. Use ignore-independent source searches and
saved rosters for this planning correction; no new full collection/test campaign
is required. Preserve mandatory final coverage and current once-only limits.

### NL-7 — P2: Replace unsupported speedups and global CI scaling with hypotheses

Tables 1.2 and section 8 promise 22–55-second passing public tests, all-green
cohorts and hours to live canary without a supporting experiment. The legacy
observer overhead is unresolved, inclusive timings overlap, and current public
cases fail before executing the remaining completion/readback work. Their
pre-reservation cost cannot predict total successful runtime. The 2.729 CI ratio
is not established as transferable to these native tests, observer settings,
Linux workers or xdist scheduling. Do not apply it as measured per-file weight.

Required revision: distinguish measurements, hypotheses and proposed diagnostic
budgets. Remove invented passing counts and throughput/ETA guarantees. Use
existing timing machinery and real representative CI observations when available;
keep missing observations explicit. Do not include evaluation in an implicitly
authorized native generation attempt.

### NL-8 — P2: Dependency contamination cause is unproven

Lines 58 and 172 attribute bytecode contamination to scrubbed child environments
and Python 3.12. The retained audit records CPython **3.13** bytecode and explicitly
says the timestamps do not establish its creator. The pinned original files were
unchanged; terminal integrity witnesses were incomplete for that lifecycle run.
The subsequent isolation canary does not prove who wrote the earlier extras.
Required revision: retain the verified facts, keep cause unknown, and require a
process/file-creation witness before prescribing a causal environment fix.

## Bounded revision requested

Preserve the submitted plan unchanged. Write a **v2** plan in a separate file,
preferably no more than 2,500 words excluding a compact evidence appendix:

1. Corrected source/evidence table; no fabricated hashes, APIs or numbers.
2. First work package: matched observer diagnostic, with correctness coverage,
   frozen inputs, explicit source/environment and persisted phase timings.
3. Next package only after the diagnostic: one small measured bottleneck or
   freshness-order boundary, with changed-input/refusal tests and one genuine
   real-schema micro integration. No general verification-result cache by default.
4. One complete synthetic canary, then one injected-failure witness, then affected
   cohorts; broad final coverage remains required. Mark blocked tests unexercised.
5. CI duration calibration as an independent later package, with actual harness
   and measurement provenance rather than a universal scaling factor.
6. Specific files/owners, dependencies, acceptance and stop conditions, diagnostic
   budgets and rollback per package. Do not compete with active U3-K/L/M work.

No implementation, provider calls, native executables, test campaigns or changes
to current scientific inputs are authorized by this review. Lead reviews v2.
