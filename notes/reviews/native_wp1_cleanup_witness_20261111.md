# E1 / #5746 actual full-runner cleanup witnesses — 2026-11-11

The external helper `scripts/adhoc/verify_native_wp1_cleanup_20261111.py`
launches the unchanged genuine fixed canary on frozen native source
`01bdcb22dad66da1a167595251b23e6352c97ab7`. It does not import or patch the
generation/runner code, substitute a toy worker, change the 60-second runner
limit, or borrow a quiet-window lease. One scenario is admitted per invocation,
with independent source review before execution and artifact verification
before moving to the next scenario.

The existing private composition is reused only after checking its manifest,
contract, restored configuration/backup and exact source/interpreter pins.
Each invocation retains a fresh config backup, reconstructs the exact prior
configured bytes, verifies their pinned digest, and restores the original
bytes before its terminal report. Prior manifests and runner outputs are never
rewritten. No full recomposition or installed dependency copy occurs.

The signal trigger requires the actual fresh `network.json` with denied bind
and EPERM, the corresponding live detached worker observed under the directly
owned outer process, exact worker command from `plan.json`, interpreter identity,
PID=PGID=SID, the unique genuine inner supervisor/driver ancestry, unchanged
60-second deadline, and no completed test/worker artifacts. Creation identities
are retained and rechecked before signals. Any completed-test race makes the
trial inconclusive rather than a successful failure witness.

1. `sigint`: signal the direct outer process after sandbox admission.
2. `driver-loss`: kill only the exact owned driver while its detached sandbox
   is live; leave the other genuine supervisors and their cleanup logic intact.
3. `deadline`: stop only the actual detached sandbox worker. Keep the existing
   earlier cutoffs and 60-second outer cap. This can establish the layered
   deadline path, not execution of the outer hard-alarm handler unless the
   artifacts separately demonstrate that handler. No earlier guard is suppressed.

The external envelope has a 70-second cutoff and 75-second hard stop. The
normal terminal witness requires unsuccessful runner certification, recorded
admission/intervention, no external rescue, no remaining observed processes
or members of the owned sessions, and unchanged source/inputs/interpreter plus
restored config. External rescue, missing terminal evidence, incomplete census,
or failed restoration prevents verification. Hard stop may leave the exact
private config active; retained backups then require explicit recovery. This
is a software bound, not a kernel real-time guarantee.

Even successful negative witnesses do not certify never-observed descendants
that escaped their known sessions. They establish no quiet lease, release,
performance, general observer equivalence, native execution or production
acceptance. Do not close those separate gates from these results.

Independent source review found three draft helper defects under #5746, all
repaired before any invocation: preserve the identity-checked psutil Process
object through `send_signal` instead of reconstructing it after the check;
and require the real inner supervisor to report SIGKILL for the exact recorded
driver identity/command in the driver-loss case. An arbitrary unsuccessful
terminal result cannot stand in for observed driver loss. The final 75-second
handler now exits unconditionally without a fresh psutil traversal; rescue
stays within the earlier five-second cleanup reserve. Missing terminal evidence
never certifies cleanup and may require explicit retained-state recovery.

First actual `sigint` attempt at tools `447b8a28abaf4cff49b358b96aabd0b49128bbbc`
refused before injection: `AccessDenied: (pid=1)` while inspecting command lines
above its owned outer ancestor. Its result is retained under
`scratch-native-u1u3/u3m/cleanup-witness-e1-cleanup-sigint-447b8a28abaf/`,
SHA-256 `10215d2f7defaa665d66c36f19e3998201ef6f0dcae84135186a6cc53cf1a8b4`.
The external helper rescued only observed owned processes; final owned-session
census was empty, config was restored, source/interpreter/inputs unchanged.
Elapsed 9.214230458019301 seconds; no injected SIGINT or scenario pass.
The narrow correction truncates ancestor command inspection at the verified
owned outer identity. This retains the ancestry and exact-command checks and
avoids querying unrelated launchd/shell ancestors. No prior evidence is altered.
