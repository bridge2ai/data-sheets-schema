# Neutralised direct-arm canary fixtures for `self_disclaimed` (#3515)

`direct_v1/`, `direct_v2/` and `direct_v3/` hold the original record, final
record, audit and coverage receipt of the three direct-arm canaries (#2913's
acceptance replay in PR #3029), neutralised so they carry no study content.
`tests/test_self_disclaimed.py` replays them through `check_files`, the code
behind `d4d review self-disclaimed --original O --final F --audit A --receipt R`,
under every lexicon version, and pins the #3029 acceptance outcomes.

These are not records. They are the smallest inputs that reproduce the lint's
behaviour on the real artifacts.

## Source artifacts

The run data was never committed. It was read, not changed, from the direct-arm
execution worktrees on 2026-09-30:

| fixture | run date | file | sha256 of the source bytes |
|---|---|---|---|
| `direct_v1` | 2026-09-23 | original (`evidence/original_full.yaml`) | `926ff5c8035c5c879d3b65a88e9e6441dc70b5d8648b9c31302f1cb57470a573` |
| | | final (`{P}_d4d.yaml`) | `432ae9b2aa119071f5da5fd31e4672d45903f08527dedc2e22b685222cfaa146` |
| | | audit (`evidence/audit.json`) | `31eb21373d130e543593379efe835bc48fc096099eb0770ffb7c09ea88bc75ee` |
| | | receipt (`{P}_coverage_receipt.yaml`) | `82aaa0cd33d8092da0ca2892ad836c096d32bdf7705bd4e4cac175d75a2626e4` |
| `direct_v2` | 2026-09-24 | original | `fa137ac2ba0329b34ffa7d87eaa1f3828a62ca5fcaac7e7c983a902dcfb9fae8` |
| | | final | `8a740d32a6cd9c4f1799c1de690f83c2c9dfa9f033e0991109ac75157d4a75a6` |
| | | audit | `886cf0d86c42ac65381ac1f8197cdc87b04c01610db53f43d237b52d5ebddee4` |
| | | receipt (the 2026-09-24 label's) | `c32416dcbd38ebb685c848c7f3e69a1c84bbfd1d048ee1a5cc2ca4d7f8668194` |
| `direct_v3` | 2026-09-25 | original | `ec48427d3e169242871727e52c5bcd4a318a4cb337824f83940fdadab38ed229` |
| | | final | `d7de13f9b882e2708c0d5d50e143a7142707264c90b5c3ee5cf55359677e2557` |
| | | audit | `82faf9c77b27dc8c41f44d4497d6577e764581d9052ff69e0af8027bbc8413e0` |
| | | receipt | `b51ab43c504c3d8bdb591a8e83966f9c603accb7db81e75050041cce2a4a8487` |

## How they were neutralised

- **Records.** Only what the lint reads is kept: the registered containers
  (`creators`, `maintainers`, `data_collectors`, `instances`, `splits`,
  `variables`) and, in `direct_v2`, the `subsets` list that holds a nested
  `instances` container (its other entries are `Item <hash>` stubs, so the
  indices stay). In each member's narrative leaves, a sentence that matches
  no cue of any lexicon version is replaced by `Placeholder <sha256[:8]>.`
  (the hash of the sentence, so equal sentences stay equal and different ones
  stay different). Sentences with a cue are kept. Other strings longer than 80
  characters become placeholders, and integers are replaced by a hash of their
  value.
- **Names and study words.** Every person is renamed consistently across all
  four files, in full, in id slugs and in the reversed form. Each renamed
  word has the same length class as the original (at least four letters or
  fewer), because the lint uses a name's last word as a self-reference only
  when it has at least four letters. Institutions become `Organisation A`
  to `D`. The study name, its domain, e-mail addresses, the award number,
  the registry and the webinar name are replaced with neutral words.
- **Data descriptors.** The names and `instance_type`s of the instances
  (the study's data types), the variable's name and the data collectors'
  names and roles are replaced as whole values, one value by one
  replacement in every file (`Entry A` to `Entry N`, `Entry C kind`,
  `derived value one`, `Contributing centres`). The split's name ("Holdout
  test set for external validation") is kept: it is generic vocabulary, and
  its words are on the lexicon's qualifier axes.
- **Audit.** Every finding keeps its index, `severity`, `slot`, `record`,
  `review_paths`, `remove_relationship` and the `artifact`/`op`/`path` of its
  `original_full` evidence. Quotes, source evidence and prose are dropped.
- **Receipt.** Chunk ids and statuses are kept. Only the extracted pairs
  addressed to a person-role member are kept. Each snippet becomes a
  placeholder followed by the role-predicate words any lexicon version found
  in it.

The neutraliser is not committed, because its substitution table spells the
study content it removes. It was checked by running `check_files` on the
source artifacts and on these fixtures under lexicons v1 and v2. The two
outputs were identical: every flag, hit rule, class, leaf, guard,
out-of-scope reason, diff row, identity basis, finding index, check (b) flag
and count. Under v2 the scope, term and cue texts of every flag hit, guarded
match and out-of-scope match were identical too.
