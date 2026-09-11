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
