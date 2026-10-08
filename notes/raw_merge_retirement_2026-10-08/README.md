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
help/usage behavior. Validation is pending the root agent's serialized test run;
no tests or applications were run while implementing this change.

#4594 remains open for default Dataset mapping construction/disposition and its
five retained-input replays. #2915 and its scientific, comparison/publication
and held figure obligations remain open. No historical record, source bundle,
protected worktree, scientific label or coverage claim is changed.
