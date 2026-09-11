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
remain tied to installed dependency versions; other non-relative imports fail
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
