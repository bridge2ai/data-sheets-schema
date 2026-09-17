# Native read-only command review, 2026-09-17

Issue [#2049](https://github.com/bridge2ai/data-sheets-schema/issues/2049)
concerns the distinction between an explicit Bash permission list and the
runtime's effective permissions. Claude Code documents built-in read-only
commands that can run without approval. Its `dontAsk` mode does not turn the
explicit list into an exhaustive list of admitted commands.
[Vendor documentation](https://code.claude.com/docs/en/permissions#read-only-commands).

The probe now includes a `grep | head` pipeline and `wc -l` against its own
synthetic source. It can run with no project settings or with the pre-existing
broad-project-grant fixture. These additions document runtime behavior; the
production controller, command policy, prompts and registered conditions are
unchanged.

Both runs on the pinned Claude Code 2.1.272 binary passed all 17 cases: the
prescribed Python programs, manifest and CLI cases, and read-only commands
were admitted; the five negative Python/manifest/roster cases were denied.
Each run used 18 scripted local-provider requests and zero real provider
requests. Neither run left proxy handlers running or reported a proxy failure.
The [probe summary](native_readonly_2049_probe_2026-09-17.json) records the
binary and script identities and each observed result. Complete synthetic
request and transcript evidence is retained locally.

Review checked that the absent mode creates no project settings and that the
default preserves the earlier broad settings fixture. Both modes use a fresh
CLI configuration directory and the same controller launch options. The
positive cases require successful tool results, and the negative cases require
observed permission denials. The result does not prove all read-only commands
are admitted or establish a filesystem boundary. Scientific acceptance still
requires inspecting actual commands, targets and instruction adherence.
