# Historical K1 planner fixture

Saved 2026-10-26 for the K1 v2/A17 comparison (#5155/#5157).
`audit_batches_56c41163f.py.txt` is the exact, unmodified Git source
`56c41163f:src/data_sheets_schema/audit_batches.py`, SHA256
`c95ec83f2f730df8c9766173f4d71367dfe705b08ec4acc4a17f8ef002da4414`.

The historical whole-root sizing helper requires this instrument's two-field
inventory and indivisible-root behavior. Its tests verify these saved bytes
under a distinct module name; they do not replace the installed A17 planner.
Production and A17 measurement tests continue to use the current module.
