# Superseded under the Element 4 gate fix (#1060)

These six CM4AI rubric10 evaluations were made by `claude-opus-5[1m]` under
the agent's earlier text, in which all five Element 4 sub-elements carried
one copy-pasted applicability trigger. Evaluators split on it: two scored the
element (denominator 50) and four excluded it (denominator 45), on the same
project and the same evidence, and one logged the resulting three zeros as an
artifact of the gate rather than a property of the record.

The rule is now stated per sub-element — oversight and deidentification can
apply to a dataset with no human participants; participant privacy, consent
and compensation cannot — and these records were rescored under it. Kept
because they are what the instrument said at the time, and because #1060's
whole point is that the number moved with the reading rather than the record.

## Two rounds, both superseded

The six files here are the **round 0** scores, written under the original
single copy-pasted trigger (denominators 45 and 50).

A first fix edited the per-sub-element prose only, and did not hold: the agent
carries an authoritative conditions table above it that still mapped both
conditions to all five sub-elements, and the rescores said in their own words
that they resolved "the shared condition list once" from that table. Those
round-1 scores were overwritten rather than kept, since they measure a text
that existed for under an hour and was never the instrument.

The second fix corrected the table, scoped the governance condition to
sub-elements 1–2, and told the ambiguity rule it does not reach a condition
that plainly fails. All six rescores then landed on one denominator, 47.
`tests/test_rubric10_element4_gate.py` now asserts the table and the prose
cannot disagree again.
