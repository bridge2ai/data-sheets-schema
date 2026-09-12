# Codex Adversarial Review

Target: branch diff against f474913423f70afdcda7c72d4e18f0624dc72b24
Verdict: needs-attention

NEEDS ATTENTION at 79f628202: coverage, evidence binding, accounting, preservation and statistics check out, but two VOICE rubric20 judgments apply an unsupported provenance penalty.

Findings:
- [medium] [P2] Flag Q19 deductions that contradict the frozen provenance rule (data/evaluation_llm/rubric20_semantic/reference_2026-09-11/VOICE_v7_rep3_r20_rating1_evaluation.json:455-456)
  Q19 deducts a point because lineage lacks structured representation and allegedly no field connects activities, entities and agents. However, the supplied data/d4d_concatenated/claudecode_agent/2026-09-01_claude-opus-5-api-generic-v7_rep3/VOICE_d4d.yaml:722–731 explicitly maps software to generated features, and lines 780–782 connect released features to standardized audio through b2aiprep. The pinned .claude/agents/d4d-rubric20-semantic.md:396 expressly accepts complete textual provenance. VOICE_v7_rep1_r20_rating1_evaluation.json in the same output directory likewise deducts for lacking programmatic traversal at line 453. These unsupported deductions propagate into the 82/88 and 81/88 totals in notes/reference_rescore_2026-09-11/results.md. Passing serialization, arithmetic and provenance checks does not establish that these judgments followed the instrument.
  Recommendation: Preserve the original ratings and transcripts. Add a dated, evidence-linked erratum identifying these Q19 failures and qualify the affected totals in the results and completion summary before manuscript use; keep any subsequent adjudication separate from the original measurements.

Next steps:
- Resolve the documented Q19 interpretation failure without changing the frozen instrument or silently rewriting scores.
- Limitations: review covered published tracked artifacts and representative semantic justifications; external source truth and billing were not independently verified. The n=3 panel remains descriptive, rubric20 repeatability remains unmeasured, and this review does not certify general-generation behavior.
