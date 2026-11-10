# Implementation review ledger

All findings below were recorded before fixes. An implementation being corrected locally does not imply merge or generation approval.

| Issue | Finding | Current disposition |
| --- | --- | --- |
| #2975 | Collection-type prose contradicts scalar declaration | G2 correction plus required 3.2.1 artifact identity in progress; unrelated exchange changes remain deferred |
| #5792 | Native diagnostic cleanup reserve overstated its time cap | Fixed at native commit `19e6d99e4`; independent re-review and normal receipt re-canary passed; not an injected cleanup-failure test |
| #5793 | Native diagnostic only measured interpreter identity before execution | Fixed and verified before/after on the same re-canary; native branch remains separate |
| #5794 | G4 report mislabeled issue identities and source facts | Corrected report reviewed by lead; deferred-issue table now agrees with original findings |
| #5795 | Acceptance-guide commands did not match their parsers | Corrected; reviewed guide integrated at `266370c8d` |
| #5796 | Acceptance guide misstated record shapes and implementation behavior | Corrected; actual Creator/Person, Maintainer, permission and API guard contracts described |
| #5797 | Guide implied component checks could establish whole-native acceptance | Corrected; whole-native acceptance remains explicitly unverified |
| #5798 | G1 test draft called unsupported validation/derivation APIs | Source repair and reduction to one positive/four negative cases in progress; initial failed attempt retained |
| #5799 | G2 helper would capture staging/source or wrong toolchain paths | Source repair before generator execution |
| #5800 | G2 helper asserted unchanged digests without a before/after comparison | Source repair before generator execution |
| #5801 | G2 helper would delete existing staging evidence | Source repair to require fresh staging before execution |

The native wrapper changes are retained on their native branch. Main-line delivery extracts portable receipt/source-review tests only; it does not import the separate native selection, lifecycle or WP1 implementation. G1 verifies main-line schema projection/rendering, not native admission.
