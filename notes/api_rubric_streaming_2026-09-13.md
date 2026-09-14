# Direct API rubric streaming — 2026-09-13

Issue #1779 was reproduced before any scientific request: the registered
32,000-token direct API quality rating exceeds the installed SDK's default
non-streaming admission limit. The reproduction used the actual SDK and a
fake HTTP transport; it reached zero HTTP requests.

`LLMEvaluationConfig(stream=True)` explicitly selects streaming while retaining
the rubric, complete user prompt, model, token ceiling and sampling parameters.
The evaluator requires both the terminal `message_stop` event and an accepted
stop reason before validating and retaining a rating. Evaluation metadata
records `response_transport`. Existing callers retain non-streaming behavior
unless they opt in; there is no automatic fallback or output-cap reduction.

The offline tests use both current rubric contracts, a two-resource external
clinical fixture and the actual SDK behind the experiment's spending guard.
Successful replies settle one request and retain its original response.
Missing terminal events or reasons preserve the response and pending charge,
accept no rating, and block another request. The evaluator also refuses a
missing terminal event without the experiment guard. Existing sampling,
identity, scope and invalid-result checks remain in the focused suite.

The generation condition remains frozen in its own worktree. This evaluator
change does not modify those registered source or implementation bytes. Before
any scoring, prepare a separate evaluator registration with this code, explicit
streaming, accepted generation inputs, applicability, exact requests, outputs
and the existing canonical sequence ledger. Reverify its own instrument and
review/CI; do not reuse the generation launch approval. Keep semantic and
field-oriented agent canaries separate, with their pinned preambles, check-echo,
original-output checks, both semantic rubrics and repeat ratings.

Validation: 48 focused tests pass; no scientific call or new score accompanies
this change. The existing $200 additional sequence allocation and cumulative
$5 per generation/evaluation attempt remain binding.
