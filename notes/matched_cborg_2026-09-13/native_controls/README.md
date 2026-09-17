# Native generation controls

## Current controls, 2026-09-17

Every launch requires an immutable source/instrument registration, a reviewed
native overlay, exact-commit CI and acceptance of preceding canaries in that
registration's order. The older observations below describe the initial
implementation. Native v10q and v10r subsequently ran and stopped; neither was
accepted. The merged [v10s registration](../../matched_cborg_2026-09-17_v10s/README.md)
has not launched and retains its original controls in its pinned checkout.

The #2035/#2041 follow-up replaces global Bash rules with a policy for each
registered native job. Root `--manifest` rules name the selected manifest and
a roster command; inline Python rules name only programs from the registered
instruction and its executable playbook, with artifact placeholders bound to
that job. This includes schema and term validation, grounding, report checks
and the original freeze. The controller rebuilds the policy before credential
access, uses that same policy to classify denials, and supplies the exact
command spellings as registered execution guidance. Its receipt hashes the
effective system prompt including that guidance.

Permissions are passed as an inline JSON settings array. The pinned CLI's
`--allowedTools` list parser splits complex Python rules (#2045). A scripted
local-provider probe exercises the actual runtime, successful required
commands and forbidden programs/manifest selections:

```bash
PYTHONPATH=src:notes/matched_cborg_2026-09-13:notes/matched_cborg_2026-09-13/native_controls \
  python notes/matched_cborg_2026-09-13/native_controls/probe_native_permissions.py \
  --claude-executable /absolute/path/to/the/pinned/claude \
  --output /absolute/path/to/a/new/probe-directory
```

The probe uses synthetic sources and stub validator/CLI modules, makes no real
provider requests, and tests real exclusive writes for the original freeze.
It establishes permission behavior, not scientific quality. Broad `Read` and
`Write` grants and argument-bearing CLI/module rules remain: these controls
are not a filesystem sandbox. Actual tool history still needs acceptance
review. The new policy requires a fresh registration and overlay; it does not
rewrite or authorize any historical condition.

The listed rules are not the complete effective Bash permissions. Claude Code
also admits built-in read-only shell commands, including `grep`, `head` and
`wc`, under `dontAsk`, as its [permission documentation](https://code.claude.com/docs/en/permissions#read-only-commands)
explains. The registered instruction is a behavioral requirement; it does not
remove those runtime permissions. Policy version 2 explicitly permits a small
read-only lookup grammar for registered inputs and this job's output files.
It allows `cat`, `grep`, `head`, `tail`, `wc` and numeric `sed -n` line windows,
including pipes among these commands. The appended command guidance lists
the supported options. Shell expansion, unregistered paths, recursive searches,
pattern files, mutating options and other shell forms are excluded. These
lookups do not replace ordered chunk reads, receipt writes or required checks.

Explicit grants provide those lookup capabilities: built-in admission alone
does not admit every supported regular expression. The grants are broader
than the lookup grammar and do not enforce file boundaries before execution.
The controller reviews every observed Bash execution with the shared command
classifier. A nonzero exit does not prove that nothing executed, so those calls
are included. Actual permission denials retain their separate classification;
a denied permitted lookup disqualifies just like a denied prescribed helper.
Missing or ambiguous execution evidence prevents acceptance. This remains a
conformance check rather than a filesystem sandbox. Helper arguments remain
broad; their actual manifests and artifact targets, file-tool paths, phase
ordering and source entailment still require independent review. Historical
registrations retain their old policies and verdicts (#2051).

The probe includes
read-only shell cases alongside the helper and denied Python/manifest cases.
Run it with `--project-settings-mode absent` to observe admission without
project settings, and with the default `broad` mode to check that broad
project grants do not widen the tested Python/manifest permissions. Use a new
output directory for each run. Scientific acceptance still inspects actual
successful calls, read targets and denied calls; a permission grant alone
does not establish instruction adherence (#2049).

## Initial observations, 2026-09-13

These files are preparation for the agentic canaries. They are not part of the
approved API transport. The former draft overlay is preserved in Git at
`3f5f909ac:notes/matched_cborg_2026-09-13/native_controls/overlay.json`.
The first API canary
failed; no launchable native overlay is supplied for that condition. A fresh
source/instrument registration is required before freezing another overlay.
At that date no scientific native generation had run. The controller refuses to start
without a separate immutable overlay, exact review/CI receipt and acceptance
of all preceding canaries from the base registration.

The draft sends every native model request through a loopback transport that
uses the base registration's common $200 sequence ledger and cumulative $5
attempt cap. The child receives a local token, not the CBORG key. Original
requests and streamed bodies are retained. Incomplete or unaccounted responses
stop the attempt. A fixed CLI session name avoids title-generation calls in
the offline probe; serialization and accounting still cover any auxiliary
requests that occur.

Twenty-three offline transport and launch tests pass, including concurrent
admission (#1766), shutdown during an active stream or token count, no late
evidence writes after bounded cleanup (#1768), and exact executable identity
despite a same-version alias retarget (#1769). The controller closes admission
and terminates the child process group before proxy cleanup. The installed CLI
2.1.270 completed a
scripted read, write and Python-helper probe with no tool permission denials;
all four responses came from an in-memory fake, and no real provider was
contacted. Its reported native limits were a 200,000-token context and 64,000
output tokens. Those differ from the CBORG catalogue's route maxima and must
be stated in the native overlay, with any compaction observed separately.
CBORG also accepted a non-generating token-count request for the synthetic
native prompt and tool schema (466 input tokens). These software checks do
not establish generation quality or live generation compatibility.

The repaired launch path also completed a new four-request fake-provider
probe with zero unfinished handlers; its evidence inventory is in
`offline_shutdown_probe.json`. This is software verification, not generation.

Still required: independently review a fresh native overlay (including
system prompt, permissions, runtime binary and controller hashes), relevant CI,
and a passing CHORUS API acceptance. Do not invoke this draft as a shortcut
around those gates.
