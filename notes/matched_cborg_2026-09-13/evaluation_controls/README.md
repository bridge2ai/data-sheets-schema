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

## Offline preparation

After independent generation acceptance, prepare the complete initial roster:

```bash
PYTHONPATH=src python notes/matched_cborg_2026-09-13/evaluation_controls/prepare_evaluation.py \
  --destination /absolute/new-evaluation-condition \
  --generation-registration /absolute/generation/registration.json \
  --generation-acceptance /absolute/independent-acceptance.json \
  --generation-job-id REGISTERED_GENERATION_JOB \
  --context-path /absolute/caller-applicability.json \
  --billing-checkpoint /absolute/fully-settled-generation-billing.json
```

The preparer requires existing acceptance of both unchanged artifacts and the
actual final generation ledger. The source bundle must still match its original
generation identity; re-pinning altered source bytes is refused. The evaluation
code, schemas, profiles, definitions and prompts have their own explicit pins.

The endpoint defaults to the generation registration's exact CBORG URL. To use
the documented direct route on LBL-Net/VPN, add
`--provider-base-url https://api-local.cborg.lbl.gov --provider-ca-bundle /absolute/verified-ca.pem`.
The direct route requires an explicit, canonical CA file; it cannot inherit
ambient trust or an unpinned generation transport setting. The new registration
pins the CA and the shared audit transport implementation. Both native and API
evaluations use the same verified client for token counting and generation,
with hostname/chain verification, redirects disabled and no environment proxy
or CA overrides. Its upstream timeout is 1,800 seconds, with a 20-second connect
timeout and no SDK retries. These transport settings do not change model,
effort, instruments or scoring. A public endpoint registration without a CA
retains its existing client defaults. Preparation only validates local trust
material; it makes no connectivity, token-count or model request.

It registers 20 rubric ratings: 12 semantic (three ratings for each rubric/class
cell), four field-agent primaries and four direct-API primaries. Grounding and
fitness cover every populated schema-known top-level slot in each selected
dataset. Excluded empty or non-schema fields are listed in the slot inventory.
An undeclared resource container is refused as ambiguous scope; an explicit
Dataset or CoreDataset retains its component resources within that dataset.

Primary canaries precede dependent repeats and slot sweeps. Each group's first
eligible slot is chosen lexicographically, before observing judgments. Subtypes
remain deferred until the complete fitness results exist. The preparer creates
no billing ledger, allocation claim, attempt, acceptance or launch approval.

The preparation report includes exact request sizes, the complete roster and a
clearly labeled local cost estimate. Bytes divided by four is only a token-size
heuristic; native cost estimates use the entire attempt cap. Sum-of-caps exposure
is distinct from expected spend. Recheck provider prices and use actual canary
costs before expansion; request admission always uses the shared live ledger.
Preparation does not contact a model or token-count endpoint.

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
