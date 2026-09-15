# Receipt acceptance in the matched canary controllers

The v10o API canary completed despite a false literal quotation in its coverage
receipt (#1854). The existing receipt checker detected it. Its
`findings_gated: 0` avoids counting the same defect twice: the existing
`canary.receipt_floors` separately reports `snippets unverified: 1`.

Both experimental controllers now recompute receipts from the saved full
record, receipt, provenance and registered sources, then enforce those existing
floors before reporting completion pending independent review. Missing,
unreadable, uncheckable, vacuous or failing receipts produce validation failure;
the result retains the observed block and floor counts. A cached passing block
cannot replace this reading of current files. No generated artifact is repaired.

This fixes omitted enforcement, without changing receiptsv3 or the shared
canary gate. In particular, the historical treatment of a quote found in another
chunk remains unchanged. Literal matching does not establish source attribution,
semantic support, complete claim coverage or scientific acceptance. The separate
source review remains necessary.

All prior artifacts, registrations and measurements remain frozen. Any new
scientific attempt must pin and review the changed controllers before launch.
