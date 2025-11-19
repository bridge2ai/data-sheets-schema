#!/bin/bash
# Test if mkdocs includes HTML files
echo "Testing mkdocs build locally..."
poetry run mkdocs build --clean -d /tmp/test_site 2>&1 | tail -20
echo ""
echo "Checking if HTML files are in build:"
find /tmp/test_site -name "*.html" -path "*/html_output/*" | head -10
echo ""
echo "Checking directory structure:"
ls -la /tmp/test_site/html_output/ 2>/dev/null || echo "No html_output directory in build!"
