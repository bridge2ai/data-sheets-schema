# Semantic-v3 authority source snapshot

These gzip files preserve the exact five source byte streams named by
`data/rubric/semantic_evidence_authority_v3.json` at release. Each uncompressed
SHA256 is verified against that frozen artifact before reproduction. Sources
are recoverable independently from commit
`b36bb067641467b7e14bea42fa378ac06167d68f` at the same paths. Compression uses
mtime=0. The snapshots allow shallow clones and installed test environments
to verify the release without requiring Git history or current schema bytes.

Do not regenerate these files or the released authority when current schema,
rubric or alias sources evolve. A proposed authority change requires a new
instrument identity and independent review. No evaluation acceptance reads
these test fixtures.
