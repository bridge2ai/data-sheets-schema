# #2912 applicability draft — independent R1

Reviewed head: `0c636dc142f3a021d9f48e083704a6081575b390` in `/private/tmp/d4d-loop-2912-20261002`.

Reviewed manifest SHA256: `c630db4d39bc7a2ab0e0bbb90ad9a73d65cf389f2b15ebf5955213a83c170ba1`.

Reviewer: Codex AI assistant, independent review agent `/root/review_pr_group_b`. This is an AI engineering/evidence review, not named human scientific approval. I reviewed the actual packet, pinned source passages and surrounding scope, normalizer, verifier, and relevant pinned rubric/agent definitions. I did not author or edit this packet.

**Verdict: no new material finding requiring a code or packet correction before publishing this explicitly unapproved draft for review.** No GitHub finding filed. This is not a conclusion that all 35 predicates are settled under one accepted scientific interpretation. #2912 must remain open, and the packet does not authorize an evaluation.

## Predicate review

All 35 declarations were checked against their supplied citations, values, evidence text, scope limitations, and the pinned predicate machinery. There are 30 true and five unresolved/null declarations; no false declaration or proposed denominator exclusion. The existing normalizer retains all 35 in applicable denominators, with the five nulls explicitly marked unknown.

| Project | Human subjects | Governed access | Shared | ML training | Collection | Processing | Processing software |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AI_READI | Human participant origin supported | Public attestation/reuse conditions and separately controlled full data supported | Conditional download supported | Null is appropriate pending intended-use definition | Multimodal collection supported | Correction and OMOP/DICOM mapping supported | Null is defensible; checking software is not silently treated as transforming software |
| CHORUS | Patient-admission origin supported | Controlled access and signed agreement supported | Controlled reuse supported | Preserved true is an intended-model-development proposal; common interpretation still required | Retrospective and multisite collection supported | Standardization/tokenization/deidentification evidence supported, completion caveats retained | OHNLP extraction/tokenization supported; no version or every-release inference |
| CM4AI | Null preserves the distinction between human-origin cell lines, the release's regulatory label, and a separate patient analysis | True is supported under the pinned governance-constraint meaning, pending selected-instrument confirmation | Public files under reuse conditions supported | Explicit intended AI model training supports proposal | Named cell-line experiments supported | Project-method evidence supports proposal only at its stated scope | Named Cell Mapping Toolkit supports project-method proposal; not proof that it produced the June release |
| VOICE adult | Adult derived-feature release and 833 participants supported | Credentialing/DUA supported, raw-audio route separate | Conditional sharing of derived data supported | Null is appropriate pending intended-use definition | Consent and voice/clinical acquisition supported | Audio feature conversion and phenotype processing supported | b2aiprep v3.0.0 is explicitly tied to the adult release |
| VOICE pediatric | 300 participants aged 2–18 and consent supported | Credentialing/DUA supported | Derived-feature sharing supported | Null is appropriate pending intended-use definition | Age-appropriate acquisition supported | Feature derivation and phenotype preprocessing supported | b2aiprep and named feature tools supported; adult software version is not transferred |

### Scientific decisions that remain holds, not newly discovered implementation defects

