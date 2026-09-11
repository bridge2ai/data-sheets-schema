# Evaluation archive provenance correction, 2026-09-11

PR #1221 archives eight obsolete rubric20 results for #1200 without changing their bytes. Review #1223 found that the instrument resolver treated an archive move as a new scoring event. It now follows byte-identical renames, while a move that changes the evaluation uses the new writing commit.

The eight pre-#314 results retain their original `fa90b4ec` recovery and instrument SHA `e8eb3d0f1e64320ce63becfdeb117441ddd0144b246f81c7cdf98b49a8669c1a`. Their paths now include `concatenated/_archive_pre_314/`. Every moved JSON was compared byte for byte with its original.

The same repair corrects 13 existing rubric10 archive attributions. These are provenance corrections, not new evaluations or changes to any score. The recovery remains a commit-based inference; only a recorded instrument hash is direct evidence of which definition the evaluator named. The adjacent JSON preserves each prior mapping beside its correction.

| Archived evaluation | Prior recovery | Corrected recovery |
|---|---|---|
| `label_aware/superseded_fable5/AI_READI_2026-09-01api_rep3_evaluation.json` | `5c891e23` | `97cbbfcb` |
| `label_aware/superseded_fable5/CHORUS_2026-09-01api_rep2_evaluation.json` | `5c891e23` | `97cbbfcb` |
| `label_aware/superseded_fable5/CM4AI_2026-09-01api_rep1_evaluation.json` | `5c891e23` | `97cbbfcb` |
| `label_aware/superseded_fable5/VOICE_2026-09-01api_rep2_evaluation.json` | `5c891e23` | `97cbbfcb` |
| `label_aware/superseded_software_role/CM4AI_2026-09-01api_rep1_evaluation.json` | `8f6d4e23` | `9a859cd1` |
| `label_aware/superseded_software_role/CM4AI_2026-09-01api_rep2_evaluation.json` | `8f6d4e23` | `7b343e70` |
| `label_aware/superseded_software_role/CM4AI_2026-09-01api_rep3_evaluation.json` | `8f6d4e23` | `7b343e70` |
| `label_aware/superseded_software_threshold/CM4AI_2026-09-01api_rep1_evaluation.json` | `7b343e70` | `4795ab99` |
| `label_aware/superseded_software_threshold/CM4AI_2026-09-01api_rep2_evaluation.json` | `7b343e70` | `4795ab99` |
| `label_aware/superseded_software_threshold/CM4AI_2026-09-01api_rep3_evaluation.json` | `7b343e70` | `4795ab99` |
| `label_aware/superseded_software_threshold/CM4AI_2026-09-04gapi_rep1_evaluation.json` | `7b343e70` | `4795ab99` |
| `label_aware/superseded_software_threshold/CM4AI_2026-09-04gapi_rep2_evaluation.json` | `7b343e70` | `4795ab99` |
| `label_aware/superseded_software_threshold/CM4AI_2026-09-04gapi_rep3_evaluation.json` | `7b343e70` | `4795ab99` |

Verification checks the evaluation blob and named agent in each recovered commit, exact-rename ancestry, and a fresh full-manifest resolve. A temporary-repository test changes the agent during an archive move and separately during a move with changed score bytes. No other evaluation mappings changed. The manifest also registers both agents’ new output-validation definitions from `ae3414f9`.
