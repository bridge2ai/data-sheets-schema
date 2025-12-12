# D4D Schema Analysis TSV Files

This directory contains tab-separated value (TSV) extracts from the comprehensive D4D Schema Evolution Analysis.

## Files

### Core Comparison Tables

**`d4d_evolution_metrics.tsv`** (593 bytes)
- High-level comparison of Gebru et al. (2021) vs Bridge2AI schema
- Metrics: sections, structure, format, ontology alignment, extensibility
- Shows +43% increase in modules, full machine-readability transformation

**`d4d_section_coverage.tsv`** (3.5 KB)
- Complete mapping of all 57 original Gebru questions to Bridge2AI classes
- Organized by 7 original modules (Motivation, Composition, Collection, Preprocessing, Uses, Distribution, Maintenance)
- Coverage status: Full, Enhanced, Extended, Moved
- Documents architectural reorganization decisions

**`d4d_module_summary.tsv`** (922 bytes)
- Summary of all 12 Bridge2AI modules (10 user-facing + Variables + Base)
- Maps each module to original Gebru sections
- Identifies 4 entirely new modules (Ethics, Human Subjects, Data Governance, Variables)
- Class counts and key enhancements per module

### Enhancement Analysis

**`d4d_enhancements_summary.tsv`** (1.8 KB)
- 15 major enhancements beyond basic question coverage
- Compares Gebru free-text approach vs Bridge2AI structured classes
- Documents impact of each enhancement
- Examples: BiasTypeEnum, CRediT roles, semantic versioning, confidentiality levels

**`d4d_new_modules.tsv`** (1.0 KB)
- Deep dive into 4 modules not in original Gebru framework
- Rationale for each new module
- Regulatory frameworks addressed (GDPR, HIPAA, IRB, 45 CFR 46, etc.)
- Influence sources (RO-Crate, FAIRSCAPE, ISO 27001, NIST)

### Semantic Web Integration

**`d4d_ontology_mappings.tsv`** (1.0 KB)
- 15+ ontology/vocabulary integrations
- Prefix, usage, and URI for each ontology
- Transforms Gebru's informal answers into linked open data
- Includes Schema.org, DCAT, PROV-O, AIO, DUO, QUDT, CRediT, etc.

### Philosophical Alignment

**`d4d_philosophical_alignment.tsv`** (428 bytes)
- 5 core values from Gebru et al. preserved in Bridge2AI
- Demonstrates how structured schema enhances original goals
- Shows preservation of transparency, bias avoidance, reproducibility

## Source Document

All data extracted from:
- **`../D4D_SCHEMA_EVOLUTION_ANALYSIS.md`** (32 KB, 822 lines)
- Analysis date: 2025-12-12
- Compares Gebru et al. arXiv:1803.09010v8 (December 2021) to Bridge2AI LinkML schema

## Usage

### Import into spreadsheet software
```bash
# Open in Excel, Google Sheets, LibreOffice Calc, etc.
open notes/d4d_evolution_metrics.tsv
```

### Parse in Python
```python
import pandas as pd
df = pd.read_csv('notes/d4d_evolution_metrics.tsv', sep='\t')
```

### Parse in R
```r
df <- read.delim('notes/d4d_evolution_metrics.tsv', sep='\t')
```

### View in terminal
```bash
column -t -s $'\t' notes/d4d_evolution_metrics.tsv | less -S
```

## Statistics

- **Total files**: 7 TSV tables
- **Total size**: ~9.1 KB
- **Coverage**: 100% of 57 original Gebru questions documented
- **Modules analyzed**: 12 Bridge2AI modules
- **Ontologies mapped**: 15+ semantic web vocabularies
- **Enhancements documented**: 15 major improvements

## Related Files

- `../D4D_SCHEMA_EVOLUTION_ANALYSIS.md` - Full prose analysis
- `../data/publications/1803.09010v8.pdf` - Original Gebru et al. paper
- `../src/data_sheets_schema/schema/` - LinkML schema source files
