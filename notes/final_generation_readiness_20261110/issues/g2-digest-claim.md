Read-only review of G2's prepared `scripts/adhoc/g2_collection_type_release_20261110.py` found an unsupported unchanged-digest claim.

The helper computes only post-build API schema digests (around lines 259–273), while the appended release note unconditionally says that neither profile's schema digest moved. Without a captured baseline and comparison, the helper cannot establish that claim.

Measure the relevant full/Core API digests on the existing merged schemas before replacement and compare with the generated artifacts afterward, using the same selected profiles and implementation. Refuse or explicitly report differences; do not silently update protected prompt pins. Write the release-history claim only after it is verified. No prompt/scanner redesign is requested.
