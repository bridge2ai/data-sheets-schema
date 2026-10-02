# Rubric20 Evaluation Summary

**Generated:** 2026-10-02 12:03:02

**Total Evaluations:** 131

Summaries separate record kind, rubric/version, the complete recorded evaluator settings, recorded rubric hash and score maximum. Missing metadata stays unrecorded; recorded hashes (including legacy placeholders) are not verified instrument digests. Generator identity is not inferred from method names.

Counts and averages describe evaluations, not distinct files: repeated ratings are retained and equally weighted. The discrimination blocks separately exclude records rated more than once within their cohort.

Cohort selection: recursive `individual/**/*_evaluation.json` and direct `concatenated/*_evaluation.json` children. Dated concatenated subdirectories are excluded. `all_scores.csv` lists every selected evaluation and its source path relative to this directory.

## Concatenated D4Ds

### Scored out of 84 — concatenated evaluations by claude-fable-5

8 evaluation(s); rubric rubric20, version 1.0. Recorded rubric hash: 5a63dff015cbd0555b8413b79f6f474f59518fc1dc8dea13850f0004d291709a.

Recorded evaluator settings: {"evaluation_type": "llm_as_judge", "name": "claude-fable-5", "temperature": 0.0}.

| Project | Method | Score | Percentage | Cat1 | Cat2 | Cat3 | Cat4 | Top Question | Weakest Question | D4D File | Evaluation File | Evaluation Time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AI_READI | claudecode_agent | 83/84 | 98.8% | 21 | 21 | 24 | 17 | Q1: Field Completeness... (5/5) | Q11: Tool and Software Tr... (4/5) | data/d4d_concatenated/claudecode_agent/2026-04-10_sonnet-4.6/AI_READI_d4d.yaml | concatenated/AI_READI_claudecode_agent_evaluation.json | 2026-07-22T00:00:00Z |
| AI_READI | claudecode_agent_core | 82/84 | 97.6% | 21 | 21 | 23 | 17 | Q1: Field Completeness... (5/5) | Q11: Tool and Software Tr... (3/5) | data/d4d_concatenated/claudecode_agent_core/2026-04-10_sonnet-4.6/AI_READI_d4d_core.yaml | concatenated/AI_READI_claudecode_agent_core_evaluation.json | 2026-07-22T00:00:00Z |
| CHORUS | claudecode_agent | 78/84 | 92.9% | 21 | 21 | 20 | 16 | Q1: Field Completeness... (5/5) | Q13: Version History Docu... (3/5) | data/d4d_concatenated/claudecode_agent/2026-04-10_sonnet-4.6/CHORUS_d4d.yaml | concatenated/CHORUS_claudecode_agent_evaluation.json | 2026-07-22T00:00:00Z |
| CHORUS | claudecode_agent_core | 77/84 | 91.7% | 21 | 21 | 19 | 16 | Q1: Field Completeness... (5/5) | Q13: Version History Docu... (3/5) | data/d4d_concatenated/claudecode_agent_core/2026-04-10_sonnet-4.6/CHORUS_d4d_core.yaml | concatenated/CHORUS_claudecode_agent_core_evaluation.json | 2026-07-22T00:00:00Z |
| CM4AI | claudecode_agent | 81/84 | 96.4% | 20 | 21 | 23 | 17 | Q1: Field Completeness... (5/5) | Q4: File Enumeration and... (4/5) | data/d4d_concatenated/claudecode_agent/2026-04-10_sonnet-4.6/CM4AI_d4d.yaml | concatenated/CM4AI_claudecode_agent_evaluation.json | 2026-07-22T00:00:00Z |
| CM4AI | claudecode_agent_core | 84/84 | 100.0% | 21 | 21 | 25 | 17 | Q1: Field Completeness... (5/5) | Q1: Field Completeness... (5/5) | data/d4d_concatenated/claudecode_agent_core/2026-04-10_sonnet-4.6/CM4AI_d4d_core.yaml | concatenated/CM4AI_claudecode_agent_core_evaluation.json | 2026-07-22T00:00:00Z |
| VOICE | claudecode_agent | 84.0/84 | 100.0% | 21 | 21 | 25 | 17 | Q1: Field Completeness... (5/5) | Q1: Field Completeness... (5/5) | data/d4d_concatenated/claudecode_agent/2026-04-10_sonnet-4.6/VOICE_d4d.yaml | concatenated/VOICE_claudecode_agent_evaluation.json | 2026-07-22T00:00:00Z |
| VOICE | claudecode_agent_core | 84/84 | 100.0% | 21 | 21 | 25 | 17 | Q1: Field Completeness... (5/5) | Q1: Field Completeness... (5/5) | data/d4d_concatenated/claudecode_agent_core/2026-04-10_sonnet-4.6/VOICE_d4d_core.yaml | concatenated/VOICE_claudecode_agent_core_evaluation.json | 2026-07-22T00:00:00Z |

### Scored out of 84 — concatenated evaluations by hybrid-heuristic-evaluator

12 evaluation(s); rubric rubric20, version 1.0. Recorded rubric hash: sha256-rubric20.

