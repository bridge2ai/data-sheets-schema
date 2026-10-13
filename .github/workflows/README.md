# GitHub Actions workflows

Current workflow routing, 2026-10-12 (#5017, #3863). Executable YAML is the
authority for triggers, permissions, commands and required jobs. This index does
not authorize a provider run, deployment, or changes to an existing registration.

## D4D assistant

Read the [current assistant guide](../D4D_ASSISTANT_README.md) for the complete
request, authorization, input and output contract. [d4d-agent.yml](d4d-agent.yml)
implements that contract using the repository input-bundle/API path:

1. The trusted request parser and controller allow-list admit an explicit request
   for one directory under `data/sheets_d4dassistant/inputs/`. Event-specific checkout
   rules decide which input files exist; untrusted request prose cannot supply new
   authorization rules.
2. `src/github/assistant_bundle.py` prepares every supported regular input file
   before generation, retaining source/conversion/bundle hashes in a manifest.
   Unsupported or unreadable input refuses; links and scripts are not fetched or run.
3. The workflow calls `d4d api run` with that bundle, then validates the generated
   full YAML before opening a PR and posting the workflow's status comment.

Only the selected input directory supplies source documentation. Additional issue
prose and URLs are not generation inputs. Ordinary feedback does not instruct the
workflow to edit an existing datasheet; another explicit request is subject to the
documented request, run-label and output checks.

The old open-ended agent action was replaced. This workflow does **not** load
`d4d_assistant_create.md` or `d4d_assistant_edit.md`, and does not require enabling
project MCP servers or changing local Claude permissions to operate. Do not follow
the former setup/reset/authentication instructions for this API workflow.

Those create/edit files remain intact because separately selected interactive
playbooks or historical instruments can name them. Consult the
[interactive command index](../../.claude/commands/README.md) for that separate
route; do not silently substitute it for the GitHub workflow. The previous workflow
README is [preserved with its historical context](../../docs/agent-instructions-history/README.md).

## Build and test

[main.yaml](main.yaml) runs the complete collected `tests/` suite, including corpus
checks, on Python 3.12: six shards for PRs, four for main/manual runs, with at most
four xdist workers per shard. Separate canary, audit/finalization and evaluation
jobs run their complete offline commands for all these events. Main/manual runs
also build schema products and examples in a separate checkout. The aggregate
`test` check fails when an applicable required job fails, is cancelled or is skipped.

See [CI partitioning](../../utils/ci_sharding.md) for coverage, timing weights,
worker configuration, artifact retention and the refresh procedure. Timing data
does not select which tests exist. Package support for Python 3.9+ is broader than
this CI matrix; do not describe the workflow as testing three interpreter versions.

Use `poetry install` for dependency setup in an existing checkout. `make setup`
is repository scaffolding: it generates, stages and commits files. `make test`
already includes its schema check; a separate early `make test-schema` is optional
feedback, not an additional mandatory final gate.

## Before changing a workflow

Read its actual YAML and directly referenced helpers/tests. Preserve complete
coverage, trusted input boundaries, provider authorization, generated-file checks,
historical evidence and published-output obligations. Use focused checks while
iterating, then complete the required final CI/review gates. Do not infer that a
Markdown/data-only change is harmless: this repository stores executable policy,
model-facing instructions and scientific inputs in those formats.
