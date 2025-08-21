# HTML Renderers for Datasheets for Datasets

This directory contains HTML rendering tools for converting D4D (Datasheets for Datasets) YAML data into human-readable HTML formats.

## Files

### Core Renderers

- **`human_readable_renderer.py`** - Main human-readable HTML renderer
  - Creates beautiful, document-like HTML with proper D4D section organization
  - Modern responsive design with professional styling
  - Intelligent categorization into D4D sections (Motivation, Composition, etc.)
  - Smart value formatting (links, numbers, lists, nested objects)
  - No raw JSON/YAML structures - everything is human-readable

- **`process_text_files.py`** - LinkML-style HTML renderer  
  - Creates HTML that follows LinkML conventions
  - More technical format showing raw data structures
  - Useful for debugging and technical review

- **`convert_yaml_to_html.py`** - Original simple YAML to HTML converter
  - Basic conversion utility (superseded by the above renderers)

### Usage

```bash
# Generate human-readable HTML (recommended)
python src/html/human_readable_renderer.py

# Generate LinkML-style HTML 
python src/html/process_text_files.py
```

### Input Data

The renderers process YAML files from `data/sheets/`:
- `D4D_-_AI-READI_FAIRHub_v3.txt`
- `D4D_-_CM4AI_Dataverse_v3.txt` 
- `D4D_-_VOICE_PhysioNet_v3.txt`

### Output

Generated files are saved to `data/sheets/html_output/`:
- `*_human_readable.html` - Beautiful, document-like format
- `*_linkml.html` - Technical LinkML-style format
- `*_data.yaml` - Extracted structured data

### Features

#### Human-Readable Renderer Features:
- 🎯 **Smart D4D Categorization** - Automatically organizes content into proper Datasheets for Datasets sections
- 📝 **Natural Language Formatting** - No technical syntax, everything reads like documentation
- ✨ **Professional Design** - Modern gradient headers, card layouts, responsive design
- 🔗 **Smart Links** - DOIs and URLs become clickable links
- 📊 **Formatted Data** - Numbers get separators, booleans become Yes/No
- 📱 **Mobile Responsive** - Works on all screen sizes

#### D4D Section Organization:
- 🎯 **Motivation** - Why was the dataset created?
- 📊 **Composition** - What do the instances represent?  
- 🔍 **Collection Process** - How was the data acquired?
- 🔧 **Preprocessing/Cleaning/Labeling** - Data processing steps
- 🚀 **Uses** - What tasks could the dataset be used for?
- 📤 **Distribution** - How will the dataset be distributed?
- 🔄 **Maintenance** - How will the dataset be maintained?
- 👥 **Human Subjects** - Does the dataset relate to people?

## Dependencies

- Python 3.7+
- PyYAML
- Jinja2

Install dependencies:
```bash
pip install pyyaml jinja2
```