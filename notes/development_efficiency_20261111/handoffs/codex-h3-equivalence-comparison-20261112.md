# Native equivalence comparison handoff

Commit: `e82c36abdb2b25a55b71c2e67552edc7a7c1f8b5` (first implementation `e7b256cc2`); base `6561dac3c3af50cbfce1ba3c8b6ad21d9cd4b834`.

- `native_equivalence_compare.py` SHA-256: `af787b48328393e5e45f8f657bbb5adb363c58220f4cc77cbe088c92559d7fd1`
- `native_equivalence_compare.json` SHA-256: `b685e084b69c074a940851f8ba77996470bcfa77ca77a27fd6bf3ffc15e1f39e`

permitted_locations: 23, dependent_values: 2581, wire_layers: 124, artifacts: 443, rule_objects: 6825, rule_modules: 319, rule_data_files: 42.

| Demonstration | Result | Exit | Differences |
|---|---|---:|---:|
| self | equal | 0 | 0 |
| irrelevant | equal | 0 | 0 |
| prompt | not_equal | 1 | 340 |
| runtime | not_equal | 1 | 319 |
| threshold | not_equal | 1 | 1 |
| identity | equal | 0 | 0 |

Each result, input, driver, policy and pair of snapshots is pinned in the companion JSON. Saved evidence is under `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-h3-equivalence-20261112`.

The script/data SHA-256 values above hash their actual committed file bytes. A comparison result’s `policy_sha256` hashes canonical JSON without a final newline; its saved `policy.json` is that canonical JSON plus a newline. Those encodings intentionally have different hashes from the indented review data file.

## Fixed test and review boundary

The adjacent data file lists exact parsed locations and the ordered dependency preimages. Embedded JSON command arguments are parsed losslessly; original hash/length bindings are verified before recomputation. Numeric limits, prompt and schema bytes are content. Unlisted artifacts, missing rule objects, unavailable helpers or uncovered identity differences hold. Rule changes are reported with object names and unified diffs for two independent reviewers.

Every package module-level function, class and assignment, plus captured controller Python sources; imports and other module statements compared separately. All package JSON/YAML data files are additionally byte-compared to guard data-driven rules. The package-wide inventory includes completion gates, receipt predicates, floors, accounting, cause classification, runtime limits, registration and admission. Captured historical controller sources cover the selected legacy control closure. This is a conservative superset, not a pruned call graph. Dynamic imports outside this inventory and external libraries are not proven complete. Fixed fixture recipes are pinned separately. New or missing objects/data files hold.

Reproduction: invoke the production script with the dependency interpreter using `-S -P -B`, `--left` and `--right` immutable exported trees, `--inputs /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-h3-equivalence-20261112/inputs.json`, `--out` a new directory outside both trees, and `--site-packages` the dependency-only site directory. The adjacent frozen policy is the default. Export `src`, `scripts`, `notes`, `tests`, `.claude`, and `pyproject.toml`. Do not regenerate the policy after seeing a pilot. The development freezer and mutant builder are provenance, not the production comparison path.

Tests: `[{"name": "pytest", "errors": "0", "failures": "0", "skipped": "0", "tests": "21", "time": "0.865", "timestamp": "2026-11-12T18:38:53.883091", "hostname": "marcins-MacBook-Pro.local"}]`. All four protected files retain candidate bytes, including its approved post-images. No production prompt pins were changed; the prompt mutation and its required pin change exist only in a saved mutant export.

## Runtime visibility

The companion JSON lists every full-runtime object location, runtime-hash site and numeric-limit field found in the fixed experiment, including parsed recorder arguments. Static flows:

- native_shared_render.metadata: raw runtime path, SHA-256 and raw_json enter render_spec.
- native_shared_render.commands: recorder --render-spec-json embeds that complete render_spec.
- native_shared_render.instruction: recorder command appears in the instruction; provider and literal model appear in its header; effort is in render_spec.
- native_shared_policy.command_policy and command_guidance: command table, allowed tools, Bash rules, post-final recorder and fenced system guidance repeat the recorder command.
- native_shared_registration.permission_expectation: runtime, permission_environment, recorder command and selected policy; instruction/system hashes and derived probe recipe.
- native_shared_stage._Replay: every request carries execution.runtime_declaration_sha256 and instruction_sha256; receipt and typed stage requests derive max_output_tokens through receipts.output_ceiling.
- native_shared_receipts.prepare and final checks: output ceiling bounds the fixed receipt request; check results and receipt carry enter subsequent requests.
- Registered helper CLI feedback can expose runtime-related refusals; all eighteen fixed command outputs are retained. Branches not reached by these inputs remain unobserved.

## Reported exposure; no production change

The entire raw declaration is model-facing through the recorder argument: auth method/provider/subscription evidence and expected API-key source, executable path/hash/version/init version, PATH/HOME/secure-storage configuration and context flag, keep-awake host/basis, limits-basis observation details. These appear unnecessary for scientific generation and disclose account/machine context. No production output was changed.

Deadline, budget guard, context window and output ceiling are genuine literal content; they are not identity exceptions.

## What this cannot see

- Fixed synthetic experiment, not proof of behavior on every input. Render and typed-stage recipes are separate pinned synthetic contexts; they are not a production execution or a real observation chain.
- The input adapter reuses candidate test recipes and pins every candidate test Python file. A change to any pinned test file holds, even if the change would be irrelevant to the experiment. This is deliberately conservative; the current adapter does not carry an independent frozen recipe bundle across test refactors.
- All registered helper commands are invoked, but many exercise refusal paths. Actual initial/final receipt-check returns, source-inventory outputs and the full fixed stage sequence are captured separately. The initial receipt check is checked=true, passed=false; it drives the synthetic rereceipt sequence. Successful production recorder, validator and permission-probe branches are not claimed.
- Only selection identifiers at the listed locations may differ. Timestamps, attempt roots, filesystem layout and other identities are not granted category-wide exceptions; uncovered identity differences hold.
- Rule inventory conservatively covers all package Python objects and captured historical controller Python objects; additional data-file checks are listed separately. Reviewers must confirm the inventory and judge listed changes. Arbitrary dynamic code, external dependency changes and native binary behavior are not proven equivalent.
- Both trees run in the same dependency environment and physical replay location, sequentially per comparison. A private Git commit represents exported content, not the original source commit. Export provenance is recorded separately.
- Python audit barriers deny network, subprocess execution except read-only git rev-parse, and writes outside the output. This is an offline trusted-source experiment, not a sandbox for hostile Python or native extensions.
- A cannot_decide result is a hold, never permission to replace a pilot reading. No result is launch authority.

## Earlier failures and disposition

producer-canary-01 through producer-canary-10 retained in scratch; early adapter construction failures and incomplete policy rosters are not passing evidence.

demo-identity returned cannot_decide on four missing read-observation preimages; observation artifacts were added and the policy regenerated from the unchanged candidate baseline.

demo-final-self held after byte-preserving capture exposed two newline-terminated JSON artifacts. Explicit lossless json_newline wire sites were added from that candidate-only baseline. Earlier unit harness attempts held writes outside scratch; TMPDIR and logging were redirected into scratch, without weakening the effect guard.

No push, PR, GitHub write, native execution, provider/model call, probe, capture or reservation. Only the assignment-required read-only fetch preceded local work.
