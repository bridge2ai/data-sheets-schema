# Codex readiness review for a v5 generation arm — 2026-08-15

Independent adversarial review, run because six prior in-session review rounds
had each found real defects and a seventh opinion was wanted before spending a
generation arm.

| | |
|---|---|
| date | 2026-08-15 |
| reviewer | Codex (GPT-5.x), via the `codex:rescue` plugin |
| session id | `01a0086b-383a-7d71-9e54-00f380278a3f` |
| resume | `codex resume 01a0086b-383a-7d71-9e54-00f380278a3f` |
| repo state | `main` at `d709c86c` |
| scope | PRs #548–#571 |

**Verdict: not ready.** Five blocking defects, eight should-fix-before-run, one
minor. Notably it contradicts claims made in this repository's own PR
descriptions and in `notes/generic_v5_analysis_plan.md` — see items 10 and 11,
which say the measured baselines are not reproducible and that a v4-vs-v5
comparison is confounded beyond what the plan admits.

The review is reproduced **verbatim** below. Nothing has been corrected,
softened, or re-ordered, including where it disagrees with figures recorded
elsewhere in this repository. Any of its findings that are later disputed
should be disputed in a separate document or issue, not by editing this one.

---

## 1. Verdict

**No.** The v5 prompt body is correctly pinned, but the API and agentic runtimes receive materially conflicting identifier and spelling rules; `reconcile_full` can promote unsupported core hallucinations into the full record; and the proposed v4-vs-v5 comparison is confounded by pipeline and schema changes. Several new checks also silently skip inputs, over-suppress findings, or remain non-fatal while the batch command reports success.

## 2. Confirmed defects

1. [d4d_generic_arm_prompt_v5.md:213](src/download/prompts/d4d_generic_arm_prompt_v5.md) requires every identifier to be a CURIE, while [d4d-uniform-rules.md:33](.claude/commands/d4d-uniform-rules.md) permits—and at line 39 requires—URLs when no prefix exists. Agentic runs read both; API runs read only the prompt body, so the runtimes implement different conditions. Introduced by #559/#564. **Severity: blocking.**

2. The parity test checks only phrases such as "as a CURIE" and "American English," not semantic equivalence ([test_playbook_reach.py:87](tests/test_playbook_reach.py)). It therefore passes despite the conflict above and despite agentic-only project examples such as `b2ai-voice:` and a Fairhub DOI ([d4d-uniform-rules.md:39](.claude/commands/d4d-uniform-rules.md), [d4d-uniform-rules.md:59](.claude/commands/d4d-uniform-rules.md)). **Severity: blocking.**

3. `reconcile_full` is told to absorb *anything* stated only by core ([api_runner.py:492](src/data_sheets_schema/api_runner.py)), even though the preceding audit explicitly detects unsupported core content ([api_runner.py:481](src/data_sheets_schema/api_runner.py)). A core hallucination can therefore become authoritative in both records. Introduced by #566/#567. **Severity: blocking.**

4. The resume path silently builds phases with whichever prerequisites happen to exist instead of requiring all `PHASE_NEEDS` ([api_runner.py:1895](src/data_sheets_schema/api_runner.py)). Missing artifacts do not invalidate downstream completed phases, while an invalid core only clears `core` and `reconcile_core`, leaving stale audit/reconcile/report phases marked complete ([api_runner.py:1865](src/data_sheets_schema/api_runner.py)). An interrupted v5 run can resume with stale audit findings or run reconciliation without core. **Severity: blocking.**

5. `plan()` claims to render the whole assembly but carries only the Phase-1 full placeholder ([api_runner.py:595](src/data_sheets_schema/api_runner.py)); its audit lacks core, `reconcile_full` lacks core and audit, and later phases lack all declared inputs. `approx_tokens()` also counts cached blocks separately even though those same blocks are already inside `messages` ([api_runner.py:449](src/data_sheets_schema/api_runner.py), [api_runner.py:577](src/data_sheets_schema/api_runner.py)). Dry-run cost/context estimates are not estimates of requests that will actually run. **Severity: should-fix-before-run.**

