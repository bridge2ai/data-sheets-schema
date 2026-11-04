| Profile | Case JUnit s | Process wall s | Process CPU s | Calls |
| --- | ---: | ---: | ---: | ---: |
| g1 | 542.363 | 546.169 | 503.784 | 1186642825 |
| bc1g2 | 571.855 | 574.371 | 520.219 | 1186878201 |

| Module | G1 self s | BC1+G2 self s | Delta self s |
| --- | ---: | ---: | ---: |
| `~` | 153.997 | 161.731 | +7.734 |
| `site-packages/yaml/scanner.py` | 124.072 | 130.296 | +6.224 |
| `<tree>/src/data_sheets_schema/shared_generation.py` | 7.327 | 10.320 | +2.994 |
| `site-packages/yaml/reader.py` | 55.667 | 57.601 | +1.934 |
| `stdlib/pathlib/_local.py` | 24.365 | 25.582 | +1.217 |
| `site-packages/yaml/parser.py` | 17.780 | 18.731 | +0.951 |
| `site-packages/linkml_runtime/utils/yamlutils.py` | 13.035 | 13.980 | +0.945 |
| `stdlib/json/encoder.py` | 25.483 | 26.269 | +0.786 |
| `site-packages/yaml/constructor.py` | 15.334 | 16.083 | +0.748 |
| `site-packages/jsonasobj2/_jsonobj.py` | 16.751 | 17.254 | +0.503 |
| `<tree>/src/data_sheets_schema/audit_batches.py` | 4.023 | 4.475 | +0.452 |
| `stdlib/json/decoder.py` | 8.105 | 8.554 | +0.449 |
| `<tree>/src/data_sheets_schema/audit_grammar.py` | 4.018 | 4.303 | +0.285 |
| `<tree>/src/data_sheets_schema/receipt_completion.py` | 0.770 | 1.004 | +0.234 |
| `<tree>/src/data_sheets_schema/typed_audit.py` | 1.045 | 1.262 | +0.217 |

| Function | G1 calls | BC1+G2 calls | G1 cumulative s | BC1+G2 cumulative s |
| --- | ---: | ---: | ---: | ---: |
| `<tree>/src/data_sheets_schema/bc1_selection.py:validate_spec_mode` | 0 | 1703 | 0.000 | 0.184 |
| `<tree>/src/data_sheets_schema/bc1_selection.py:enabled` | 0 | 3788 | 0.000 | 0.005 |
| `<tree>/src/data_sheets_schema/bc1_selection.py:_pairs` | 0 | 45873 | 0.000 | 0.034 |
| `<tree>/src/data_sheets_schema/typed_audit_runtime.py:_bc1` | 0 | 102 | 0.000 | 0.001 |
| `<tree>/scripts/build_api_registrations.py:partition_profiles` | 0 | 0 | 0.000 | 0.000 |
| `<tree>/scripts/build_api_registrations.py:size_typed_audit_input` | 0 | 0 | 0.000 | 0.000 |
| `<tree>/src/data_sheets_schema/bc1_registration.py:size_inputs` | 0 | 0 | 0.000 | 0.000 |
| `<tree>/src/data_sheets_schema/schema_cache.py:load_yaml` | 14 | 14 | 5.367 | 5.418 |
| `<tree>/src/data_sheets_schema/schema_snapshot.py:capture_schema` | 5670 | 5670 | 19.012 | 18.382 |
| `<tree>/src/data_sheets_schema/audit_omissions.py:_schema` | 10 | 10 | 68.031 | 68.904 |
| `<tree>/src/data_sheets_schema/audit_omissions.py:_read` | 322 | 322 | 184.668 | 194.971 |
| `<tree>/src/data_sheets_schema/duplicate_keys.py:nesting_exceeds` | 312 | 312 | 138.695 | 148.044 |
| `<tree>/src/data_sheets_schema/shared_generation.py:capture` | 1693 | 1693 | 126.059 | 136.770 |
| `<tree>/src/data_sheets_schema/shared_generation.py:assert_current` | 1641 | 1641 | 120.403 | 131.928 |
| `<tree>/src/data_sheets_schema/shared_generation.py:_contracts_digest` | 5057 | 5057 | 89.515 | 97.603 |
| `<tree>/src/data_sheets_schema/typed_audit_runtime.py:recover` | 22 | 22 | 267.576 | 291.372 |
| `<tree>/src/data_sheets_schema/typed_audit_runtime.py:_rebuild` | 34 | 34 | 259.453 | 282.859 |
