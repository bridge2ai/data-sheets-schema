# Superseded Fable 5 evaluations

These files are the claude-fable-5 scores of the runs named in their
`label` field. They are kept as evidence and are **not** read by
`scripts/arm_comparison.py`, whose glob does not descend into this
directory.

They were moved here when the arm was rescored under `claude-opus-5[1m]`,
so that `label_aware/` holds exactly one evaluation per (label, rubric)
under one evaluator. Nothing about the judgements is retracted: an
evaluator is an instrument, and a score is only comparable to another
score from the same one.
