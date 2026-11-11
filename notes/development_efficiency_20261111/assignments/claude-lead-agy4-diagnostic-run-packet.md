# AGY4 assignment from the Claude lead: the exact command packet for the one diagnostic run

Track: native (not on the API route). Read-only. You write a packet; you do
not run anything in it.

## The owner said yes (D132, 2026-11-11T16:11:12Z, in `data-sheets-schema/notes/coordination/STATUS.md`)

The owner approved your proposal from `handoffs/agy4-cpu-diagnostic.md` §7:
**one** existing `cpu-monitoring` run against the existing contract
`scratch-native-u1u3/u3m/wp1-contract-382f0dfd1ce8.json`, started only when
the 1-minute load per CPU is below 2.5, followed by the reviewed
configuration restoration. No retry, no new source identity, no provider or
model call. The lead will run it. A run that hits a setup error is not
repeated, so the commands must be right the first time.

## What the lead needs from you

Reconstruct, from the retained records only, the exact sequence that produced
`scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111`
and what must differ for a second run. Sources to read (all read-only):

- that directory's `plan.json`, `pytest-command.json`, `bootstrap.json`,
  `wp1-harness.json`, `u3m-harness.json`, `wp1-quiet-lease.json`,
  `host-load.json`, `outcome.json`, and the sibling `.outer.json`,
  `.outer.log` and `.supervisor.json`;
- `composition-382f0dfd1ce8/composition.json` and `config-restored.json`, and
  `tree/.git/config` beside `tree/.git/config.bak-u3m-20261109`;
- `cleanup-wrapper-382f0dfd1ce8-20261111/started.json` and `result.json`;
- `capture-recheck-382f…once.json` and `wp1-contract-382f0dfd1ce8.json`;
- the tool scripts those records name (path and sha256), in the worktree the
  records name. Hash each script file and compare with the recorded hash.

Answer these, each with the record and field it comes from:

1. **The launch command.** The full argv of the outermost process that was
   run for the interrupted diagnostic (interpreter, flags, script, every
   argument), its working directory and its environment requirements. If no
   record holds the outermost argv, say so and give the innermost recorded
   one, marked as such.
2. **The configuration arming.** What exactly differs between the armed
   private Git configuration (sha256 `8a96cf34…`) and the restored one
   (`95a1f7d1…`): which tool writes the armed bytes, with what command, and
   what the run needs it for. Whether the run can start with the restored
   configuration as it is now.
3. **The restoration.** The exact command of the reviewed cleanup wrapper
   (helper sha256 `4a5a483d…`), what it writes, and whether its output
   directory and `config-restored.json` are write-once (a second restoration
   would then need a new output name: say which).
4. **Once-only claims and names.** Which files make a run refuse to start
   again (for example an existing output directory, a `.once.json` claim, a
   lease): for the `cpu-monitoring` kind specifically. Propose the new output
   name for a second run and show that nothing with that name exists.
5. **The load gate.** Whether the tool itself reads host load and refuses
   above some bound for this kind, or whether the gate is only the operator's
   check. Give the file and line.
6. **What a good result looks like.** The files that must exist afterwards
   (the two `phase-metrics` JSON files, `pytest.xml`, `origins-after.json`)
   and the fields the lead should read first, including the diagnostic's
   result value and the reservation boundary against the 210-second target.
7. **Anything that makes the run unsafe to start now**, such as a changed
   tool hash, a missing dependency link, a stale lease, or a claim file.

## Rules

- Read-only. No run, no import of project code, no write outside this notes
  directory and `codex-development-efficiency-20261111/tmp/diagnostic-packet-20261111/`.
- Every path, hash and argv in the packet is copied by a script from the
  record that holds it, not typed. Put the script in
  `codex-development-efficiency-20261111/scripts/adhoc/` with the usual
  header, and show the command you ran. Where you state that something does
  not exist, say how you searched (include ignored files).
- Mark each statement as read from a record, read from source code, or your
  inference.
- No at-sign handles.

Write `handoffs/agy4-diagnostic-run-packet.md` in this notes directory, print
its path and SHA-256, and stop.
