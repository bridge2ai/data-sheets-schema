# Bridge2AI Data Sheets - HTML Demos

This directory contains interactive HTML demonstrations of the Bridge2AI Data Sheets Schema implementation.

## Live Demo

View the interactive HTML datasheets at: [GitHub Pages URL will be here]

## Contents

- `index.html` - Landing page with links to all dataset demonstrations
- `D4D_-_AI-READI_FAIRHub_v3_human_readable.html` - AI-READI diabetes dataset
- `D4D_-_CM4AI_Dataverse_v3_human_readable.html` - CM4AI cell atlas dataset  
- `D4D_-_VOICE_PhysioNet_v3_human_readable.html` - Bridge2AI-Voice dataset
- `datasheet-common.css` - Shared stylesheet with responsive design and dark mode

## Features

- **Compact Table Formats:** Authors, distribution data, and funding displayed as clean tables
- **Actual Dataset Titles:** Real titles extracted from YAML metadata
- **Required Field Indicators:** Visual cues showing required vs optional fields
- **Responsive Design:** Mobile-friendly with dark mode support
- **Semantic Organization:** Content organized by D4D sections

## Technical Implementation

These HTML files are generated from YAML source data using the `HumanReadableRenderer` class in `src/html/human_readable_renderer.py`. The renderer includes:

- Intelligent detection of different data types (authors, demographics, funding)
- Automatic table formatting for structured data
- Schema-aware required field indicators
- Responsive CSS design with accessibility features