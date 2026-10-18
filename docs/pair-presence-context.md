# Historical presence rules in the pair checker

`python -m data_sheets_schema.d4d_pair_consistency --full FULL --core CORE`
compares the pair using the current full/core schemas, or the files explicitly
selected by `--full-schema` and `--core-schema`.

The CLI captures the adjacent `PROJECT_provenance.yaml` once. Its recorded
`schema.digest_md5` serves two purposes: comparison with today's rendered
Dataset digest under the record's selected profile, and lookup of the recorded
CoreDataset slot inventory in the existing digest ledger. An unrelated digest
change cannot excuse a missing shared slot that this inventory proves existed.
Content disagreements remain errors under every history case.

When the digest differs and the ledger proves the slot did not exist, presence
mismatches remain warnings. An unknown inventory keeps the existing broad
warning rule, without claiming historical absence was established. A known
empty inventory is distinct from an unknown one. Missing, unreadable or malformed
provenance cannot establish a historical exception, so presence remains strict.
No ledger entries or historical records are changed by this check.

JSON output adds a versioned `presence_context` with the captured provenance
hash, recorded and current digest, selected profile, `schema_moved`, inventory
availability and selected comparison-schema paths. Text output includes a short
context line. The pure `validate_pair_data(...).to_dict()` format is unchanged.
Custom schema options continue to select pair structure; the historical digest
comparison still uses the current profile digest. The schema paths in the
context are selections, not claims of captured schema hashes or historical
schema recovery.

For #4309, a read-only scan of 90 tracked pairs with known digests found seven
pairs with ten presence errors previously downgraded to warnings by the CLI.
All seven already failed for other errors. The correction establishes neither
new scientific scores nor a historical overall pass-to-fail result in that scan.
