# Complete fitness specification identity — 2026-09-11

This is a new boundary for future slot-fitness judgements, resolving #1261.
It supplements, without rewriting, `fitness_cache_decision_2026-09-11.md` and
its JSON audit for #919. No new fitness judgement or semantic rescore ran.

The generation digest intentionally abbreviates nested ranges. The slot-fitness
judge receives their full specification, so generation digest equality alone
does not establish fitness-instrument equality. Its cache context now also
records a SHA256 of the complete captured specifications. The current Dataset
value is `537e5536d3344b1d0a5e8f5e9a064a47ef0bfaebc3209e6004fb233acce4b42e`.
The generation digest remains `a91bad8b8eaf7c34b147ff5970474342`; no schema,
vocabulary or semantic rubric definition changed.

At 2026-09-11T23:25:17Z the offline loader audit again accepted zero of the
1,441 retained fitness entries. All four cache files still match the hashes
registered in the earlier decision. Their earlier schema already differs;
entries with a matching generation digest but no complete specification identity
are also rejected, as a behavioral regression verifies. Empty specification
fields preserve existing non-fitness context fingerprints. The companion JSON
records the new context, both unchanged generation digests, retained cache hashes,
and the earlier decision's hash.

Fresh fitness comparisons still require their own pinned instrument, canary
and budget. This amendment does not add fitness calls to the separately
registered 24-record semantic reference rescore.
