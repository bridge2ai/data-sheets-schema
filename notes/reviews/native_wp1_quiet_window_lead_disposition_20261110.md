# WP1 quiet-window plan: lead disposition

2026-11-10, 06:18 UTC. Read-only review; no native code or test execution.

The AGY2 drafts identify the correct four inherited lock checks, but **v1–v3
are not accepted implementation recipes**. Preserve them and their reviews in
`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/`.
The reviewed v3 is `native_wp1_quiet_window_adapter_plan_v3_2026-11-10.md`,
7,281 bytes, SHA-256
`400f4b638891c26a71e2f5748ed06bc34c7ff1a0fb191f7fb67602a2045e7a48`.
The author was still shortening v3 during the first reads. Independent
pre-publication review caught the changing identity. After the author
acknowledged that editing had stopped, the lead rechecked this retained
version; the findings below remain present. Earlier draft hashes do not
identify the retained final file.

V3 still names nonexistent `kill_group`, `collect_descendants` and
`terminate_pids` helpers. The inspected partial supervisor instead contains
`_SandboxHandoff.kill_detached` and a local `kill_owned`; its outer integration
is unfinished. V3 also resolves the interpreter executable before finding its
environment, which can discard a virtual-environment prefix. Existing
`supervised_main` and `dependency_site()` derive and validate the prefix from
`Path(sys.executable).absolute()`. Reuse that actual contract. Earlier missing
environment-variable, session-ID and child-argument assumptions are recorded
under issue 5757; cleanup defects are under 5760, parent gate 5755.

The following requirements replace the drafts' speculative wiring. The native
owner should resolve the two remaining integration details in source, after
the current approval stop is lifted; another speculative plan rewrite is not
needed.

1. Keep the existing inherited runners unchanged. Adapt their M import, C/A
   entry and A pause checks only inside the WP1 helpers. Canary mode still
   refuses every existing quiet lock. Measured modes must also refuse an
   existing foreign, stale or symlink lock without modifying it.
2. The outer supervisor creates one exclusive lock per measured arm **before**
   host qualification. Record owner identity, UTC start and bounded expected
   end from initial acquisition, including the qualification phase. Preserve
   the existing quiet-host thresholds and settling/sample requirements. Use a
   separate bounded qualification interval; one failed qualification aborts.
   Start the unchanged 900-second arm budget only after qualification passes.
3. Load dependencies using the existing validated physical environment
   contract. Record and verify child identities across the real process tree:
   outer supervisor, its new-session supervised child, driver, detached worker
   and child-check. Same-session equality is insufficient. Carry a validated
   output identity through both child spawns; child-check has no `argv[2]`.
   The exact witness carrier remains an implementation detail requiring a
   focused test. Environment text alone is not ownership proof.
4. A matching owned lock may pass the four inherited checks. A path adapter
   must support `os.PathLike`. Loss or alteration of the lock raises into the
   existing bounded child cleanup; there is no `OwnedProcesses.terminate`
   API. Preserve the lease-loss reason in the outcome.
5. Integrate release with the completed L2 detached-child ownership mechanism.
   Verify cleanup before removing only the same owned lock. Normal exit,
   interruption, deadline and qualification failure all need explicit handling;
   `os._exit` does not run `finally`. Unknown cleanup must remain uncertified,
   never an apparent success or permission to remove another owner's lock.

First finish and review L1/L2 and the permitted small observer smoke if the
owner approves. Then implement this adapter as a separate bounded unit, with
cheap process/lock fixtures covering both refusals and the real spawn topology.
No composition, timing arm or provider call is authorized by this note. A
passing fixture is not the required same-path canary or a generation result.

Source inspected: native checkpoint `e3e9cfa12` plus frozen partial supervisor
SHA-256 `8719d1c12e8a0c0eed03ea8f484a2856f34ab5d6d7589f4e7f0d5ef8492277dd`
and driver `2e190561b5f7c8658d3cb424d69059d315e96b7316f196e08663c3a22f4018d6`.
