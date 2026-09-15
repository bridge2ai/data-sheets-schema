Reviewed public commit: `f36a5254d57b958a7b9c92e6b8cd9522fc39c260`.

# Codex Adversarial Review

Target: branch diff against c6243db1b3777fca62ff3a541e45a82c1e824eb7
Verdict: needs-attention

Do not ship: a surviving entry can retain a rejected relationship by changing an unchecked scalar target.

Findings:
- [high] Bind scalar relationship targets to member identity (src/data_sheets_schema/evidence_assertions.py:201-206)
  The signature ignores `target_dataset`, although D4D_Composition.yaml:506–524 defines it as the target dataset's identifier/URL. Static reproducer: original `related_datasets` contains `(id=urn:rel:r, target_dataset=https://example.org/R)` and `(id=urn:rel:s, target_dataset=https://example.org/S)`, both with `relationship_type=derives_from`. Declare `remove_relationship={"path":"/related_datasets/0","identity":"/id"}`. Keep only the second entry but change its target to https://example.org/R. Its signature still matches the original second entry, so the checker returns no finding while the explicitly rejected relationship remains. Both API and native gates use this check.
  Recommendation: Include scalar relationship endpoints such as `target_dataset` in member identity binding. Reject changed endpoints and add this survivor-retargeting regression alongside legitimate-removal controls.

Next steps:
- Fix endpoint identity binding and re-review the affected matching paths.
