# Callback relayer review, 2026-11-14

The production diff at 71a327bcd was reviewed separately without editing it.
The stage file is byte-identical to its pre-prefix version. Capture-level reuse
includes exact input bytes, fresh history checks, the existing sticky validator
guard and transactional publication. Standalone and final assembly replay remain
fresh. No acceptance-rule defect was identified in that pass.

Findings for the lead's issue ledger; this helper may not write to GitHub:

1. The diagnostic summary initially read a live metrics file once for its rows
   and again for its digest. An append between those reads could make an interim
   digest name a later file view. Corrected by parsing and hashing one byte
   buffer. Final summaries must be regenerated after the measurement exits.
   Raw metrics were not rewritten. This is a diagnostic provenance finding,
   not a production callback defect.
2. Total observer CPU is not established as flat. Early measurements show lower
   repeated-verification cost, while total CPU varies across payloads and stage
   transitions. The final handoff must give the completed measurement and keep
   this distinct from the passing scanner proof. Do not close the broader
   performance claim on the strength of the structural repair alone.
3. The summary initially rendered an absent function span as zero seconds.
   That is not evidence of zero cost, particularly for the older instrument.
   Corrected to report `not recorded`; the measured total observer times are
   unchanged. The final table must be regenerated with this correction.
4. The optional post-run retained-capture profiles both refused because their
   schema snapshot was not a nonempty immutable SchemaSnapshot. One profile
   also reports a negative aggregate timer. These are unusable replay profiles;
   preserve them as diagnostic failures and do not use them to attribute CPU.
   The live observer measurements were recorded before this replay attempt.

The stage-transition regression now exercises the approved whole-unit boundary:
an identical verified unit skips replay; changing the unit forces a fresh replay.
It no longer asserts reuse of an individual receipt producer across a core
transition. The causal-prefix regression separately verifies suffix-only
observation work. The additional forty-variant storage test is not callback
performance evidence.
