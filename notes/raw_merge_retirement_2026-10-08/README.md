# Unsupported raw RO-Crate merge retirement

[#4593](https://github.com/bridge2ai/data-sheets-schema/issues/4593) permits
explicit retirement of the unsupported raw merge command. `d4d rocrate merge`
now reports a clear nonzero Click error before repository/helper setup, merger
import, crate-content reads or output writes. Its legacy arguments and options
remain recognizable; normal Click argument checks and `--help` still work.
Inputs and existing outputs are preserved.

The previous command promised merged RO-Crate JSON but constructed a
Dataset-producing merger without its required mapping loader, then called
methods that class does not define. Its only positive CLI test supplied a
fictional merger API. That test is replaced with a real refusal/preservation
control.

This change does not redirect raw merging into Dataset transformation or the
separate graph-concatenation helper. Restoring raw merge would require explicit
policies for relative identifiers and blank nodes, root/descriptor ownership,
contexts, conflicting values/lists and source provenance. It does not invent
those policies or identifiers. The separate `transform --merge` operation and
legacy mapping table are unchanged.

The reference search included ignored and hidden files. Active advertisements
in `docs/cli.md`, `CLAUDE.md` and CLI help now explain retirement. Historical
root-policy review notes remain evidence of the earlier finding.

Focused controls cover real CLI refusal, primary-path aliases, new and existing
outputs, output/input aliases, symlinks and hard links, directory sentinels,
malformed/undecodable input bytes, blocked content opens/producer imports and
help/usage behavior. All **66 tests passed** across four modules: 27 existing
RO-Crate CLI cases (including the replaced fake-merger test), 12 new retirement
cases, 17 transform mapping-selection cases and 10 adversarial mapping-selection
cases. There were no failures, errors or skips. JUnit records 13.560 seconds;
the coordinator's console reported 13.59 seconds and 14 dependency deprecation
warnings. No provider, native or real-project replay was run for this change.

The tested commit is `9eefd41b8e0bdb731a3ab86d0f5c55d2ced4cc7c`, tree
`bc845b160dce1a7a87134d4eb318a02595e40638`.
[validation.json](validation.json) records the exact module counts, invocation
with private path prefixes replaced by roles, and nine file pins checked
against both the tested commit and working bytes. These include the changed
production module, all four tested modules, the two active documentation files
and declared dependency files; they do not attest the complete runtime or
installed dependency versions.

The retained external JUnit file `raw-merge-retirement-tests-01.xml` is 11,084
bytes, SHA-256 `5d1fd129724c5c29c4ca7e3fcba66be35d6928a5234961371240d0880ffa4c77`.
Independent source review was clear after correcting the command-summary table
in the CLI documentation to describe retirement.

#4594 remains open for default Dataset mapping construction/disposition and its
five retained-input replays. #2915 and its scientific, comparison/publication
and held figure obligations remain open. No historical record, source bundle,
protected worktree, scientific label or coverage claim is changed.
