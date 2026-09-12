# Schema digest cache freshness — 2026-09-11

Issue #942 left the digest caches keyed only by class and the caller's path.
After a schema rewrite, a long-running generator could keep the old slot
inventory, prompt text and fingerprint even though its shared SchemaView had
refreshed. Changing working directories also confused distinct files with the
same relative path, including a class's implicit default path.

Both caches now include the resolved schema path and content hash. Old revisions
of the same source are removed from these caches. Custom-schema display paths
and copied mutable return values retain their existing behavior. The rendered
text cache also includes the vocabulary pin's content; the vocabulary loader
reloads changed bytes. That resolves the vocabulary-cache portion of #946.

Review round 1 reproduced the same-size/same-timestamp rewrite and both relative
path cases against the old code. It also reproduced the stale vocabulary pin.
The related test run exposed #1256: a fixed 1 ms lookup budget rejected hashing
the current source. The replacement verifies reuse of the rendered inventory
without rebuilding or rerendering unchanged inputs.

Review round 2 checked default and explicit path resolution, restored schema
bytes, retained display paths, mutable-object isolation, both cache layers and
vocabulary-only changes. All 74 focused schema, cache, sync and provenance tests
passed. The current unchanged schema fingerprints and rendered lengths remain:

| Class | Digest MD5 | Characters |
|---|---|---:|
| Dataset | a91bad8b8eaf7c34b147ff5970474342 | 43582 |
| CoreDataset | dfb9f93caa70559638007035b1be9276 | 29991 |

Review round 3 addressed #946's remaining check-time races and retained views.
Four regressions demonstrated false success after merged/source/vocabulary
changes, and one extra view and two digest-cache entries on each stale retry.
The check now captures input bytes, rejects observed changes, and discards cached
rebuilds if sources change during the check.

Review round 4 found #1258: changing and restoring the merged file can defeat
an end-of-check comparison. The independent comparison digest now comes from
the preserved rebuild and a vocabulary snapshot, calculated in a short-lived
Python process. The parent caches only up to 32 digest strings, keyed by content,
displayed source and dependency versions. No temporary LinkML views remain in
the generation process. Known and custom schema display paths are preserved.

Review round 5 checked changed-then-restored files, custom relative/absolute
paths, child failures and timeouts, cache isolation and repeated stale checks.
All 97 focused tests passed. These checks do not lock external editors or promise
that a file cannot change after a completed check; the generation inputs must
remain stable for the run.

No schema, vocabulary, generation artifact or prior evaluation was rewritten.

The Codex plugin review then returned two material findings, retained verbatim
in `schema_cache_codex_review_2026-09-11.txt`: #1259's downstream slot-prompt cache
and #1260's separate hash/parse reads. Both are addressed. Shared views and the
digest/vocabulary caches now hash and parse the same captured bytes; relative
imports still resolve against the original source directory. Renderers receive
one vocabulary snapshot. Fitness contexts and slot specifications use the same
captured inventory and vocabulary, with specifications invalidated when that
instrument changes. Existing persisted judgements remain under their original
contexts.

Five snapshot regressions and four fitness regressions failed before the fixes.
All 150 focused tests pass after them, including an edit between fitness context
creation and prompt construction. The current full/core fingerprints and fitness
schema context remain unchanged. A follow-up plugin review checks the fixes.

The follow-up plugin review returned two further material findings, retained
verbatim in `schema_cache_codex_followup_2026-09-11.txt`. Issue #1261 demonstrated
that the generation digest deliberately truncates some nested ranges which the
fitness judge sees in full. Fitness judgements now carry an additional SHA256
of the complete captured slot specifications; their generation schema digest
remains separate. The real `DataSubset.total_size_bytes` integer-to-decimal
regression leaves the generation digest unchanged but refreshes the fitness
prompt, context and persisted cache entry. Legacy entries without the complete
specification identity remain on disk and cannot satisfy the new context.
The separate dated fitness-cache amendment preserves #919's earlier decision.

Issue #1262 demonstrated that the rebuild cache still trusted source sizes and
timestamps. It now hashes captured source and imported-module bytes, including
ignored files, and runs the generator against those same copies. Relative
imports outside the source directory retain their layout. LinkML package imports
were initially tied to installed dependency versions (the fifth plugin round
below also captures and binds their bytes); other non-relative imports fail
the preflight as unchecked because their bytes cannot be attested by this local
snapshot. The generator's temporary source filename is restored to the logical
source name so committed merged schemas still reproduce byte for byte.

Four source-snapshot regressions and the complete-fitness regression failed
before these fixes. Further tests cover parent-relative imports, source paths
with spaces and wrapped YAML, and retention/rejection of legacy cache entries.
The combined targeted run passes all 153 tests. Both real repository schemas
remain in sync, with the unchanged fingerprints and lengths above. The offline
cache audit confirms all 1,441 historical fitness judgements remain unchanged
and ineligible under the new context. A third plugin review checks these fixes.