Recorded evaluator settings: {"evaluation_type": "rule_based_with_quality_heuristics", "name": "hybrid-heuristic-evaluator", "temperature": "N/A"}.

| Project | Method | Score | Percentage | Cat1 | Cat2 | Cat3 | Cat4 | Top Question | Weakest Question | D4D File | Evaluation File | Evaluation Time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AI_READI | claudecode | 49/84 | 58.3% | 10 | 4 | 18 | 17 | Q2: Entry Length Adequac... (5/5) | Q1: Field Completeness... (0/5) | data/d4d_concatenated/claudecode/AI_READI_d4d.yaml | concatenated/AI_READI_claudecode_evaluation.json | 2025-12-08T19:16:57.567637 |
| AI_READI | claudecode_assistant | 56/84 | 66.7% | 10 | 9 | 20 | 17 | Q2: Entry Length Adequac... (5/5) | Q1: Field Completeness... (0/5) | data/d4d_concatenated/claudecode_assistant/AI_READI_d4d.yaml | concatenated/AI_READI_claudecode_assistant_evaluation.json | 2025-12-08T19:16:57.606638 |
| AI_READI | gpt5 | 3/84 | 3.6% | 3 | 0 | 0 | 0 | Q2: Entry Length Adequac... (3/5) | Q1: Field Completeness... (0/5) | data/d4d_concatenated/gpt5/AI_READI_d4d.yaml | concatenated/AI_READI_gpt5_evaluation.json | 2025-12-08T19:16:57.558510 |
| CHORUS | claudecode | 16/84 | 19.0% | 8 | 1 | 3 | 4 | Q2: Entry Length Adequac... (5/5) | Q1: Field Completeness... (0/5) | data/d4d_concatenated/claudecode/CHORUS_d4d.yaml | concatenated/CHORUS_claudecode_evaluation.json | 2025-12-08T19:16:57.612149 |
| CHORUS | claudecode_assistant | 41/84 | 48.8% | 10 | 7 | 10 | 14 | Q2: Entry Length Adequac... (5/5) | Q1: Field Completeness... (0/5) | data/d4d_concatenated/claudecode_assistant/CHORUS_d4d.yaml | concatenated/CHORUS_claudecode_assistant_evaluation.json | 2025-12-08T19:16:57.637382 |
| CHORUS | gpt5 | 10/84 | 11.9% | 10 | 0 | 0 | 0 | Q2: Entry Length Adequac... (5/5) | Q1: Field Completeness... (0/5) | data/d4d_concatenated/gpt5/CHORUS_d4d.yaml | concatenated/CHORUS_gpt5_evaluation.json | 2025-12-08T19:16:57.609490 |
| CM4AI | claudecode | 46/84 | 54.8% | 10 | 4 | 15 | 17 | Q2: Entry Length Adequac... (5/5) | Q1: Field Completeness... (0/5) | data/d4d_concatenated/claudecode/CM4AI_d4d.yaml | concatenated/CM4AI_claudecode_evaluation.json | 2025-12-08T19:16:57.669692 |
| CM4AI | claudecode_assistant | 46/84 | 54.8% | 10 | 4 | 15 | 17 | Q2: Entry Length Adequac... (5/5) | Q1: Field Completeness... (0/5) | data/d4d_concatenated/claudecode_assistant/CM4AI_d4d.yaml | concatenated/CM4AI_claudecode_assistant_evaluation.json | 2025-12-08T19:16:57.705094 |
| CM4AI | gpt5 | 28/84 | 33.3% | 10 | 8 | 3 | 7 | Q2: Entry Length Adequac... (5/5) | Q1: Field Completeness... (0/5) | data/d4d_concatenated/gpt5/CM4AI_d4d.yaml | concatenated/CM4AI_gpt5_evaluation.json | 2025-12-08T19:16:57.661543 |
| VOICE | claudecode | 54/84 | 64.3% | 13 | 9 | 18 | 14 | Q2: Entry Length Adequac... (5/5) | Q1: Field Completeness... (0/5) | data/d4d_concatenated/claudecode/VOICE_d4d.yaml | concatenated/VOICE_claudecode_evaluation.json | 2025-12-08T19:16:57.723893 |
| VOICE | claudecode_assistant | 54/84 | 64.3% | 13 | 9 | 18 | 14 | Q2: Entry Length Adequac... (5/5) | Q1: Field Completeness... (0/5) | data/d4d_concatenated/claudecode_assistant/VOICE_d4d.yaml | concatenated/VOICE_claudecode_assistant_evaluation.json | 2025-12-08T19:16:57.777263 |
| VOICE | gpt5 | 0/84 | 0.0% | 0 | 0 | 0 | 0 | Q1: Field Completeness... (0/5) | Q1: Field Completeness... (0/5) | data/d4d_concatenated/gpt5/VOICE_d4d.yaml | concatenated/VOICE_gpt5_evaluation.json | 2025-12-08T19:16:57.716685 |

## Individual D4Ds Summary

### Scored out of 84 — individual evaluations by hybrid-heuristic-evaluator

