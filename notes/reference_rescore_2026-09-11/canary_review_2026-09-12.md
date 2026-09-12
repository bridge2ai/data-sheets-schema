# Reference evaluation canary review — 2026-09-12

The CHORUS v7 rep1 rubric10 canary completed one evaluator session from
2026-09-12T07:20:00Z to 07:28:54Z. Its original assessment is **35/50 (70.0%)**
on both the fixed and adjusted bases, with no excluded sub-elements. This
is one rating of an existing D4D, not a regenerated D4D or a repeatability
measurement. At canary acceptance, the remaining 55 registered ratings had not
been launched.

## Execution and instrument evidence

- Agent definition SHA256 quoted in full in the evaluation metadata:
  `66ad623121272099bf94535ae5be2163a5f5005fe895d2bf2bf04c4f90e34864`.
- The evaluator echoed the revised release-history sentence required by the
  registered preamble. All fifty item names match the source rubric.
- Input SHA256:
  `e5c0f47198cd20ea47158959f6cfb4d25648965eb8c063ac977e2b5b9aba355d`.
- Evaluation SHA256:
  `017f888bdccf12a04b62917e8fa08c39263cf45a5533fb349ca9eb075335199f`.
- Every assistant event identifies `claude-opus-5`. The evaluation reports
  the requested `claude-opus-5[1m]` selector. The successful CLI usage receipt
  explicitly maps that selector to the same canonical model and a 1,000,000
  token context window. Both identities and this evidence are preserved.
- Temperature is null; no deterministic-score claim is made.
- The CLI reports a total cost of $2.2204425, including its auxiliary model
  usage, under the registered $5 attempt cap. This is the CLI's reported
  usage cost, not an independently reconciled billing statement.

## Failures, review, and offline recovery

1. #1303: the completed evaluator output was initially rejected because a
   CLI system diagnostic contained a string-valued `message`. The parser
   now accepts validator evidence only from assistant calls and user tool
   results; diagnostics cannot attest validation.
2. #1304: the next check rejected the context selector by literal equality.
   The gate now recognizes this exact selector only with matching canonical
   model and context-window evidence in the successful CLI result. Unknown
   aliases, conflicting identity fields, or contradictory evidence fail.
3. #1305: review of recovery found that a schema-valid edited assessment
   could otherwise be published. A failing regression demonstrated this.
   Recovery now requires byte equality with the last successful Write to
   the evaluator's actual output path, and rejects changes during validation.

The original incomplete receipt, candidate, prompt, transcript, and previous
registration remain byte-for-byte intact. Recovery created a separate receipt
and published the original candidate bytes; it made **zero additional model
calls**. The registered amendment pins runner commit
`6c7b4b43ccf355d11f1b4d6f53cad5bda37ef75f` and manifest
`78dc05cada5a4905d8eabd2320ebcd0054d83e92d5611de93b4f98fc557f324a`.
The complete evaluator prompts, 24 inputs, both instruments, schemas, budget,
cohort, and 202 prior evaluations retain their previous hashes.

Validation: 70 focused tests passed, including the paid-run gates and semantic
JSON contracts. The actual retained transcript and candidate passed check-echo,
identity, schema, arithmetic, original-Write, and frozen-byte checks during
offline recovery. Final review found no additional execution blocker for the
registered evaluation protocol.

The first PR CI run passed 3,445 tests and found one missing derived-index
entry for the new evaluation. Regenerating
`tests/data/evaluation_instruments.json` added the canary's recorded instrument
and the two rubric10 definition versions introduced before it. All 12
instrument-provenance tests then passed. Regenerate this index with
`python scripts/instrument_provenance.py --write` when publishing further
reference evaluations; the operation does not rewrite their scores.

## Assessment review and limits

The review checked all item identities, totals, applicability, and assessment
summaries. It inspected the interpretation of the revised release-history,
processing-software, governance, and social-impact criteria. All five
applicability conditions are recorded as met, consistent with this record's
human clinical data, controlled sharing, and documented collection activity.

Acceptance establishes that the registered scoring procedure completed and
its evidence is retained. It does not independently endorse every judgment.
For example, item 1.1 applies a strict persistence interpretation to the
project-fragment URI. Its prose says the URI "resolves today", but this session
performed no network reachability check; that phrase must not be cited as
verified URL availability. Missing ethics or consent documentation in a
datasheet does not establish that the underlying dataset lacked oversight.

Repeatability and small-difference ranking remain unmeasured. The planned
rubric10 repeated ratings must finish before reporting their spread; rubric20
repeatability remains outside the registered repeat panel.

## Generation scope

The approved reference cohort remains the 24 existing v7/v8 D4Ds with both
semantic rubrics. A separate offline CHORUS `generic_v9` generation plan renders
successfully from the existing source bundle. No new generation or download
was launched. Adding a v9 generation cohort requires its own recorded condition
and generation canary; the existing versions and their scores remain retained.
