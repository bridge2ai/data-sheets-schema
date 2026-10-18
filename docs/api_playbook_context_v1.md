# Opt-in API playbook context v1

Issue #4014: historical generic and tuned templates ask the model to open the
provenance guard and full/core playbook. An API request has no filesystem tools;
those references did not deliver the factual boundary or phase responsibilities.

`api_playbook_version=1` is a separate instruction condition, supported only with
API renderer 8. It supplies `src/download/prompts/api_playbook_v1.md` directly in
every phase request. Version 0 (the default, omitted from recorded specs) retains
historical request text and assembly hashes for renderers 1–23, including agentic
instructions. No existing prompt pin, registration or saved run is replaced.

Use an explicit new run label and register this instruction axis before comparing
outcomes. For an offline inspection with a neutral external bundle:

```sh
d4d api plan --project EXTERNAL --bundle /inputs/source.txt --manifest none \
  --condition generic_v9 --label new-api-policy-v1 --api-playbook-version 1 --json
d4d api render-prompt --project EXTERNAL --bundle /inputs/source.txt --manifest none \
  --condition generic_v9 --label new-api-policy-v1 --api-playbook-version 1 \
  --runtime 'Claude API (direct)'
```

`api run` and `api batch` accept the same flag. Rendering defaults to the agentic
runtime, so it requires the explicit API runtime above. Agentic runtimes and any
other renderer refuse version 1 before execution. This implementation performs no
live runs and does not authorize spending or modifying held study registrations.

The adapter selects sections from the registered base template before substituting
paths/names or inserting tuned evidence. It preserves the full metadata header and
all selected-condition decision rules. Its runtime adaptations are:

| Historical directive | API v1 behavior |
| --- | --- |
| Open two `.claude` playbooks | Inline the frozen factual and phase policy |
| Write full/core/report output paths | Return the final phase's requested artifact; controller writes destinations |
| Generate core and its header | Controller derives core from validated same-run full; no model core generation |
| Run shell validation/provenance commands | Controller runs checks and records provenance; model must not claim unavailable results |
| Forbid every generated record, including current work | Current-run carried artifacts are allowed work products, never independent factual evidence |
| Treat schema files as factual inputs | Supplied digest is structural authority; bundle and manifest context provide facts |
| Return counts and completion summary in every phase | Follow the final phase-specific artifact format |

The controller's phase gates, source context blocks, cache boundaries, deterministic
core derivation and final phase suffixes are unchanged. Conditions requiring a
coverage receipt retain their existing receipt suffix; other conditions do not
acquire one. This policy does not import later generic decision rules into earlier
conditions or consume the mutable agentic playbooks.

The policy is pinned in the canonical registry and checked against a frozen SHA256.
A recorded rendering spec carries both `api_playbook_version` and
`api_playbook_sha256`; replay requires the exact supported version and digest.
The provenance prompt-file list includes the policy. Agentic playbooks remain
recorded as not consumed on the API runtime. Resume identity binds the new spec
and resolved instruction, refusing cross-policy resumes.

The assembly digest additionally binds this policy version, digest and adaptation.
`condition_delta` reports an `assembly` difference, and `runs compare-arms` reports
an `assembly digest` confound even when both runs use the same generic condition.
Condition names alone cannot establish equivalence; use recorded procedure facts.