6. The report phase is asked to describe what reconciliation changed but receives only the audit findings, not either reconciled output ([api_runner.py:513](src/data_sheets_schema/api_runner.py), [api_runner.py:542](src/data_sheets_schema/api_runner.py)). Reports must reconstruct or invent actions they cannot observe. The report-claim verdict then pins only the report, not the full/core records or schema it checked against ([api_runner.py:1320](src/data_sheets_schema/api_runner.py)). **Severity: should-fix-before-run.**

7. `grounding.check_run` returns `checked: true` with zero findings when both record files are absent because missing paths are simply skipped ([grounding.py:165](src/data_sheets_schema/grounding.py)). Its distinct sets also preserve identifier case ([grounding.py:145](src/data_sheets_schema/grounding.py)), so case-insensitive DOI variants are miscounted as distinct; a direct check counted `doi:10.1234/ABC` and `doi:10.1234/abc` as two. Introduced by #547/#555. **Severity: should-fix-before-run.**

8. Report claims explicitly concerning both records fall into `_target == "either"` and are checked only against core ([report_claims.py:148](src/data_sheets_schema/report_claims.py), [report_claims.py:273](src/data_sheets_schema/report_claims.py)); a "removed from full and core" claim passes if core removed it while full retained it. Dotted schema claims are checked using only their root slot ([report_claims.py:361](src/data_sheets_schema/report_claims.py)), so "`distributions.bogus` is undeclared" is falsely contradicted because `distributions` exists. Introduced by #546/#553. **Severity: should-fix-before-run.**

9. `schema_moved` is true after any change to the full-schema digest ([d4d_pair_consistency.py:703](src/data_sheets_schema/d4d_pair_consistency.py)), then downgrades every shared-slot presence mismatch to a warning ([d4d_pair_consistency.py:267](src/data_sheets_schema/d4d_pair_consistency.py)). It does not establish that the particular slot was added after the run, so unrelated schema edits suppress real historical pair defects. Introduced by #550/#561. **Severity: should-fix-before-run.**

10. The v5 plan's baselines are not reproducible against current data ([generic_v5_analysis_plan.md:46](notes/generic_v5_analysis_plan.md)): current checks find minted fragments in AI_READI rep2/rep3 that its "0 elsewhere" omits, 320 undeclared CURIEs rather than 370, and 618 generated-prose British occurrences rather than 627. **Severity: blocking.**

11. `comparable_conditions()` treats adjacent bases as an isolating comparison ([api_runner.py:114](src/data_sheets_schema/api_runner.py)), so it labels v4-v5 comparable even though v5 adds four rules and #566 changes request assembly. The v4 records also pin schema digest `622e…`, while current v5 would use `44d…`. This comparison cannot measure only "the v5 block." **Severity: blocking.**

12. The agentic phase log accepts arbitrary phase names and treats any bare name as completed ([cli/provenance.py:21](src/data_sheets_schema/cli/provenance.py)); downstream status checks only that a nonempty list exists ([runs.py:1179](src/data_sheets_schema/runs.py)). It does not require the four phases or verify their completion, so it can report a phase account without proving reconciliation ran. Introduced by #562/#571. **Severity: should-fix-before-run.**

13. API batch success depends only on individual schema validation ([cli/api.py:325](src/data_sheets_schema/cli/api.py)); pair divergence, a failed report/grounding check, or ungrounded identifiers still enter the "succeeded" count. The canary will not automatically stop the sweep on the defects v5 is intended to measure. **Severity: should-fix-before-run.**

14. `--project VOICE` in `backfill-checks` matches `VOICE_PEDIATRIC_provenance.yaml` because filtering uses `startswith("VOICE_")` ([cli/provenance.py:556](src/data_sheets_schema/cli/provenance.py)). A scoped overwrite can modify records outside the requested project. Introduced by #552/#557. **Severity: minor.**

## 3. Answers to questions 1–5

### 1. Prompt genericity, pinning, and runtime reach

The executable body is generic: `prompt_body()` strips everything above `## Prompt body` ([api_runner.py:315](src/data_sheets_schema/api_runner.py)), and no project name or rationale count occurs in that body. The whole file is not generic—its rationale names VOICE, CM4AI, identifiers, and measured counts ([d4d_generic_arm_prompt_v5.md:26](src/download/prompts/d4d_generic_arm_prompt_v5.md))—but the documented launch path renders only the body.

