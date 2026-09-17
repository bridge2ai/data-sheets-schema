# Native command admission review, 2026-09-17

The registered lookup grammar was previously enforced by the terminal audit.
Runtime permissions also admit some shell reads, so a command outside that
grammar could execute before the audit rejected it. Issue #2055 adds a parent
`PreToolUse` callback using the same classifier before Bash execution.

The callback uses the native SDK JSONL control channel. It keeps safe mode,
restricted mode, isolated configuration and the existing capability grants.
It does not enable ordinary settings hooks or install an SDK dependency.
An admitted command still needs the runtime's own permission. Denials retain
their existing classification; no attempted command is rewritten.

## Review and corrections

Codex reviewed initialization, callback identity, command and working-directory
binding, deadlines, shutdown, transcript preservation and terminal evidence.
This is implementation review, not independent scientific acceptance.

Two findings were filed as #2056 and corrected: a blank command remains a
non-disqualifying denial, and shutdown retains unread native pipe bytes before
freezing the transcript. The final pass also rejects a terminal event before
initialization, preventing a subsequent acknowledgement from sending a prompt.
Regression tests exercise each correction with local child processes.

The initialization and decision records bind the policy hash and retain the
exact native callback and parent response. A missing, duplicate, malformed,
contradictory or timed-out decision prevents completion. The terminal audit
matches every Bash call to one decision and one result. The two-second parent
classification deadline precedes the three-second native callback timeout.

## Verification

- 215 focused tests passed in 32.15 seconds, covering native launch, proxy,
  evidence, command policy, lookup grammar, control channel and CI sharding.
- The actual pinned Claude Code 2.1.272 executable passed all 27 scripted
  command cases with broad project settings present and with settings absent.
  Its SHA-256 is
  `195e24e8e1f9bf46f1eaee72d434a33e18f9f5796f29a6348a00d16c5f8aee75`.
- The final broad-settings probe reconciled all 27 control decisions and
  preserved compatibility with native transcript observation. It includes
  permitted helpers and lookups, blank commands, compound commands,
  multiple `sed` print ranges, unrelated files and modified Python programs.
- Three additional pinned-runtime probes injected a stalled classifier,
  an exception and a malformed decision before a permitted snapshot helper.
  Each stopped with the expected reason, no tool result, no snapshot files
  and no unfinished proxy handlers. Physical file traversal included ignored
  files when checking for unintended snapshot creation.
- All probes used a scripted local provider: zero real provider requests.
  The [compact probe results](native_pretool_2055_probes_2026-09-17.json)
  retain case outcomes and evidence hashes; full neutral evidence is archived
  locally. CI includes the new tests once in the existing native-controls job.

The [official hook documentation](https://code.claude.com/docs/en/hooks#timeouts)
distinguishes ordinary hook timeouts from SDK callback timeouts. The actual
pinned-runtime probes establish the selected mechanism's behavior here.

## Limits and condition boundary

This is a Bash conformance control, not a filesystem sandbox. Helper arguments
and `Read`/`Write` grants remain broad. Actual artifact targets, ordered source
reads, receipt timing, required checks and source entailment still require
independent review. These probes do not establish generation quality or
repeatability.

Historical registrations and verdicts remain unchanged. The new control code,
policy version 3 and revised execution guidance require a fresh registration,
review, successful merged-head CI and a new launch instruction. This change
does not accept a scientific canary or expand the cohort.
