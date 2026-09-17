# Native lookup contract, 2026-09-17

Issues [#2051](https://github.com/bridge2ai/data-sheets-schema/issues/2051)
and [#2052](https://github.com/bridge2ai/data-sheets-schema/issues/2052)
concern the agreement between permitted lookup forms, runtime grants and
acceptance checks. The previous system instruction permitted only prescribed
helpers even though the runtime admits some built-in shell inspections.

## Resolution and review

Policy version 2 records exact registered read inputs and this job's output
directories. It describes a small grammar for `cat`, `grep`, `head`, `tail`,
`wc` and numeric `sed -n` windows, including pipes among those commands.
Quoted paths and regex characters remain data. Unquoted expansion, unregistered
paths, recursive searches, pattern files, follow mode, redirects, extra
commands and other sed programs are outside the grammar. Resolved output
symlinks cannot name an unregistered target.

The controller classifies executed Bash calls with the same function used for
denials. A command error alone is not evidence that execution was denied.
Missing, repeated, out-of-order or contradictory call/result evidence fails
validation. Known denials keep the maintainer's existing rule: a denied
prescribed operation disqualifies; a denied forbidden operation is listed.
Old policies do not gain lookup permission, and the new controller rejects
an overlay that does not rebuild exactly. The new module is an overlay pin.

The first expanded runtime probe exposed #2052: a plain-word grep was admitted
but an anchored regex was denied under built-in admission alone. Explicit grants
now supply the named lookup capabilities. Those grants are broader than the
instruction grammar; the grammar is checked after execution. Broad file tools
and helper arguments remain. This is not a filesystem sandbox, and actual
helper arguments, file-tool paths and phase ordering still require independent
review. The change does not alter factual input restrictions, source-review
instruments, required checks or the interpretation of historical attempts.

## Validation

Neutral fixtures cover quoted paths, literal regex metacharacters, numeric
windows, pipelines, unregistered files, output-directory symlinks, expansions,
redirects and mutations. Controller integration proves that a permitted lookup
can pass, a denied permitted lookup fails, and a nonconforming execution fails
even if its tool result reports an error. A contradictory successful result
cannot be hidden by a denial entry.

The affected policy, lookup, launch and receipt suites passed 172 tests with
17 API skips for native-only cases. After the explicit grant change, policy,
controller and CI scheduling tests passed 79 tests with the same 17 skips.
The four loopback shutdown tests require network access to their local fake
provider; they passed outside the network-restricted sandbox. New lookup tests
are included in the existing once-per-CI native lane.

The final pinned-runtime probes and their identities are recorded in
`native_lookup_2051_probe_2026-09-17.json`. They use neutral synthetic sources,
stub helpers and an in-memory provider. They establish observed tool admission
and command classification, not generation quality or scientific acceptance.

## Next condition

After review and required CI, merge these controls and register a new condition
for both arms with fresh output paths. Keep the frozen source bundles, schema,
profiles and evaluation instruments unless a separately identified defect
requires a change. Preserve every prior attempt and score. The order remains
CHORUS native, Kids First native, CHORUS API, Kids First API, accepting each
unchanged canary before the next. A new merged-head launch instruction is
required; this engineering PR does not launch or retry a scientific canary.