The third plugin review, retained in `schema_cache_codex_third_2026-09-11.txt`,
found imported-file invalidation (#1265), discarded symlink aliases in rebuild
snapshots (#1266), and Unicode escaping in the restored source filename (#1267).
Six regressions failed against that revision. The cache identity now includes
the full transitive import closure. Views preload those captured definitions,
so LinkML never reopens their live files after hashing. Logical import paths
and separately resolved target identities preserve symlink behavior. Package
imports use the installed LinkML bytes; remote imports are explicitly refused
because a local snapshot cannot attest them. Source rebuilds preserve their
logical aliases and use LinkML-compatible Unicode serialization.

All 181 focused tests pass, including edits when LinkML starts parsing,
transitive imports, fitness memo invalidation, and real direct-versus-snapshot
generation for import aliases, root aliases and Unicode paths. The existing
full/core generation digests and complete fitness specification SHA256 remain
unchanged. A fourth plugin review checks the complete implementation.

The fourth plugin review is retained in
`schema_cache_codex_fourth_2026-09-11.txt`. Its three findings are addressed:
stable logical aliases coexist instead of evicting one another's pinned views
(#1269); captured metadata is normalized through LinkML's own metamodel,
including list-form prefixes (#1271); import resolution and lazy namespace
initialization follow the installed LinkML behavior (#1270). Four regressions
failed against the reviewed revision. Direct and captured views now agree on
both the imported specification and the namespace map after a prefix override.

All 185 focused tests passed, followed by 38 affected view/import/sync/fitness
tests after the final lazy-loader adjustment. A fifth plugin review checks the
complete branch before merge. No current generation digest, fitness instrument
hash or historical measurement changed in this compatibility round.

The fifth plugin review is retained in
`schema_cache_codex_fifth_2026-09-11.txt`. Issue #1273 reproduced a caller that
initializes namespaces before loading imports: a relative module's prefix
override could then select a different local file. Snapshots now capture both
supported namespace initialization orders and select the captured bytes using
the view's actual resolver state. An unavailable unselected alternative does
not reject a valid import closure. Inventory keys also include the stable view
identity so eviction and restoration cannot reuse another selection's inventory.

Issue #1274 reproduced an official LinkML URL available entirely offline via
`URI_TO_LOCAL`. Both snapshot paths now recognize these package aliases and hash
the actual package bytes. The source preflight routes package reads to the
captured files inside its generator subprocess. This is necessary because the
installed `gen-linkml` drops its supplied import map when creating a second
view. The subprocess uses the current Python environment whose dependency
versions were captured; installed files and parent-process mappings are unchanged.

Four compatibility regressions failed before these fixes. Further behavioral
checks demonstrated and fixed the discarded import map by giving the capture
modified package bytes without editing the installed file. Direct-versus-captured
checks cover both namespace orders, view eviction and restoration, missing
unselected files, and URL/CURIE package spellings. All 24 import compatibility
tests pass. The combined cache, fitness, preflight and provenance checks pass
all 183 tests. Both real schemas regenerate exactly, and generation digests,
the complete fitness hash and all historical fitness cache bytes remain fixed.
A sixth plugin review checks the complete branch.

The sixth plugin review is retained in
`schema_cache_codex_sixth_2026-09-11.txt`. All three findings are addressed.
Equivalent `linkml:./types` and `linkml:../schema/types` spellings bypassed
literal package mapping and could poison a rebuild cache (#1275). The isolated
generator now normalizes paths at its loader lookup, binding namespace-resolved
local files as well as installed packages to the captured copies.

The source preflight now uses the same captured namespace traversal as schema
views, with the generator's default initialization order and strict errors.
This supports local aliases such as `lm:types` after prefix expansion (#1276)
and avoids a separate, divergent import resolver. Captured YAML is parsed
directly with LinkML's duplicate-checking loader before constructing the schema,
so a one-line flow document without a newline cannot be guessed to be a filename
(#1277). The existing edit-during-parse regression still exercises actual LinkML
parsing, using the new literal parser entry point.

Nine regressions failed against the reviewed revision. All 51 focused snapshot
and import checks pass after the fixes, including real changed-and-restored
package inputs, prefix override generation and flow-style roots/imports.
The final local review checked the named reproductions, shared resolver ordering,
loader lookup normalization, duplicate-checking parser semantics and isolation of
the child process. No finding from the six plugin reviews remains unresolved.

The final compatibility run also preserves the generator's inference of an
omitted source name from its ID. CI found #1278: the memoization test counted
calls to the shared cache accessor, which now also supplies the view identity.
The corrected guard forbids constructing a new view or rebuilding an unchanged
inventory after warmup; it permits the byte reads required for freshness.
All 60 affected compatibility/cache/statistics checks pass. Both real schemas
regenerate exactly, with the same full/core generation digests and complete
fitness hash; all historical fitness cache files remain byte-identical.

Final combined validation: 206 cache, import, preflight, fitness, statistics and
provenance tests passed. No further code change followed this run. CI must pass
on the committed revision before the branch is merged.