1. **Common ML-training interpretation is not yet settled.** CHORUS's frozen true declaration relies on planned model development and an external-validation holdout; CM4AI explicitly names intended AI model training; the other three null declarations describe broader AI/ML research or tool-development intent. The packet explicitly asks the human reviewer to decide the threshold consistently, including revisiting CHORUS through a new reviewed context if needed. It does not claim a trained model, a released train/test split, or empirical applicability stability. The snapshot cannot become an accepted consistent panel simply by running its verifier.
2. **CM4AI needs an accepted record scope.** The June release says Human Subjects: No and describes commercially available de-identified human cell lines. The Nature paper separately analyzes 914 pediatric/young cancer patients. Those patients are not the experimental release's cohort. The cited pipeline section concerns the paper's cell-mapping methods; the release explicitly omits computed maps. The packet discloses these distinctions. A June-release-only evaluation cannot inherit project-wide processing/software claims or downstream participants without renewed scope review.
3. **Applicability and earned documentation points remain different questions.** The pinned rubric10 agent explicitly excludes validation-only software and a pipeline whose outputs are absent from the scored release from satisfying the software-documentation item. AI_READI's REDCap checking and OMOP DQD passages do not by themselves name a release transformation tool. Its additional bundled questionnaire answer `N/A - no labeling was performed` at lines 4409–4410 is not evidence that no preprocessing software exists. Null is preferable to such a false exclusion. The software predicate also must not be defined merely by whether a name is documented in the record being scored.
4. **Regulation is not used as a participant signal.** CM4AI's noncommercial/share-alike restrictions and embargoes support a governance constraint under the pinned instrument wording, not patient-data credentialing or an FDA classification. This does not resolve human_subjects.
5. **Adult and pediatric releases are correctly separated in this draft.** Adult v3.1 has 833 participants and b2aiprep v3.0.0; pediatric v1.1.0 has 300 participants aged 2–18, with separately cited methods. A pediatric method mention inside the adult source does not change adult cohort membership. Original raw audio and its separate access route are not attributed to either PhysioNet derived-feature release.

The README and manifest already identify these interpretation/scope holds and require named human review. They are therefore limitations of the draft's current scientific acceptance, not concealed bugs requiring duplicate issues.

## Independent identity and adversarial checks

Probe script: `/tmp/d4d-2912-review-probes-b.py`.
Machine-readable proof: `/tmp/d4d-2912-review-probes-b.json`.

The independent script completed successfully with the primary repository virtualenv, `PYTHONDONTWRITEBYTECODE=1`, and `PYTHONPATH=src`:

- All five bundle byte sequences equal both their manifest pins and the named Git base `e16a5105ac69aacd85881ca3b2825c1df5fbfa55`; current-source substitution was not used.
- All 33 citations independently matched exact inclusive byte-preserving physical-line excerpts, excerpt hashes, nearest containing `FILE:` header, exact original filename, and source-section boundary.
- All 35 context values matched the evidence ledger and normalized context hashes, with exact seven-predicate coverage per project. No citation was borrowed across projects.
- All ten original ignored CHORUS files were read from the primary worktree and matched the recorded original hashes. The copied v2 context and all three copied companions are byte-identical to those originals. The originals were unchanged after the probes.
- Six independent mutations, confined to disposable copies, were rejected: altered quote with refreshed evidence-file pin; reversed citation range; adult/pediatric citation swap; invented named human reviewer; changed normalizer source; and pinned source path escaping the repository.
- The packet's own verifier also passed at the immutable head and reported the expected manifest digest, five contexts, 35 declarations, 33 citations, five nulls, human review pending, and evaluation unauthorized.
- All packet/pinned-input hashes stayed unchanged, the author checkout stayed clean, and no source files were edited.

The direct original-file checks include ignored content. The additional AI_READI software/source-role search used `rg --no-ignore --hidden` across the complete exact pinned AI_READI bundle; it was a bounded source review, not an assertion that no relevant software or context exists anywhere else.

## Approval and publication boundary

`prepared_by` is explicitly AI, the prior CHORUS reviewer identity is unverified, and every human-review approval field remains pending/null. Preserved historical review text is not promoted to human approval. A passing verifier checks the fixed packet's supplied identities; it is not a scientific approval or evaluation admission gate. The external review should pin this exact manifest digest.

No provider/web calls, paid evaluations, GitHub mutations, source changes, pushes, merges, or protected-original writes occurred. Human predicate/scope approval, selected semantic/Q19 instrument, eligible record identities and original-bundle joins, new registration, CM4AI canary, repeated ratings, and applicability stability remain outstanding as documented.
