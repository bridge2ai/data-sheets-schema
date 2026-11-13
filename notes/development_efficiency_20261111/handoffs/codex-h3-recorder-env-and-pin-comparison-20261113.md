# Helper 3 recorder environment and pin comparison

Part 1 commit: `c577c0eff176440206a93f6647d8fd2f19a6d224` on `codex/native-recorder-env-20261113`. Status: Part 1 committed; validation and Part 2 design ruling pending.

The exact saved synthetic model-facing recorder line is 1806 characters (1806 UTF-8 bytes), excluding its newline:

```bash
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-h3-recorder-20261113/tests/recorder-bound-digest-01/venv/bin/python -m data_sheets_schema.cli provenance record --project SYNTHETIC --method claudecode_direct --label offline-test --input-bundle /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-h3-recorder-20261113/tests/recorder-bound-digest-01/cases/test_native26_model_line_and_c0/inputs/bundle.txt --manifest /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-h3-recorder-20261113/tests/recorder-bound-digest-01/cases/test_native26_model_line_and_c0/source-manifest.yaml --profile neutral --chunk-manifest /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-h3-recorder-20261113/tests/recorder-bound-digest-01/cases/test_native26_model_line_and_c0/inputs/chunk_manifest.txt --reasoning-effort high --prompt .claude/agents/d4d-provenance-guard-v2.md --prompt .claude/commands/d4d-agent-v2.md --prompt .claude/commands/d4d-full-core-v2.md --prompt .claude/commands/d4d-uniform-rules-v2.md --prompt src/data_sheets_schema/omission_inventory_v1/context.schema.json --prompt src/data_sheets_schema/omission_inventory_v1/policy.md --prompt src/data_sheets_schema/omission_inventory_v1/response.schema.json --prompt src/download/prompts/d4d_generic_arm_prompt_v10.md --prompt src/download/prompts/evidence_protocol_v7.md --prompt src/download/prompts/native_shared_generation_v1.md --prompt src/download/prompts/native_shared_receipt_policy_v1.md --prompt src/download/prompts/native_source_attribution_v1.md --prompt src/download/prompts/shared_generation_v1.md --render-spec-env D4D_RENDER_SPEC --render-spec-sha256 f4708e6b35c694c735cc28eeb98f75c39df1a5ffbbd3b7dfd73bfc1ab4d3e670 --prompt-text-env D4D_LAUNCH_INSTRUCTION
```

The new ending is `--render-spec-env D4D_RENDER_SPEC --render-spec-sha256 <registered digest> --prompt-text-env D4D_LAUNCH_INSTRUCTION`. The controller supplies the JSON. The recorder admits only the literal variable name, rejects missing/empty values and conflicting options, verifies the specification digest and retains the existing reconstruction and exact instruction checks. The historical JSON option remains supported.

Local review finding H3-RE1: initial commit f57ac61da lacked the digest anchor, allowing a changed non-model-visible specification field to leave the instruction unchanged. Final commit c577c0eff fixes that. Do not take f57ac61da alone. The lead must file H3-RE1 externally if required; no GitHub write was authorized. The latest whole focused cohort has 59 passes, including coherent value-plus-command rehash refusal.

The 2282 notes show a literal environment-variable name was admitted while shell expansion was refused. This command uses no expansion and no inline JSON; an apostrophe inside the specification therefore never enters the command. Other independently supplied command paths still retain their existing spelling constraints. No runtime-permission admission is claimed without a real authorized probe.

Changed model-facing artifacts: recorder command in initial instruction, registered helper command table, recorder command in tool policy and Bash allow rules, command guidance appended to the base system instructions, derived instruction/system/command hashes in stage requests. Permission expectation/environment and source pins are supporting changes. Replay confirmation is pending unless the companion JSON contains completed replay evidence; no claim is made from an unproduced snapshot.

## CI triage and launch carry

The baseline readback file passed 15 tests. The merged export reproduced all eight closed-wire failures: the component fixture was intentionally incomplete, and the new diagnostic preflight checks that shape. The repair supplies the closed wire with explicit placeholders; all production checks and existing assertions remain intact. The failure-publication file did not exist at the baseline. At the merged head, its seven tests pass in isolation once local Git metadata is supplied; the reported foreign-origin failure depends on broader collection/prior-state. The isolation repair uses the established fixture, with a historical collection import included in the fixed export run.

