# W7-BC1-BOUNDARY-01: fixed D62 refusal premise moved under D63

2026-10-30. Local review issue; offline rules prohibit GitHub filing.

The unchanged `tests/test_bc1_registration.py` ran on private archive
`28a2d625d6224d4848303197f0739daecacb43e3` from packet
`07700a4c70fcd9f842d4d51086c2dd6ec39958ce`: **28 passed, 1 failed**.
Both original refusal parameter outcomes were observed before editing: the
4,000,000 aggregate / 1,000,000 per-call case failed because the CLI successfully
wrote a valid registration; the 4,500,000 aggregate / 600,000 per-call case passed
its CLI/library refusals. General fit refusals and inclusive-boundary tests
passed. This is a stale numerical test premise, not a relaxed production guard.

Original evidence remains in
`d4d-executions/plans/reviews/wave7_resume_2026-10-30/bc1-original-registration-01/`:

- `outcome.json`: `bb211a7705e9acae26b55d86de49bcbea55c465a5a21985919e8403b6872dd38`.
- `pytest.xml`: `6b39177161a534cc2386f37e4b07afd235cbfd9ff625989da16e451b6c33c240`.
- Original test-module SHA-256: `a067d1b649fe389d9d4dc10cc4cf7914306d2c0374acc76599ebc1cb1b15bd3b`.

The independently reviewed design replaces the two fixed refusal numbers with
the actual current gated boundary. Real `prepare_registration` uses the exact
same label, registration path and completed record as the CLI, with generous
unrelated limits and no disk writes. The aggregate boundary uses only
`GATED_SCENARIOS`; the per-call boundary uses only rows marked `gated`. Advisory
scenarios remain outside acceptance. An exact-boundary CLI dry run must succeed,
show its explicit dry-run marker and write no directory. At boundary minus one,
both the real CLI and library must refuse, name the measured boundary and leave
no output directory. No serializer, calibration, production allowance or guard
changes. Existing independent Fraction/component tests remain unchanged.

The formatter emits altered registration identities as fixed-length hashes;
raw aggregate/per-call cap numerals do not become request text. The positive
control and exact numeric refusal assertions verify this boundary premise in
the actual composed execution. This tests admission behavior, not calibration
truth or scientific acceptance. Implementation review and fresh-archive tests
remain pending. Preserve the original completed evidence and fixture outputs.

Independent read-only implementation review confirmed the bounded test change
at module SHA-256 `3faec9cbb38c5896a0df5ab24d039183b2c501d4d6efea3b7502ac7bf4bd9dca`,
the two original parameter outcomes and the unchanged production/calibration
sources. No blocker was found before local commit and fresh-archive validation.
