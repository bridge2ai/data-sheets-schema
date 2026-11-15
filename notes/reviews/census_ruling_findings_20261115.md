Read-only candidate review finding, 2026-11-15. The helper has no GitHub write permission; the lead should file this record as an issue before integration.

Title: Manifest write seeding must preserve an existing memo entry for the identical pin.

The initial candidate assigned the newly generated fingerprints to the memo unconditionally. If a caller removed a prior manifest and recreated identical bytes at the same path, that assignment could erase a cached refusal or refresh the fingerprints of an existing successful verdict. The existing rule requires a different pin or process after refusal, and requires the original successful verdict's fingerprints for reuse.

Resolution: seed only an absent key. Preserve both refusals and successful verdicts, then run the existing full verification path. Two regression tests recreate the same pin after a failed verification and after a payload identity change. No production registration or dispatch call is removed.

Operational finding from the public canary rerun: the full ancestor recheck refused because /Users/marcin changed identity during generation. The failed field and actor were not captured. The implementation uses the existing full stat identity, including directory timestamps, so broader directory activity can cause a conservative refusal even when the installed payload bytes have not been shown to change. The lead should record this availability finding as an issue. The settled requirement to refuse ancestor identity changes remains implemented; no check was weakened and no new design decision was assumed.
