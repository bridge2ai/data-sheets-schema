# Native default-profile series, unit 3

This branch stacks on unit2's controller, captured permission verification and
mandatory subscription guard. It adds the explicit native front door and saved
probe producer from the pre-owner source, then the separately reviewed bounded
retained-binary checks. Profile1 is excluded. No CLI command index is replaced;
the entry point is `python -m data_sheets_schema.native_generation`.

`prepare-subscription-guard` and `validate-probe` use saved evidence offline.
The explicitly named `permission-probe` and `launch` commands can invoke a live
binary, but neither is run by this session. Their software tests replace the
actual native process boundary. Retained-binary default verification reads the
declared file and reports version/signature checks as unverified unless those
checks are separately requested and succeed. It never discovers a substitute.

The source-recovery helper, its two inventories and the separate commits record
the exact archived inputs. The added front-door regressions require both guard
authorities before launch dispatch, prove saved validation never launches the
probe producer, and check guard preparation's byte joins and refusal to replace
an existing destination. Existing permission/subscription tests cover admission,
observation, saved readback, one-use evidence and cleanup behavior.

Final head and test counts are logged under `### codex` in the primary
`notes/coordination/STATUS.md`. This is software evidence from synthetic fixtures,
not a real-binary probe, an account/quota observation, launch clearance or
scientific acceptance. AGY publishes the local series and Claude reviews it.
