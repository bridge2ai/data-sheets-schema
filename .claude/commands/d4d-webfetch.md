Generate D4D datasheets using live URL fetching with WebFetch and ARTL MCP tools,
following the GitHub Actions workflow methodology.

## Workflow Reference

Read .github/workflows/d4d_assistant_create.md for the full workflow.

## Projects and Source URLs

### 1. AI_READI
- https://docs.aireadi.org
- https://fairhub.io/datasets/2

### 2. CM4AI
- https://cm4ai.org
- https://doi.org/10.18130/V3/B35XWX

### 3. VOICE
- https://docs.b2ai-voice.org
- https://doi.org/10.13026/249v-w155

### 4. CHORUS
- https://chorus4ai.org

## Output Location

Save to: data/sheets_d4dassistant/{project}_d4d.yaml

## Generation Process

For each project:

1. **Read workflow instructions** from .github/workflows/d4d_assistant_create.md
2. **Use WebFetch** to retrieve content from each URL
3. **Use WebSearch** to find additional documentation if needed
4. **Use ARTL MCP** to search for related academic publications:
   - mcp__artl__search_europepmc_papers: Find papers by keywords
   - mcp__artl__get_europepmc_paper_by_id: Get paper metadata by DOI/PMID
   - mcp__artl__get_europepmc_full_text: Get full text content
5. **Read schema** from src/data_sheets_schema/schema/data_sheets_schema_all.yaml
6. **Extract D4D metadata** following schema structure:
   - Motivation (purposes, tasks, gaps addressed)
   - Composition (instances, subsets, sampling, anomalies)
   - Collection (acquisition, mechanisms, collectors, timeframes)
   - Preprocessing (strategies, cleaning, labeling)
   - Uses (existing, future impacts, discouraged/intended/prohibited)
   - Distribution (formats, dates, licenses)
   - Maintenance (maintainers, updates, versions)
   - Human Subjects (if applicable: IRB, consent, privacy)
7. **Generate valid YAML** conforming to schema
8. **Validate** with: poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <file>
9. **Save** to data/sheets_d4dassistant/{project}_d4d.yaml

## File Header

```yaml
# D4D Datasheet for {PROJECT} Dataset
# Generation Method: D4D Assistant Workflow (live URL fetch)
# Workflow: .github/workflows/d4d_assistant_create.md
# Source URLs:
#   - {URL1}
#   - {URL2}
# Schema: src/data_sheets_schema/schema/data_sheets_schema_all.yaml
# Generated: {DATE}
```

## Tools Available

- **WebFetch**: Retrieve content from URLs (web pages, PDFs)
- **WebSearch**: Search for additional documentation
- **ARTL MCP (mcp__artl__*)**: Search academic literature

## Validation

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <file>
```

All D4Ds must validate before completion.