111 evaluation(s); rubric rubric20, version 1.0. Recorded rubric hash: sha256-rubric20.

Recorded evaluator settings: {"evaluation_type": "rule_based_with_quality_heuristics", "name": "hybrid-heuristic-evaluator", "temperature": "N/A"}.

| Project | Method | Avg Score | Evaluations | Avg % | Avg Cat1 | Avg Cat2 | Avg Cat3 | Avg Cat4 |
|---|---|---|---|---|---|---|---|---|
| AI_READI | claudecode_agent | 9.2/84 | 14 | 11.0% | 6.9 | 1.2 | 0.2 | 0.9 |
| AI_READI | claudecode_assistant | 8.6/84 | 14 | 10.3% | 4.7 | 1.9 | 0.8 | 1.3 |
| AI_READI | gpt5 | 7.1/84 | 8 | 8.5% | 2.0 | 1.2 | 1.6 | 2.2 |
| CHORUS | claudecode_agent | 24.8/84 | 12 | 29.4% | 10.0 | 4.0 | 5.0 | 5.8 |
| CHORUS | claudecode_assistant | 15.4/84 | 12 | 18.3% | 9.0 | 1.8 | 1.5 | 3.1 |
| CHORUS | gpt5 | 6.0/84 | 2 | 7.1% | 6.0 | 0.0 | 0.0 | 0.0 |
| CM4AI | claudecode_agent | 14.2/84 | 12 | 17.0% | 8.8 | 3.2 | 1.2 | 1.2 |
| CM4AI | claudecode_assistant | 15.2/84 | 12 | 18.2% | 7.8 | 4.6 | 1.0 | 1.8 |
| CM4AI | gpt5 | 10.5/84 | 4 | 12.5% | 4.5 | 2.0 | 0.0 | 4.0 |
| VOICE | claudecode_agent | 11.2/84 | 9 | 13.4% | 5.3 | 5.3 | 0.0 | 0.6 |
| VOICE | claudecode_assistant | 13.1/84 | 9 | 15.6% | 7.9 | 2.4 | 1.2 | 1.6 |
| VOICE | gpt5 | 15.3/84 | 3 | 18.3% | 3.3 | 2.0 | 7.0 | 3.0 |

## Top Performing D4Ds (Score >= 80%)

Up to 20 evaluations per cohort; ties use the stable evaluation identity order.

### Scored out of 84 — concatenated evaluations by claude-fable-5

8 evaluation(s); rubric rubric20, version 1.0. Recorded rubric hash: 5a63dff015cbd0555b8413b79f6f474f59518fc1dc8dea13850f0004d291709a.

Recorded evaluator settings: {"evaluation_type": "llm_as_judge", "name": "claude-fable-5", "temperature": 0.0}.

| Project | Method | Type | Score | D4D File | Evaluation File |
|---|---|---|---|---|---|
| CM4AI | claudecode_agent_core | concatenated | 84/84 (100.0%) | data/d4d_concatenated/claudecode_agent_core/2026-04-10_sonnet-4.6/CM4AI_d4d_core.yaml | concatenated/CM4AI_claudecode_agent_core_evaluation.json |
| VOICE | claudecode_agent | concatenated | 84.0/84 (100.0%) | data/d4d_concatenated/claudecode_agent/2026-04-10_sonnet-4.6/VOICE_d4d.yaml | concatenated/VOICE_claudecode_agent_evaluation.json |
| VOICE | claudecode_agent_core | concatenated | 84/84 (100.0%) | data/d4d_concatenated/claudecode_agent_core/2026-04-10_sonnet-4.6/VOICE_d4d_core.yaml | concatenated/VOICE_claudecode_agent_core_evaluation.json |
| AI_READI | claudecode_agent | concatenated | 83/84 (98.8%) | data/d4d_concatenated/claudecode_agent/2026-04-10_sonnet-4.6/AI_READI_d4d.yaml | concatenated/AI_READI_claudecode_agent_evaluation.json |
| AI_READI | claudecode_agent_core | concatenated | 82/84 (97.6%) | data/d4d_concatenated/claudecode_agent_core/2026-04-10_sonnet-4.6/AI_READI_d4d_core.yaml | concatenated/AI_READI_claudecode_agent_core_evaluation.json |
| CM4AI | claudecode_agent | concatenated | 81/84 (96.4%) | data/d4d_concatenated/claudecode_agent/2026-04-10_sonnet-4.6/CM4AI_d4d.yaml | concatenated/CM4AI_claudecode_agent_evaluation.json |
| CHORUS | claudecode_agent | concatenated | 78/84 (92.9%) | data/d4d_concatenated/claudecode_agent/2026-04-10_sonnet-4.6/CHORUS_d4d.yaml | concatenated/CHORUS_claudecode_agent_evaluation.json |
| CHORUS | claudecode_agent_core | concatenated | 77/84 (91.7%) | data/d4d_concatenated/claudecode_agent_core/2026-04-10_sonnet-4.6/CHORUS_d4d_core.yaml | concatenated/CHORUS_claudecode_agent_core_evaluation.json |
