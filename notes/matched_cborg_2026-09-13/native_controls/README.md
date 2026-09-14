# Native generation controls — unexecuted draft

These files are preparation for the agentic canaries. They are not part of the
approved API transport. The former draft overlay is preserved in Git at
`3f5f909ac:notes/matched_cborg_2026-09-13/native_controls/overlay.json`.
The first API canary
failed; no launchable native overlay is supplied for that condition. A fresh
source/instrument registration is required before freezing another overlay.
No scientific native generation has run. The controller refuses to start
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
