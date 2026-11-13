# One genuine capture-readback integration canary: execution plan

2026-11-11. Source-only planning; no runtime, copying, integration or source edits performed. Frozen native remains `458887766effe38207a77fea2d8033f1f3e1c7f3`; tools remain `7043f0be145d5a0922cdbd3a73f099e6e9a12a3c`. This plan is a draft on existing `codex/native-development-analysis-20261111` and confers no execution or packet approval.

## Readiness and setup review

Capture A is now clean/committed at `459e56bf896a29d854c5d250ce8632d7e2564427`, parent `458887766effe38207a77fea2d8033f1f3e1c7f3`. Its three-file delta is `native_shared_registration_orchestration.py`, `native_subscription_capture.py`, and `tests/test_native_subscription_capture.py`; all four protected preimages remain unchanged. AST-fact work is still uncommitted in its separate worktree at the inspected snapshot. Do not copy its dirty files, select its current directory as runtime source or invent a final integration SHA.

The proposed one-test node is:

`tests/test_native_subscription_capture.py::test_genuine_registration_read_capture_for_event_rechecks_live_selection_and_stage_root`

Source review of the committed test (`:375–450`) finds:

- **Root:** it changes cwd to `registration.authority.ROOT` before `make_case`; that is necessary for registration reconstruction. The sandbox must import every production module from the new private composition, not from the donor, primary checkout or frozen native source. Run with cwd equal to that private root and basetemp outside every worktree. Do not monkeypatch a production ROOT to make a mixed-origin run pass.
- **Capture path:** the hard-coded `captures/<sha(word_raw)>/capture-1/capture.json` matches `tests/utils/native_synthetic_evidence.py:124–139,179–185`. The fixture creates exactly that slot and hashes the final word after binding synthetic CI. This is coherent for this pinned fixture, not a general slot-discovery algorithm. The readback uses the guard's exact saved event fields, not fresh invented replacements.
- **Process trap:** `git_only` wraps the shared `subprocess.Popen` after the test begins and delegates only list/tuple argv whose basename is `git`, with `shell` false. `make_case` constructs fake peer bytes and saved synthetic authorities; it does not execute the peer. Genuine Git queries use ordinary `subprocess.run`, so this trap permits their Popen path. This is a test sentinel, not an OS security boundary: basename checking alone does not prove the executable's identity, and it does not intercept every OS spawn API. Retain the external network/native-exec sandbox and controlled PATH.
- **Coverage:** unchanged readback must equal the independently read manifest, with exactly `verified → outer-claims → recheck_verified → inner-claims`. The second lookup inserts a regular file at the previously absent stage root after outer claims and must refuse during genuine recheck. Both full `verified` and `_recheck_verified` must separately refuse that same mutation. Wrappers delegate to the actual functions; component stubs are not used by this node.

No further test-source setup change is justified by this inspection alone. Dynamic import/origin, trace-count and fixture-success assumptions remain unexecuted gates; the test is not a prior pass. Two independent read-only checks agree on the test setup and bounded supervisor plan.

**Retained failed attempts:** `agy-native-path-alias-parity-20261111/tmp/capture_recheck_5838_5847/canary-attempt1-mkdir.log` failed before preparation because the supplied pytest directory already existed; current `make_case((tmp_path / 'case').resolve())` fixes that input shape. `canary-attempt2-gitconfig.log` failed at 22.40 seconds in fixture dependency identity (`native_supervisor_authority_v2.head → git rev-parse HEAD`): `fatal: unable to access '/Users/marcin/.gitconfig': Operation not permitted`. Neither reached the readback/mutation behavior. Files named `canary-pass` in this directory must not be interpreted as success without inspecting their JUnit content. Preserve all these logs unchanged.

The retained M/WP1 child environment already uses a fresh output HOME and `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_SYSTEM=/dev/null` (`run_native_u3a_tests_20261107.py:55–66`). `resources.git_env` retains those settings while removing borrowed repository selectors. Require them in the actual child environment witness, not just the outer shell. This addresses the observed inherited-user-config failure without reading personal configuration or relaxing the sandbox. Retain the synthetic CI URL only in the new private repository's backed-up local config.

## Existing supervisor route and required bounded adapter

The current WP1 CLI cannot run this node: `native_wp1_validation_20261110.py:45–54` admits only its existing fixed equivalence/diagnostic nodes. `u3m_validation focused` would select two workers and retain the older 3,290-second selector limit. Do not substitute the new node into an old diagnostic label, run naked pytest, or weaken the node guard.

