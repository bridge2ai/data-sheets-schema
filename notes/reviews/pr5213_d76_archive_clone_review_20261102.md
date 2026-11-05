# D76 round three: archive-copy tooling review, 2026-11-02

Local issue record D76-R3-T6 for AGY; no GitHub action while offline.

Final-commit revalidation requires independent copies for the notes cohorts.
At the capacity check,17,737,812KiB remained. Seven ordinary extracted copies,
a new base and tar would consume about6.2GiB before the test artifacts, leaving
little headroom above the working reserve. Existing evidence must be preserved.

The bounded clone helper reads a SHA-bound retained archive proof, verifies both
main and FAIRSCAPE tracked bytes and absence of untracked/ignored files, and
copies into fresh physical paths. Each regular file uses macOS `clonefile`,
with a distinct inode and no ordinary-copy fallback. Literal symlinks are kept.
Complete before/after/source/destination inventories bind bytes and modes,
including Git metadata. Failed copies remain as evidence and are never cleaned
up automatically. Original tar files and earlier copies are unchanged.

Independent read-only review found an initial defect: `os.walk` silently skips
unreadable directories unless given an error callback. That could make a claimed
complete inventory omit Git metadata. The frozen contract produced2 passes
and1 failure before repair, log SHA-256
`95e76d6889537e405cf183c76d05b54616e1892c1f873d505b69980b1e63fe57`.
The real clone control verifies distinct inodes, actual copy-on-write isolation,
literal symlinks and refusal to overwrite; the error control verifies there is
no full-copy fallback. The repair makes every traversal error fatal.

Post-repair contracts pass3/3, log SHA-256
`7f651a454b7b284efe70fac28605ab5d9c389d39a8b6c9aae1f2193f021e78e2`.
One full pinned16bb clone canary completed with proof SHA-256
`1d5df77e24fcec9ce1cc22f4d7c60e5f0533c617f6671dff5a96e78f25a83ac0`.
Source-before, source-after and destination inventory files all have SHA-256
`e7d6dd964121ff9628903ed15640292a363963e196a60e68a6156d79ec120670`.
Both main and FAIRSCAPE remain clean at their pinned trees. These observations
are specific to this local macOS filesystem. Successful clones reduce initial
data duplication; subsequent writes can still allocate blocks, so the capacity
gate remains in force. This tool does not establish cross-platform CI results.
