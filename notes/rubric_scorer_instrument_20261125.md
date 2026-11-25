# Codex semantic rubric instrument registration draft

Issue 6315; prepared 2026-11-25. Build and offline tests only. A live scorer
evaluation needs the owner's separate authorization; this document grants none.

Instrument name: `2026-11-25_codex-gpt-6-astra-ultra-fast_semantic-v3`.
The model is explicitly `gpt-6-astra`, reasoning effort `ultra`, requested
service tier `fast`, using noninteractive Codex CLI. The runner supplies all
three settings and ignores user configuration and inherited rules. It records
the entrypoint file hash and the CLI version observed in the run's session log.
A launcher script's hash is not a pin of every executable it launches.

One invocation selects one record, one exact method directory and label, and
one of `rubric10-semantic` or `rubric20-semantic`. Each gets a new run directory
outside the checkout, a new home and Codex home, and a working directory with
only that record and its rubric inputs. The parent directory must already exist.
The method directory is an explicit argument, including a future release runtime
directory; there is no hardcoded study roster or generation-runtime assumption.

The prompt includes the complete, unchanged selected agent definition, source
rubric, output schema and frozen version-3 evidence authority. An independently
supplied applicability context is optional. Full file bytes occur between named
BEGIN/END delimiters. The plan and receipt pin their SHA-256 values and the
complete rendered prompt. The wrapper supersedes only old runtime, batch and
output-location examples; it does not replace or shorten any scoring criterion.
The controller supplies normalized context, its canonical digest and scope
identities, so the evaluator need not invent hashes or applicability exclusions.

Registered source files at the specified main base:

- `.claude/agents/d4d-rubric10-semantic.md`:
  `c817aa5fefd91552be68016818c8a87ab91b8798ac96666d975bc61af32c7fb3`.
- `.claude/agents/d4d-rubric20-semantic.md`:
  `35de3a37264e80f48e6e037fed42b6cc586152058d4da6c08bad93b8096f588b`.
- `data/rubric/rubric10.txt`:
  `9a03a8366d1ef2f6e82efe2c7e14c45053739f7e9f7f05c1ca1868d75c986a97`.
- `data/rubric/rubric20.txt`:
  `c8c0d3a96878d895006a4f287af761635b64cb1fc7968b3256eb7d37db360612`.
- `data/rubric/semantic_evidence_authority_v3.json`:
  `0605c742c61f2cc4e13de907f8e09752bde5ebd08d173b31d837c273a4bf3872`.

The full output schema hash is selected separately for each rubric and recorded
by every plan. The semantic instrument version remains 3.0; a different model
is a different scorer instrument, not an alteration of the criteria version.

Ultra effort can delegate automatically. Each child must stay within the same
one-record context. The acceptance reader requires the emitted root thread id,
fresh exec metadata, matching cwd, actual model and ultra effort in every retained
turn, and a closed set of child logs linked to successful v2 spawn results. A
different model, missing child log, unknown tool, reroute or foreign ancestry
refuses publication. Historical v1 delegation aliases are not accepted.

The runner disables shell, executor, image, hook, memory, application and search
features, supplies no MCP configuration, and accepts only the reviewed delegation
operations in session history. The read-only sandbox is not a filesystem read
confinement guarantee. These controls provide isolated inputs and an acceptance
audit; a live canary must confirm the installed CLI's actual tool/session shape.
No such live evidence is claimed by the offline tests.

The raw response is preserved. Only the evaluator model metadata is stamped by
the controller, using the matching root session's observed model, with runtime
temperature null when unobserved. No scores, applicability choices or evidence
are repaired. `evaluation_model` records the observed name, explicit selection
basis, log hashes, requested tier and `service_tier_observed: null`. The inspected
CLI logs do not expose the served tier. A requested fast tier is not evidence of
which tier the server served.

New outputs go to:

```text
data/evaluation_llm/RUBRIC_semantic/label_aware/2026-11-25_codex-gpt-6-astra-ultra-fast_semantic-v3/PROJECT_LABEL_evaluation.json
```

Before publication the runner executes, from the selected checkout:

```sh
poetry run python scripts/validate_evaluation_schema.py --file CANDIDATE --rubric RUBRIC-semantic --input ORIGINAL_RECORD --agent-definition ORIGINAL_DEFINITION
```

An explicit caller context adds `--context ORIGINAL_CONTEXT`. Validation uses an
existing virtual environment with environment creation disabled. The runner
captures the candidate bytes and hash before invoking the real schema and
structured-evidence validator, requires exit zero and unchanged candidate bytes
afterward, then publishes that captured snapshot exclusively. Existing outputs and spent run directories
are refused. Failed candidates, process output and refusal receipts are retained.
The copied authentication file is private transient runtime state and is excluded
from the retained artifact inventory. The runner unlinks only its copy immediately
when Codex exits, before validation, and again during final cleanup on failure,
timeout or interruption. The original caller file is preserved. Catchable SIGTERM
uses the same cleanup path. An uncatchable process kill or host failure cannot run
Python cleanup; inspect such abandoned runs before archiving them. Cleanup is not
a claim that arbitrary model responses or CLI logs can never contain a secret.

This differs from the earlier Claude-subagent scorer in model, reasoning policy,
CLI, delegation, session evidence and tool restrictions. Do not pool the two
sets of scores or infer calibration from using the same rubric. The nested
instrument directory also keeps these new outputs out of legacy direct-child
comparison readers until that instrument is explicitly selected.

Offline entrypoints:

```sh
python scripts/adhoc/score_semantic_rubric_codex_20261125.py --help
python scripts/adhoc/plan_semantic_rubric_label_20261125.py --help
```

The driver only lists plans. It has no batch execution mode. After the owner
authorizes one live canary, review its schema/evidence result and actual session
identity before authorizing further evaluations. Open decisions are that live
authorization and subsequent calibration/comparison acceptance, not a change to
the already selected model, effort or rubric criteria.
