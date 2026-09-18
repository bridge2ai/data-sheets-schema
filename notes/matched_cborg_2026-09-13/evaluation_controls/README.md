# Registered evaluation controls

These controls run one reviewed evaluation job against an independently
accepted full/core generation pair. They reuse the existing CBORG budget ledger,
stream transport and native controller. They do not accept a generation, choose
a scientific verdict, retry a failed rating, or expand a canary into a cohort.

The present study registration uses CBORG Claude Opus 5, the approved **$400 total
sequence allocation**, and **$5 per evaluation attempt**. These constants belong
to this study's controls, not to the reusable D4D generation package. Existing
charges consume the same allocation. No provider call is needed to render a
request or run the offline tests.

## Before a paid job

1. Independently accept the unchanged generated full/core pair and its complete
   procedural/scientific evidence. Bind both artifact hashes, the generation
   registration hash, and one canonical `evaluation_sequence_state` path in the
   acceptance. This controller path lives outside frozen artifacts and attempts.
2. Register the exact current code commit and immutable file closure, Python
   binary **and environment**, provider/model/prices, source generation evidence,
   fully settled billing checkpoint, applicability context, instrument, output
   paths, deadlines and complete job roster. Preserve the original ledger.
3. Render native instructions with `instructions.render_instruction` and API
   requests with `api.render_request`. Pin those exact files. The latter captures
   the existing library's actual request without constructing a provider client.
4. Obtain an independent registration review naming the exact manifest hash,
   allowed jobs and passing CI for its code commit. A review file does not create
   generation acceptance or scientific canary acceptance.

The launch command is:

```bash
PYTHONPATH=src python notes/matched_cborg_2026-09-13/evaluation_controls/run_evaluation.py \
  --registration /absolute/registration.json \
  --review /absolute/launch_review.json --job REGISTERED_JOB_ID
```

Use the registered virtual environment's `python` and provide `CBORG_API_KEY` in
the parent's environment. The key is never supplied to the native child; it gets
an ephemeral local proxy token. A job has one exclusive attempt directory and
one new published output. Existing paths prevent launch; no resume or overwrite
is supported. The shared sequence lock spans admission, execution and shutdown.
Once ownership advances to a successor registration, siblings and predecessors
cannot spend the old checkpoint. A successor must explicitly identify the last
evaluation registration and its current, fully settled ledger.

## Instruments and evidence

| Style | Execution and acceptance contract |
|---|---|
| `semantic_agent` | Native session with the pinned semantic definition, source rubric, complete input and caller context; definition check-echo before tools; exact semantic validator |
| `field_agent` | Native session with its separate field-oriented definition and score domain; exact field-agent validator |
| `direct_api_quality` | Existing `D4DLLMEvaluator` template instrument, one complete streamed JSON rating |
| `grounding` | Existing slot scorer with the selected value and exact source bundle |
| `fitness` | Existing slot fitness scorer with the complete class/profile/schema specification |
| `subtype` | Existing form classifier, only for registered prior fitness judgments classified as form failures |

API jobs allow one call and no transport retry. Complete provider termination,
strict JSON, the instrument's valid score domain and settled accounting are
required. Truncated or duplicate-key responses remain failed artifacts. A
watchdog stops late writes after deadlines; SDK cleanup is bounded separately.
Every repeat constructs a fresh scorer and makes its own request.

Native sessions use `--safe-mode`, `--restricted`, fresh CLI configuration, no
session persistence, strict MCP configuration and only Read, Write and the exact
registered validation command. Explicit additional directories make registered
external inputs reachable; the controller still admits only exact read files
and the attempt's own output directory. This is a tool admission policy, not an
OS sandbox. The complete original input, context and rubric are also embedded in
the instruction, whose exact deterministic rendering is checked before launch.
The native system prompt is the original pinned agent definition.

Acceptance requires callback/control history, runtime identity, the definition
echo, typed successful Write evidence for the final candidate, a successful
validator report after that Write, and a fresh parent validation. Disallowed
operations are recorded; a denied prescribed or unclassifiable operation fails
the attempt. No other evaluation is available through the registered Read policy.

The mechanical receipt is deliberately named
`completed_pending_independent_review`. Review the scientific application of each
style/rubric/full-or-core canary before admitting that group's remaining jobs.
Its independent acceptance binds the receipt and output hashes. Neither valid
JSON nor passing arithmetic proves a correct judgment.

Conditional subtype requests need the actual fitness explanation. Prepare a
separate reviewed successor registration after fitness completes, using
`subtype_selection: all_form_failures` and the complete unchanged parent evidence.
The runner checks that the roster covers exactly those failures, with matching
input, slot value and class/profile/specification identities. It cannot render a
future explanation before it exists or silently select favorable failures.

Offline presence, schema/pair, receipt, provenance and report checks remain
separate instruments. Do not relabel them as paid semantic or quality ratings.
The dated execution plan must enumerate them alongside the paid roster.

## Verification

```bash
PYTHONPATH=src python -m pytest \
  notes/matched_cborg_2026-09-13/evaluation_controls -q -p no:cacheprovider
```

Tests use actual validators and ledgers, real local child processes, and the
Anthropic SDK over an offline mock HTTP transport. They do not send provider
requests. Controller regression tests additionally need local loopback sockets.
CI runs this suite once on the Python 3.12 offline shard.

The review fixes include #2090 (CoreDataset subtype identity), #2091 (field-agent
exact-file validation), #2093 (strict responses, bounded cleanup and conditional
subtype registration), and #2095 (exclusive shared-budget handoff). Historical
generation controls retain their original default command classifier; evaluation
passes its own exact-command classifier explicitly.
