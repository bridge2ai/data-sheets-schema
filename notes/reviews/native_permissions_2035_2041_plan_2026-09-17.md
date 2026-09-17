# Native permission follow-ups, 2026-09-17

The active goal remains: fix and verify the shared guidance for #1801,
#1815 and #1816; register a new condition for both generation arms; accept
the API canary before the matched agentic canary; expand only after review,
preserving every historical output. The preceding assessment turn identified
the next action but did not change implementation state.

## Immediate work

1. Resolve #2035 and the remaining part of #2041 together. Build permissions
   for each registered job, fix the manifest path, remove arbitrary Python
   execution, and include the validators delegated to the executable
   playbook in the denial classifier.
2. Exercise the permission rules with the pinned Claude Code 2.1.272 binary
   and a local scripted provider. Check legitimate commands, different
   manifests, non-roster commands, modified programs, quoting and multiline
   programs. These probes make no external model calls.
3. Run relevant controller and proxy tests, review the combined change, and
   record any findings as issues before preparing a pull request.
4. Prepare a fresh condition for both arms with the revised controls and
   unused output paths. Keep the merged v10s registration and its readiness
   record unchanged. Carry forward the existing sources, scientific
   instruments, preservation checks and cumulative accounting.
5. Reconcile the new condition with the active goal's API-first order and
   the separately approved native-first v10s registration. Bind any launch
   to the reviewed condition, exact merged code and successful CI; do not
   reuse v10s funding or readiness as a new launch receipt.

## Acceptance evidence

- A manifest-prefixed command outside the roster is denied by the runtime.
- An arbitrary or modified inline Python program is denied by the runtime.
- Required schema, term, grounding, report and original-freeze programs
  remain executable and are classified as prescribed when denied.
- Preparation and execution use the same job-specific command definitions.
- Historical registrations and generated outputs retain their bytes.
- Canary acceptance inspects actual tool history and unchanged original
  records, receipts, provenance, source grounding and reports. Passing the
  controls tests alone does not establish scientific acceptance.

Broad file-tool permissions and argument-bearing CLI rules are not a full
filesystem sandbox. This work must describe their remaining limits plainly.
