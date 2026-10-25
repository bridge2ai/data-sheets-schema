# Default native generation PR series — 2026-10-25

Base: cached `origin/feat/v10-preflight-scripts`,
`7c1002caeb776ccb0caebb474e22e5558b7b9602`. Offline: no fetch, push, GitHub,
provider, real executable probe or launch. AGY publishes; Claude reviews.

## Unit 1: immutable protocol, selection and rendering

Branch `codex/n2-1-protocol-selection`. Exact archived protocol, evidence,
selection, rendering and native policy bytes are recovered from the retained
N1 trial; its owner modules are excluded. Shared scientific asset pins already
match the base's reviewed R9 files, which is necessary to test this unit at its
own head. No prompt text or canonical registry was changed.

Inherited dependencies are the base's schema/profile/resource readers,
`api_runner.RunSpec`, and existing native runtime registration. The added
logical-schema path validates every captured occurrence and does not consult
live paths during rebuild. The API caller dispatches only after strict native
validation; `shared_generation.py` remains unchanged. Ordinary API routes keep
their selector. Native execution is still refused by the API runner and has no
controller until the next unit. This unit is a foundation, not launch acceptance.

The reconstruction helper and exact source inventory are
`scripts/adhoc/recover_native_n2_unit1_20261025.py` and
`notes/native_n2_unit1_recovery_2026-10-25.json`.

Independent read-only review found no material blocker. The original private
API-selector assertion was moved to the actual public native construction
boundary: all ten malformed selections still refuse, before API selection.
Additional tests prove native construction/replay avoids that API boundary and
ordinary construction retains it. Lexical registration tests belong to unit2,
where their registration dependency exists; they were not silently skipped.

Exploratory validation history is retained: the first roster had a collection
error from that not-yet-delivered registration test; the next native run had
159 passes and one obsolete boundary assertion failure. After the caller-boundary
regressions, all 235 cases passed, but the session correctly exited 1 because a
parallel documentation addition triggered the repository's notes-directory
guard (#3772). That run is not a passing acceptance run. The source is now
frozen for a fresh test run at the committed unit head; final results and head
are recorded by the orchestrator-facing STATUS log and subsequent handoff.

## Remaining units and dependencies

2. Controller, receipt-to-record and captured replay/cache integration. Recover
   default-only modules from `a33d80d84c70cc9ee557f15d6e34fa73fc14f153`, before
   owner integration, with narrow patches onto the current base. Permission and
   subscription libraries must accompany registration/readback here. Preserve
   current base API fixes and whole-package authority checks.
3. Saved permission probe production, direct launch/subscription enforcement
   regressions and later independent binary/permission fixes.
4. Final alignment, declared differences, scanner disclosure and acceptance.
   Both default public-adapter fixtures retain the 900-second runtime deadline
   and existing 180-second recorder helper timeout.

The original fourteen profile1 failures remain deferred and unfixed on their
preserved lane. The fifteenth N1c failure, the default recorder timeout, remains
unresolved until fresh default-path evidence establishes completion. No prior
pass is relabeled as current-head acceptance.

The cached base records D32's decision but does not contain the later A12/A13
implementation. Unit4's comparison must distinguish this source base from the
intended final API stack. Later AGY integration/rebase requires its own tests.