Preferred future change: a separately reviewed, fixed `capture-recheck` kind in the **existing WP1 supervisor**, not another process-management framework. Retain outer ownership of the detached sandbox through the child gate, deadline-before-preflight, source/contract verification, credential allowlist, network/native-exec denial, dependency and origin witnesses, owned-descendant cleanup and exact restoration. Freeze the supervisor change in the eventual source commit before composing.

The bounded adapter must:

1. Name only the full node above, one worker, a **900-second total invocation cap**, and an exclusive once marker keyed to source/contract/node. Refuse an occupied marker or output; a failure never permits automatic retry under a new label.
2. Use a distinct `capture_readback_integration_canary` classification with every quiet-host/freshness/native-acceptance flag false. Add it to `NO_LEASE_KINDS`, not `QUALIFIED_KINDS` or CPU comparison arms. Refuse an existing quiet-window lock and inherited lease. Preserve existing arm/mode behavior; any monitoring environment field is instrumentation selection, not a CPU comparison claim.
3. Require the existing certified **same-manifest 60-second equivalence canary** before this node, in both outer and supervised admission. The outer no-lease path currently checks canary evidence only for CPU diagnostic kinds; explicitly include this new kind. Pin `tests/test_native_subscription_capture.py` in `REQUIRED_FILES`; record the exact test, harness and composition identities. Keep arbitrary node, retry and timeout overrides unavailable. This target does not consume `U3WP1_CONSUMER_ARM`; do not claim it exercised a consumer-observer arm. Passive phase metrics remain separate.
4. Preserve the existing driver cutoff at outer deadline minus 10 seconds and detached-sandbox cutoff at minus 5 seconds. The outer deadline includes preflight, pytest and cleanup. No 900-second refresh after fixture setup; no timeout widening on failure. Keep cleanup uncertified if interrupted/forced/observed survivors or integrity errors remain.

The existing membership-based driver already handles `NO_LEASE_KINDS`; its supervisor algorithm should remain unchanged. Review the adapter's classification, marker and exact-one-test enforcement before runtime. Do not change either currently frozen checkout during planning.

**Cap rationale:** the retained post-5834 genuine fixture took 183.040 wall seconds (119.922 thread CPU) before launch. This new test constructs it once, then performs an initial capture read, two event lookups and two final refusal checks, with seven further verified/recheck entries. A 30-second cap is incompatible with the observed setup alone. Reuse the already bounded 900-second integration ceiling; this is a ceiling, not a duration prediction or freshness-policy change. The test checks saved-data reconstruction, not a successful fresh reservation. Keep sparse preparation separately bounded at 180 seconds and the prerequisite equivalence canary at 60 seconds: 1,140 seconds of maximum preparation/test budgets, plus separately bounded config restoration. No new profiling or N=10 campaign is included.

## Exact private composition

After review and explicit integration/runtime authorization, record final clean source **S** containing the approved capture commit, final approved AST commit if included, and reviewed fixed-node adapter. The current helper requires S at the assigned native checkout; it cannot compose an arbitrary donor path. Keep native458887/tools7043 untouched until that separate authorization. Do not run this test on the unpatched production checkout.

Use tools7043's `scripts/adhoc/prepare_native_wp1_canary_20261111.py` unchanged (SHA `37963c7d81070dc6dee2b9727fa6fb0db91f9d620515d29e78ab46636b9699aa`) with the existing dependency interpreter, `-S -P -B`, full `--source S`, and exact `--acknowledge-private-api-proposal` equal to the API postimage below. The flag only records the separately granted private validation permission. Preparation is sparse and local: no corpus copy, dependency export, install, hydration or network.

It creates new `scratch-native-u1u3/u3m/composition-<S12>/`, `worktree-<S12>/` and `wp1-contract-<S12>.json`, refusing existing paths. The composition's only delta from S must be these four packets, verified in both worktree bytes and Git tree. Retain the new full composition commit/tree/parent, manifest SHA, interpreter, source/test/adapter pins and local object-store identity.

