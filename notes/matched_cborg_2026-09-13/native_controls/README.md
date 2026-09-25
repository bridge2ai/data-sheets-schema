# Native generation controls

## Current controls, 2026-09-17

Every launch requires an immutable source/instrument registration, a reviewed
native overlay, exact-commit CI and acceptance of preceding canaries in that
registration's order. The older observations below describe the initial
implementation. Native v10q and v10r subsequently ran and stopped; neither was
accepted. The [v10s registration](../../matched_cborg_2026-09-17_v10s/README.md)
retains its original controls in its pinned checkout. v10v subsequently stopped
on the unregistered file read tracked in #2061; its original evidence is preserved.

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
It establishes permission behavior, not scientific quality. Argument-bearing
CLI/module rules remain: these controls are not a filesystem sandbox. Actual tool history still needs acceptance
review. The new policy requires a fresh registration and overlay; it does not
rewrite or authorize any historical condition.

The listed rules are not the complete effective Bash permissions. Claude Code
also admits built-in read-only shell commands, including `grep`, `head` and
`wc`, under `dontAsk`, as its [permission documentation](https://code.claude.com/docs/en/permissions#read-only-commands)
explains. The registered instruction is a behavioral requirement; it does not
remove those runtime permissions. Policy version 4 retains the small
read-only lookup grammar for registered inputs and this job's output files.
It allows `cat`, `grep`, `head`, `tail`, `wc` and numeric `sed -n` line windows,
including pipes among these commands. The appended command guidance lists
the supported options. Shell expansion, unregistered paths, recursive searches,
pattern files, mutating options and other shell forms are excluded. These
lookups do not replace ordered chunk reads, receipt writes or required checks.

Explicit grants provide those lookup capabilities: built-in admission alone
does not admit every supported regular expression. The grants are broader
than the lookup grammar. Before each Bash execution, a parent `PreToolUse`
callback now applies the same classifier used by the terminal audit (#2055).
It denies commands outside the registered grammar without changing them.
Prescribed commands still pass through the runtime's own permission check.

That check admits only the registered text, while the classifier matches a
program by its meaning and a roster command by its words. From policy
version 5 the callback also refuses, before execution, a prescribed call the
job's permission rules would not admit as written (#2369): a double-quoted or
reflowed program, a `$` variable or expansion, a line continuation, a
comment, a glob, or any spelling no rule matches. It mirrors the pinned
runtime's matcher: the rule envelope's escapes, exact rules, argument rules
that read runs of spaces as one, and the text the runtime parses as too
complex. The refusal names the registered spelling, and a refusal by the
controller does not disqualify the run, so the model can copy the spelling
and continue. Before #2369 such a call reached the runtime, which refused
it, and the refusal counted as a denied prescribed command. Preparation
refuses a registration whose own spellings the check would refuse.
Recorded version-4 policies, and the audit, evaluation and finalization
policies, replay unchanged. The check also ports the runtime's own checks on
the raw text before it parses (a backslash before whitespace, `=` or `~[` or
`<N-M>` forms, zero-width and other non-ASCII whitespace, a newline and `#`
inside an argument, the 10,000-character parse limit) and its brace check on
an argument joined from quoted pieces. That brace check is the apostrophe
refusal of #2308: an apostrophe splits a single-quoted JSON specification
into pieces, and so does `--opt='{…}'`. Text the runtime re-quotes from its
arguments before matching (a newline, or `$` and a name) is admitted only by
an exact rule. The review of #2398 found these checks by reading the pinned
binary; a newly pinned runtime must be checked the same way, and the offline
probes rerun, before registering. Not modelled: the parser's time and node
budget (#2398 review).

The same callback now checks `Read` and `Write` targets (#2061). File reads are
limited to the registered input/playbook closure and this job's output files;
writes are limited to output files. The provenance inventory of other agent
definitions does not grant read access. Paths are resolved against the registered
repository, including the runtime's conversion of relative paths to absolute
ones; other call arguments must match exactly. Links cannot escape the frozen
output roots, and hard-linked output files cannot alias pre-existing inputs.

Large Bash output may be saved by the runtime in its isolated configuration.
The parent permits Read of that exact file only after observing a prescribed
call and matching native result metadata in the current session's
tool-results directory. Its size and hash are recorded, checked before reading
and reconciled at completion. Source text mentioning a filename grants nothing.
The configuration directory itself is never made generally readable or writable.
This includes diagnostics from a helper's nonzero exit; the helper's success and
the procedure's stop rules are judged separately from file identity.

The callback uses the native SDK control protocol over JSONL stdin/stdout;
it does not load an SDK package or an ordinary settings hook. The pinned
runtime retains `--safe-mode`, `--restricted` and its isolated configuration.
Initialization must succeed before the generation instruction is sent. Missing,
ambiguous or malformed control messages stop the controller. A stalled
classifier stops after two seconds, before the runtime's three-second callback
timeout. The hook contract and policy identity are pinned in the overlay;
the started receipt records the policy hash. The parent preserves its control
exchange separately and retains the original native transcript, including
unconsumed pipe bytes at shutdown. Executed calls require matching decisions,
calls and results. The [vendor documentation](https://code.claude.com/docs/en/hooks#timeouts)
distinguishes blocking SDK callback timeouts from non-blocking ordinary hook
timeouts; the pinned-runtime probes verify the actual selected mechanism.

The terminal audit still checks every observed Bash execution. A nonzero exit
does not prove that nothing executed, so those calls are included. Every denial
is listed; a denied prescribed command disqualifies, while denial of an
unprescribed or blank command does not do so on its own. Missing or ambiguous
execution evidence prevents acceptance. Executed file calls also require matching
callbacks, decisions and results. Stopped receipts preserve their available
control audit. Helper arguments still require review: this is not a filesystem
sandbox. Actual manifests and
artifact targets, file-tool paths, phase ordering and source entailment still
require independent review. Historical registrations retain their original
policies and verdicts; these controls require a new condition.

A narrow exception records native input rejection before a callback (#2084).
For a `Read` with one string-valued `offset` or `limit`, the exact typed
validation error and error-only result must agree with the original argument,
unique call/result identity, prior session initialization and event order.
This records `input_rejected_before_callback`, without granting access or
inventing a permission decision. Any callback or conflicting execution evidence
prevents that exemption. A second narrow exception covers the runtime's refusal
to overwrite a file the session has not read (#2285): a `Write` with exactly
`file_path` and `content` whose result is exactly the
`<tool_use_error>File has not been read yet. Read it first before writing to it.</tool_use_error>`
wrapper and its `Error: …` plain text is recorded the same way, as
`input_rejected_before_callback` with `tool: Write`, `rejection: file_not_read`
and the literal target path, under the same identity, session and order
conditions. Other missing callbacks remain unexplained. Live
completion and retrospective review verify the same rejection evidence.
Transcript loading preserves physical line numbers; blank frames make history
uncheckable, and malformed or incomplete frames are rejected. The
[review](../../reviews/native_input_rejection_2084_review_2026-09-18.md) records
the offline checks. This change does not reinterpret or resume v10y.

The probe includes file reads/writes, symlink escapes and persisted-output
provenance alongside read-only shell, helper and denied Python/manifest cases.
Run it with `--project-settings-mode absent` to observe admission without
project settings, and with the default `broad` mode to check that broad
project grants do not widen the tested Python/manifest permissions. Use a new
output directory for each run. Scientific acceptance still inspects actual
successful calls, read targets and denied calls; a permission grant alone
does not establish instruction adherence (#2049).

## Transport probe, 2026-09-25

Audit27's ninth worker request returned HTTP 500 seven times at 272 to 277
seconds. CBORG's catalogue lists `stream_timeout: 270` for the Opus 5 routes,
and hidden thinking can delay a response's first byte past that. Claude Code
2.1.272 accepts `--thinking-display summarized`, which asks for streamed
thinking summaries (#2463). `transport_probe.py` tests whether that setting
gets a response through.

The probe resends one retained request once. It uses the source
registration's own transport, stall policy and response buffer, through the
registered native proxy. The only change is `thinking.display`. It records when
the response headers, first event, first thinking text and last byte arrived,
but keeps no text. It runs once per registration and never resends. A 5xx is
counted at its whole reservation. A row still pending afterwards is settled at
its whole reservation in a separate `reconciled_billing.json`, under the
maintainer's standing authorization, and the ledger is left as written.

The probe is a link in the lineage. Holding the sequence lock, it takes the
tip with a durable sequence claim and continues the tip's settled checkpoint
under the same caps. The next registration continues from the probe's
`result.json` `successor_continues_from`. An audit prepared from the earlier
tip fails at its sequence guard. Audits accept a probe predecessor only after
#2469.

```bash
PYTHONPATH=src:notes/matched_cborg_2026-09-13:notes/matched_cborg_2026-09-13/native_controls \
  python notes/matched_cborg_2026-09-13/native_controls/transport_probe.py prepare \
  --out DIR --source-registration R --source-request REQUEST_DIR --tip-checkpoint C \
  --sequence-state S --origin-registration O --authorization A
# review DIR/registration.json, then, with CBORG_API_KEY set:
... transport_probe.py run --registration DIR/registration.json --sha256 HEX
```

## Phase checks for renderer 13, 2026-09-17

Renderer 13 separates Phase 1 corrections from terminal Phase 3/4 failures
(#2067). The generator may correct its draft record and coverage receipt using
the registered sources, retaining every write and checker result. After a
full-record or receipt write, the first core derivation needs a fresh successful
strict receipt check, with no pending receipt check or write. The registered
receipt floors govern success; coverage and token-overlap diagnostics do not
all constitute failures. Operators preserve the measured artifacts instead of
repairing them after execution.

The parent observes the actual native calls and results. It stops a premature
core derivation before its execution callback, and stops when a selected
evidence check or source-review inventory fails. Ordinary Phase 1 receipt
failures remain correctable. The same reviewer is run on the final or stopped
transcript, so a later success cannot erase a terminal failure. Unprescribed
helpers remain subject to the existing denial classification; a denied help
request or compound command does not become a phase failure. The phase reviewer
uses the shared pure shell/program classifier; filesystem lookups remain in
the timed callback worker.

This check does not prove initial source-read/receipt order, schema/term
validation, original-freeze hashes, complete Phase 3/4 artifacts or scientific
support. Those retain their independent acceptance checks. Renderer 12 and its
stopped attempts remain unchanged. See the [review](../../reviews/native_phase_scope_2067_review_2026-09-17.md)
and [offline evidence](../../reviews/native_phase_scope_2067_probes_2026-09-17.json).

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