Preserved original repairs `48cb2d1f494add9903851af3c3babce31213af79` and `ef193e4eabc65a1c7ab39ecc64ad2945889f3416`; added H3-LR1 as `a22c51a9d082cad64eccb64c2de900b32e8e2630`, without rewriting. Their carried hashes and the two separate CI fixture commits are below. Fetch was attempted but failed to resolve GitHub; base is the locally available published `8760de5efe88b5af62e9d77e6335fa7e248017b6`.

- `53c45bf6488e8e6117464b89c8c4fc6dda0e05e1 Require the existing pinned journal start for sequence capture (6048)`
- `115c1f68770969e46901c0afbbebf2e6582e6ae5 Call the trusted launch-entry validator directly (6047)`
- `19988f6df21cc693c1237eab07899623013bda63 fix(native): recheck unspent generation under capture lock (6048, 6047)`
- `cdfad9fc6bebc8b9fa98f70d4d65416b040f80c7 test(native): complete readback component wire after diagnostic preflight`
- `922b6d5c5cc353e00ea6e5b1c3fb7f8524211483 test(native): isolate failure publication from foreign controller aliases`
- `f57ac61da03bfd7e6d81903ec2bf097c5903b8c0 fix(native): pass recorder specification through controller environment (6065)`
- `c577c0eff176440206a93f6647d8fd2f19a6d224 fix(native): bind environment specification digest into recorder instruction (6065)`

## Saved checks

- base-failure-publication: {"tests": 0, "failed": 0, "errors": 0, "skipped": 0}
- base-readback: {"tests": 15, "failed": 0, "errors": 0, "skipped": 0}
- fixed-ci-export: {"tests": 23, "failed": 0, "errors": 0, "skipped": 0}
- fixture-fixes: {"tests": 22, "failed": 1, "errors": 0, "skipped": 0}
- merged-failing-files: {"tests": 22, "failed": 10, "errors": 0, "skipped": 0}
- merged-failure-git: {"tests": 7, "failed": 0, "errors": 0, "skipped": 0}
- merged-origin-collection: {"complete": false}
- recorder-bound-digest-01: {"tests": 59, "failed": 0, "errors": 0, "skipped": 0}
- recorder-focused-01: {"tests": 55, "failed": 0, "errors": 0, "skipped": 0}
- recorder-public-native26: {"complete": false}

The initial merged publication reproduction lacked Git metadata. The working-tree fixture run changed HEAD during registration reconstruction and is not acceptance. Both are retained, not relabelled as passes. The stable fixed export is the acceptance rerun.

## Part 2 decision required

No pin-comparison gate or allowlist is presented. The existing production verifier loads the pinned consumer source through `_consumer` and `verified_source_module`, rederives preparation, and requires its exact checkout. Calling it violates the requested prohibition on executing either input tree; substituting a structural parser would silently weaken validation. A ruling was requested: add separately reviewed data-only production packet validation, or permit isolated existing production validation before a data-only comparison. No self/other-project/prompt/binary/floor equivalence demonstrations are claimed. Script/data hashes are therefore absent.

Part 3 has not started; it follows Part 2. The four protected files and guard v1 match the base byte for byte (computed hashes in JSON). No real native binary, provider/model call, probe, capture, reservation, push or GitHub write. Synthetic tests write only their own evidence. Other CI failures and cancelled shards remain untriaged here.

## Development replay reading

The accepted aid produced both snapshots but retained cannot_decide because its old inventory lacks four merged support modules. That hold is preserved. The focused expected-change assertion reports explained_model_projection, 388 byte-identical artifacts, and model-unresolved artifacts []. It verifies the exact recorder substitution, lossless Bash rule spelling, source-byte hash preimages and dependent hash propagation. The deliberately missing-environment recorder fixture changes its expected refusal message; successful recording is tested separately. The permission expectation remains supporting evidence and its remaining metadata differences are retained explicitly. This establishes only the fixed synthetic model projection; it is not registration equivalence or an exhaustive behavioral proof.