| Protected target | Preimage SHA-256 | Private postimage SHA-256 | Patch SHA-256 |
|---|---|---|---|
| `src/data_sheets_schema/shared_generation.py` | `94b3cf6845827c8fdf7bf05cc6251e2fb196ceb91ea8ce377f2c9e3b8be3773d` | `2ec18e60316423035f88a2a30263c56385bfbbc587303e84e805a8349ab4f781` | `22b81b6cd63a708d82bfbd038b7e1d9aaf340bf1d86828f138b56dd9ef4756c5` |
| `src/data_sheets_schema/api_runner.py` | `b109cb918a3079a384937ccfad7ab9b195a55713a355f11f848da98fab59596a` | `830eec1e12e96f807fa76ea26e066a1923b60380013c424cfa99f0012af0a881` | `996bd9bce74d509033a1daf340ea2a6edfc2a820316e798459892738a989475f` |
| `src/download/prompts/canonical_hashes.yaml` | `39b93c009457681a1d8d8b8afee5a869bbd6f5e70b6f4332522db5d7e22d0584` | `543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252` | `34db8dfd6e925b114d2df2b74d3de8d39b57482b21603241e1a568815e791ff8` |
| `tests/utils/run_spec_boundary_contracts.json` | `a7f96a253a37e994f0c62c7d9b2ab21b0a94d4f342975f84103cd274ef11af72` | `b1e0cbd14c533a51b88eacb84b974cb93963e18d8f1fb71ae4ed3228f784d1ce` | `dc58e99f73fe5de1a4f6179639dd2cfd2215c0dd665319e8d15b148b1824509f` |

Packet directories remain `scratch-native-u1u3/owner-packets/u3m/2bf9eb831cdc/` for the revised API metadata/packet and `owner-packets/u3h/e0b964b0e182/` for retained D127 inputs, including canonical prompt metadata/packet, as resolved by the unchanged M composer. Verify its `packet_inputs()` overrides; do not manually select the obsolete canonical packet from the historical base table. Protected production files and approval records remain untouched.

## Terminal evidence and stop boundary

Run the prerequisite equivalence canary once on the new manifest; verify its actual one-test JUnit and certified cleanup before admitting the genuine node. Then run the genuine node **once** through the fixed supervisor. Require exactly one matching testcase, zero failures/errors/skips, no timeout or forced cleanup, stable source/contract/dependencies/import origins, and certified outer/supervisor cleanup. Verify nonempty saved fixture artifacts: preparation/composition/registration authorities, capture manifest and constituent files, invented review/word/guard, and the stage-root mutation left for inspection. Do not label synthetic lifecycle declarations as actual native process evidence.

After terminal completion or failure, with owned descendants retired, call unchanged `compose_native_u3m_20261109.py cleanup --commit S` once under a separate bounded helper invocation (proposed ceiling 180 seconds). It refuses foreign config bytes, restores `tree/.git/config` byte-for-byte and mode from `config.bak-u3m-20261109`, and writes `config-restored.json`. Keep the source checkout at S through cleanup. If setup partially failed, restoration times out or config identity differs, preserve everything and report rather than resetting/overwriting; no restoration success without readback and witness. Retain all manifests, logs, JUnit, deadline/cleanup/origin/sandbox witnesses and SHA-256 digests. Stop for review; no full diagnostic, completion/failure cohort or native launch follows automatically.

## Input pins and pending decisions

Capture test SHA: `5c07a3858e74adbc73d504a9caa68381bcbf93816a410584de57d0715fa23639`; capture source `b2e0f065a7a21b36bf015d558b8ca4e8aba15b01b8ffa8ab4359827b68cfad16`; shared-registration source `c674f2bea05d20d744871fe8839ee634527045e8fef23c027548afbc1b6ce233`.

Failed-attempt log hashes: mkdir `68809707296cea5f24105e5c7ab94253ca260d53119ebf54dd48e7d46bfe6358`; user-config denial `a5cbb3a3f06d0dae32d2344f0f6ec13b978c1102c5fba91196cd53069f01fb76`. These were read only. No message was sent to the other worker or relayed through another channel; its messaging restriction remains respected.

Current supervisor SHA: `f7426c2fd0560d5f8bf84935c083fcfe6908327213db1023af8607167eb88d07`; driver `8124db6c15367e177f01590fb7742c89c5b912a8306a93b665610a1ecda4aa8d`; child gate `c2c43d76a4fb52b5a03a1eb9eae3d8d997b84a9ec062cdc16b01bc3a16754be1`; M composer `007667a8e1faac01411edff8a34a16bf036a732617f15c8f35b8ea54a4098cc0`. A future adapter changes its own pin and requires a new reviewed source/contract; do not reuse old metadata.

Pending: final AST commit/review or explicit decision to test A alone; independent approval of A and fixed-node adapter; exact integrated S and private-composition permission; lead runtime-slot release and acceptance of these caps. Production protected API installation and D128 scanner approval remain separate owner decisions. A passing software readback canary would not close the stale-reservation or later native acceptance gates.
