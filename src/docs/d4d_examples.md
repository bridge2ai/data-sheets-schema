# D4D Examples

This page provides links to rendered Datasheet for Datasets (D4D) examples for Bridge2AI data generating projects.

## Curated Comprehensive Datasheets

These are the most comprehensive datasheets for each project, created through extensive AI-powered synthesis:

### AI-READI
- [Human Readable HTML](html_output/concatenated/curated/AI_READI_human_readable.html)
- [LinkML Format HTML](html_output/concatenated/curated/AI_READI_linkml.html)
- [Download YAML](yaml_output/concatenated/curated/AI_READI_curated.yaml)

### CM4AI
- [Human Readable HTML](html_output/concatenated/curated/CM4AI_human_readable.html)
- [LinkML Format HTML](html_output/concatenated/curated/CM4AI_linkml.html)
- [Download YAML](yaml_output/concatenated/curated/CM4AI_curated.yaml)

### VOICE
- [Human Readable HTML](html_output/concatenated/curated/VOICE_human_readable.html)
- [LinkML Format HTML](html_output/concatenated/curated/VOICE_linkml.html)
- [Download YAML](yaml_output/concatenated/curated/VOICE_curated.yaml)

## GPT-5 Synthesized Datasheets

These datasheets were automatically synthesized from multiple documents using GPT-5:

### AI-READI
- [Synthesized HTML](html_output/concatenated/AI_READI_d4d_synthesized.html)
- [Download YAML](yaml_output/concatenated/gpt5/AI_READI_d4d.yaml)

### CHORUS
- [Synthesized HTML](html_output/concatenated/CHORUS_d4d_synthesized.html)
- [Download YAML](yaml_output/concatenated/gpt5/CHORUS_d4d.yaml)

### CM4AI
- [Synthesized HTML](html_output/concatenated/CM4AI_d4d_synthesized.html)
- [Download YAML](yaml_output/concatenated/gpt5/CM4AI_d4d.yaml)

### VOICE
- [Synthesized HTML](html_output/concatenated/VOICE_d4d_synthesized.html)
- [Download YAML](yaml_output/concatenated/gpt5/VOICE_d4d.yaml)

## Claude Code Synthesized Datasheets (Deterministic)

These datasheets were automatically synthesized using Claude Sonnet 4.5 with **deterministic settings** (temperature=0.0) for reproducibility:

### AI-READI
- [Synthesized HTML](html_output/concatenated/claudecode/AI_READI.html)
- [Download YAML](yaml_output/concatenated/claudecode/AI_READI_d4d.yaml)
- [Download Metadata](yaml_output/concatenated/claudecode/AI_READI_d4d_metadata.yaml)

### CHORUS
- [Synthesized HTML](html_output/concatenated/claudecode/CHORUS.html)
- [Download YAML](yaml_output/concatenated/claudecode/CHORUS_d4d.yaml)
- [Download Metadata](yaml_output/concatenated/claudecode/CHORUS_d4d_metadata.yaml)

### CM4AI
- [Synthesized HTML](html_output/concatenated/claudecode/CM4AI.html)
- [Download YAML](yaml_output/concatenated/claudecode/CM4AI_d4d.yaml)
- [Download Metadata](yaml_output/concatenated/claudecode/CM4AI_d4d_metadata.yaml)

### VOICE
- [Synthesized HTML](html_output/concatenated/claudecode/VOICE.html)
- [Download YAML](yaml_output/concatenated/claudecode/VOICE_d4d.yaml)
- [Download Metadata](yaml_output/concatenated/claudecode/VOICE_d4d_metadata.yaml)

## Individual Dataset Datasheets

These datasheets were created from specific dataset metadata sources:

### AI-READI (FAIRHub v3)
- [Human Readable](html_output/D4D_-_AI-READI_FAIRHub_v3_human_readable.html)
- [LinkML Format](html_output/D4D_-_AI-READI_FAIRHub_v3_linkml.html)

### CM4AI (Dataverse v3)
- [Human Readable](html_output/D4D_-_CM4AI_Dataverse_v3_human_readable.html)
- [LinkML Format](html_output/D4D_-_CM4AI_Dataverse_v3_linkml.html)

### VOICE (PhysioNet v3)
- [Human Readable](html_output/D4D_-_VOICE_PhysioNet_v3_human_readable.html)
- [LinkML Format](html_output/D4D_-_VOICE_PhysioNet_v3_linkml.html)

## About the Datasheets

### Curated Comprehensive Datasheets
The **Curated Comprehensive Datasheets** represent the most complete and authoritative metadata for each project, created through extensive AI-powered synthesis of multiple data sources and documentation. These files include both human-readable HTML renderings and downloadable YAML source files.

### GPT-5 Synthesized Datasheets
The **GPT-5 Synthesized Datasheets** were created by:
1. Concatenating multiple project-related documents in reproducible order
2. Processing with GPT-5 to extract and synthesize D4D metadata
3. Validating against the LinkML schema
4. Rendering to human-readable HTML format

These provide automated comprehensive project-level metadata and include both HTML views and downloadable YAML files.

### Claude Code Synthesized Datasheets (Deterministic)
The **Claude Code Synthesized Datasheets** are generated with **deterministic settings** for reproducibility:
1. **Temperature=0.0**: Eliminates randomness in model responses
2. **Pinned model version**: `claude-sonnet-4-5-20250929` prevents changes from model updates
3. **Version-controlled prompts**: Stored in external files tracked in git
4. **Local schema**: Uses version-controlled schema file (not remote)
5. **Comprehensive metadata**: Each YAML includes a metadata file tracking all generation parameters

**Key Features:**
- Reproducible: Running twice on same input produces identical output
- Traceable: Complete provenance tracking via metadata files
- Comparable: Can meaningfully compare with GPT-5 outputs
- Transparent: All prompts and settings version-controlled and documented

**Metadata Files** contain:
- SHA-256 hashes of input file, schema, and prompts
- Model settings (temperature, max_tokens)
- Processing environment details
- Git commit hash for provenance
- Reproducibility command

See [DETERMINISM.md](https://github.com/bridge2ai/data-sheets-schema/blob/main/DETERMINISM.md) for complete details on the deterministic approach.

### Individual Dataset Datasheets
The **Individual Dataset Datasheets** provide detailed metadata for specific datasets from each project's primary data repository (FAIRHub, Dataverse, PhysioNet).

## Schema Information

All datasheets conform to the [Datasheets for Datasets](https://arxiv.org/abs/1803.09010) framework by Gebru et al., implemented using the [Bridge2AI LinkML schema](https://github.com/bridge2ai/data-sheets-schema).

The YAML files can be validated, transformed, and processed using LinkML tools. See the [LinkML documentation](https://linkml.io/) for more information.
