# Generated-product acceptance silently discards SSSOM header differences

Read-only review of `scripts/adhoc/check_final_generation_products_20261110.py` found that parsing discards arbitrary comment/header content and verifies only selected status counts. Changed total counts, precedence statements or additional status categories could pass despite the stated narrow allowances.

Compare normalized header lines, permitting only the known generated date and exact expected free_text/unmapped count changes. Alternatively state an explicitly row-only scope, but do not claim whole-file consistency from discarded header content. Keep the check bounded to these generated products.
