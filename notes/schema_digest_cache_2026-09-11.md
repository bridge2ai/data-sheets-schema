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

No schema, vocabulary, generation artifact or prior evaluation was rewritten.
The separate concurrent-write and repeated-stale-rebuild memory concerns in
#946 remain open; this change does not claim to synchronize concurrent editors
or free views retained by LinkML's method caches.
