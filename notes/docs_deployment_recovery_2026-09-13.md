# Documentation deployment recovery — 2026-09-13

After #1616 merged at 5d4044fe7, the automatic documentation workflow failed
before building: `poetry install -E docs` requested an extra removed by the
packaging cleanup. #1758 covers both deployment workflows, which share that
command. Both now install the declared development dependency group with
`poetry install --with dev`; it contains the MkDocs tools, while LinkML is a
runtime dependency. The lockfile and dependency declarations are unchanged.

The old command fails with `Extra [docs] is not specified`; the replacement
passes a dry-run dependency selection. `make gendoc` and the actual MkDocs
site build pass locally (4.23 seconds for MkDocs), including its existing
Mermaid CDN asset check. Generated validation pages were restored afterward.
The follow-up contains the two workflow command changes and this note.
No generation/evaluation implementation, instrument, production artifact or
historical measurement changes. Independent review and exact-head CI precede
merge; verify the successful automatic documentation deployment and remove
the completed follow-up branch/worktree.