Pinning is correct. The on-disk whole-file SHA-256 is `606e7382…`, body SHA-256 is `baf755f8…`, and size is 11,812 bytes, matching [canonical_hashes.yaml:123](src/download/prompts/canonical_hashes.yaml) and commit `9b6dd51d`. `d4d api prompts check --strict` reported 11 canonical files, zero failures.

All four topics reach both runtimes, but they are not equivalently enforced. API sees the body; agentic sees the body plus the uniform-rules file. Their CURIE/URL and American-English scopes conflict, the agentic path gets project-specific examples the API path does not, and the parity test only probes phrases. None of the four is a fatal post-generation gate.

### 2. Effects of giving `reconcile_full` core

No prior-run cache or cross-project context is directly introduced: core is carried as an uncached same-run artifact after the bundle/schema prefix. The material risks are:

- A confirmed feedback loop: unsupported core-only content is ordered into full.
- A confirmed resume-invalidation defect: stale audit/reconciliation can survive a regenerated or missing core.
- Copying wording verbatim is discouraged at [api_runner.py:499](src/data_sheets_schema/api_runner.py), but no check detects it. Whether a real v5 model does so remains unverified.
- The dry-run planner does not include the added core artifact, so it cannot assess the context increase it claims to estimate.

### 3. Correctness of the new checks

They are not fully correct.

- Grounding silently passes missing/empty record input and miscounts case variants as distinct.
- Report checking misses explicit both-record claims, can falsely contradict dotted-path schema claims, and does not bind its verdict to the records/schema checked.
- Backfill's project filter is not exact.
- The pair checker correctly distinguishes exceptions/missing files as `ran: false`, and its finding truncation is explicit, but `schema_moved` suppresses too broad a class of historical presence errors.
- All three API-side checks are recorded after repair, which is correct, but batch success ignores their outcomes.

Read-only executions reproduced 11/12 v4 pair divergences and the documented 19/10 ungrounded identifiers. A dry-run of `backfill-checks` processed all four rep1 projects and reported its findings without writes. The full pytest invocation could not start because this sandbox exposes no writable temporary directory.

### 4. Honesty and reproducibility of the analysis plan

The plan is honest only about one limitation: four prompt rules move together, so effects cannot be attributed within that block ([generic_v5_analysis_plan.md:9](notes/generic_v5_analysis_plan.md)). It is not honest about the larger comparison: v4-v5 also changes reconciliation inputs/instructions, provenance behavior, phase logging, checks, and schema digest. Therefore even attribution to "the v5 block" is unavailable.

Current-data reproduction produced:

- Correct: absent identifiers 19 in VOICE rep1 and 10 in CM4AI rep3; URL-valued identifier slots 397; pair divergence 11/12.
- Incorrect/stale: minted fragments omit AI_READI rep2=14 and rep3=13; undeclared CURIEs are 320 because `urn:`/`ark:` are classified as no-authority URIs, not undeclared CURIEs; generated-prose British occurrences are 618 across the pair, with 626 total including quoted occurrences, not 627.

### 5. Fresh-run reproducibility and interpretation

Prompt pinning, resolved-request hashing, bundle/schema hashes, assembly digest, phase snapshots, and observed API context usage are useful and correctly present. Ordering of normal phase execution is deterministic.

A fresh run remains uninterpretable as an experiment because:

- the two runtimes do not implement the same rules;
- v4-v5 is confounded by procedure and schema changes;
- planner context/cost numbers do not describe actual requests;
- resume can reuse stale dependencies;
- reports cannot observe the changes they claim to summarize;
- agentic phase completion is unvalidated self-report;
- batch calls pair/claim/grounding failures "success."

## 4. Open questions / things requiring a real v5 batch

- Whether the model copies core wording verbatim into full after the new feedback instruction.
- Whether conflicting CURIE/URL instructions produce systematically different API and agentic identifiers.
- Whether AI-READI's enlarged `reconcile_full` request fits the provider's unstated context ceiling.
- Actual v5 pair-divergence, grounding, spelling, and omission rates.
- Whether the model follows unsupported-core audit findings instead of the unconditional absorption instruction.

Codex session ID: 01a0086b-383a-7d71-9e54-00f380278a3f
Resume in Codex: codex resume 01a0086b-383a-7d71-9e54-00f380278a3f

---

*End of verbatim review.*
