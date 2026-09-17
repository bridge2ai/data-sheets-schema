# Native command controls review, 2026-09-17

Scope: #2035 and item 1 of #2041. The other two #2041 items already merged
in #2017/#2022. This change requires a new generation condition; v10s remains
frozen and unlaunched.

The new preparer binds root manifest rules and inline Python programs to each
registered job. It reads both the rendered instruction and the selected
executable playbook, binds artifact placeholders as Python string literals,
and supplies exact executable command spellings. Schema and term validators
admit arguments; the grounding, report and exclusive-write freeze programs
do not. The controller rebuilds this policy before credential access and
uses it for denial classification. It rejects missing, changed, widened or
legacy global policies.

The playbook's grounding display now prints the unpacked `kind` and
`identifier` explicitly. Its output is unchanged; removing the literal `*`
keeps the exact program expressible without a permission wildcard. Unknown
artifact placeholders and literal wildcard characters stop preparation.
The runtime binary can be selected explicitly and is still resolved and
hash-pinned, avoiding accidental use of a retargeted installation alias.

## Adversarial checks and correction

The first full runtime probe denied all six required Python command forms
even though the unit tests passed. Filed #2045: the pinned CLI's
`--allowedTools` list parser splits complex programs after inner parentheses.
Permissions now use inline JSON settings, with the tool-rule envelope escaped
separately from shell quoting. The production controller and probe use the
same delivery helper.

The corrected probe ran the actual Claude Code 2.1.272 binary, SHA256
`195e24e8e1f9bf46f1eaee72d434a33e18f9f5796f29a6348a00d16c5f8aee75`,
with a local scripted provider. All **15 cases passed**: six required Python
forms, two selected-manifest forms, a roster command without the root option,
and a registered module ran; a non-roster `runs select`, a different manifest,
arbitrary Python, an altered program and another record path were denied.
The source manifest contains a space and apostrophe. CLI and validator
modules are synthetic stubs; the freeze performs actual exclusive writes.
This tests admission, not the scientific behavior of the validators.

The [public probe summary](native_permissions_2035_2041_probe_2026-09-17.json)
binds the complete local policy and transcript. The probe made **zero real
provider requests**. Reported runtime token/cost fields in the private
transcript describe scripted responses, not charges to the study allocation.

Validation: **170 affected tests passed** across command policy, launch,
proxy, evidence and selected-playbook tests. A subsequent unknown-placeholder
regression brought the policy suite to **13 passing tests**. CI runs that
suite in the existing single native-controls lane; no matrix expansion.
The controller regression proves a widened policy fails before credentials
or creation of an attempt directory. Program matching parses syntax without
executing candidate code. Required programs denied by the runtime are
classified as prescribed and disqualify the attempt; modified programs do
not receive that classification.

This was a Codex review and local runtime verification. No completed Opus
review or independent scientific acceptance is claimed.

## Limits and preservation

The policy fixes the root `--manifest` escape to arbitrary subcommands and
the unrestricted `-c` grant. Broad file-tool grants and arguments to allowed
CLI/module/validator commands remain; this is not a filesystem sandbox.
Acceptance must still inspect successful calls, file paths and full tool
history as well as denied calls and the controller receipt. The effective
system prompt, including job-specific command guidance, now has its own hash
in the started receipt.

The v10s registration remains
`30d6d5a49a2c96518bbe6363b59ae834e64241f4cf1062048a907ee67ba07cc5`,
its overlay remains
`8678ed0924b4571be3d1de9a792eb2746af5627574eacd2bf9b63415972b493e`,
and its pending readiness record remains
`997e49a88e76b7c3ef119e8acf5d8568aca1c4f4cc98d000e26baf326eb7ac36`.
All three hashes were checked after the edits. No historical output,
accounting record or launch receipt was edited. #1801/#1815/#1816 still
require fresh unchanged-canary acceptance; these engineering checks do not
close them.
