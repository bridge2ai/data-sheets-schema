# Issue draft: normalize the macOS TMPDIR spelling in the CHORUS probe

Found during R6 validation, 2026-10-29. Not filed because the task prohibits
network and `gh`. Addressed in this branch before either full CHORUS probe ran.

The proof receives `$TMPDIR` as `/var/folders/...`, while the import launcher
resolves it to `/private/var/folders/...`. The CHORUS probe's `receipts_file`
metadata uses the resolved import path. Replacing only the caller's tree path
would therefore leave `/private<TREE>` for the base and `<TREE>` for head,
failing a comparison on path spelling alone.

The probe now asserts that the declared `GIT_WORK_TREE` resolves to the imported
tree, then reports the imported module's relative path under the caller's
tree spelling. Direct invocations without that variable retain the resolved
tree. Actual source reads, request bytes, receipt fields and counters are
unchanged. The full replay's existing committed baseline hash is the control
for the resulting normalized output.
