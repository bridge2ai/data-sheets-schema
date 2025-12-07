## Add your own custom Makefile targets here

SCHEMA_EXAMPLEDIR = src/data/examples
VALID_EXAMPLEDIR = $(SCHEMA_EXAMPLEDIR)/valid
INVALID_EXAMPLEDIR = $(SCHEMA_EXAMPLEDIR)/invalid
SCHEMA_CLASSES = $(shell $(RUN) yq -cr '.classes | keys | join(" ")' $(SOURCE_SCHEMA_PATH))

# D4D Pipeline directories
RAW_DIR = data/raw
PREPROCESSED_DIR = data/preprocessed
PREPROCESSED_INDIVIDUAL_DIR = $(PREPROCESSED_DIR)/individual
PREPROCESSED_CONCAT_DIR = $(PREPROCESSED_DIR)/concatenated
D4D_INDIVIDUAL_DIR = data/d4d_individual
D4D_CONCAT_DIR = data/d4d_concatenated
D4D_HTML_DIR = data/d4d_html

# Projects
PROJECTS = AI_READI CHORUS CM4AI VOICE

# Bridge2AI source documentation Google Sheet
# Note: Use CSV export URL format for the extractor script
# Updated 2024-12-05 to new sheet (old sheet was marked OBSOLETE)
BRIDGE2AI_SHEET_ID = 1jBD6sTp6TDemy6v75PGAHSVz5yfIAXZ8zdDPbmOGATM
BRIDGE2AI_SHEET_URL = https://docs.google.com/spreadsheets/d/$(BRIDGE2AI_SHEET_ID)/export?format=csv

# ============================================================================
# D4D Pipeline: Step 0 - Download source documents
# ============================================================================

# Download source documents from Bridge2AI Google Sheet
# This populates data/raw/{PROJECT}/ with HTML, PDF, JSON files
# Note: The sheet exports as CSV with columns: CM4AI, VOICE, AI-READI, CHORUS
download-sources:
	@echo "Downloading source documents from Bridge2AI Google Sheet..."
	@echo "Sheet ID: $(BRIDGE2AI_SHEET_ID)"
	@echo "CSV URL: $(BRIDGE2AI_SHEET_URL)"
	@echo ""
	@echo "📄 Columns: CM4AI, VOICE, AI-READI, CHORUS"
	@echo ""
	@mkdir -p $(RAW_DIR)
	$(RUN) python -m src.download.organized_dataset_extractor \
		"$(BRIDGE2AI_SHEET_URL)" \
		-o $(RAW_DIR)
	@echo ""
	@echo "✅ Download complete! Files saved to $(RAW_DIR)/"
	@echo "Run 'make data-status' to see results"

# Dry run - analyze sheet without downloading
download-sources-dry-run:
	@echo "Analyzing Bridge2AI Google Sheet (dry run)..."
	$(RUN) python -m src.download.enhanced_sheet_downloader \
		"$(BRIDGE2AI_SHEET_URL)" \
		--dry-run

# Download from a custom sheet URL
# Usage: make download-sheet SHEET_URL="https://docs.google.com/spreadsheets/d/..."
download-sheet:
ifndef SHEET_URL
	$(error SHEET_URL is not defined. Usage: make download-sheet SHEET_URL="https://...")
endif
	@echo "Downloading from custom sheet: $(SHEET_URL)"
	@mkdir -p $(RAW_DIR)
	$(RUN) python -m src.download.organized_dataset_extractor \
		"$(SHEET_URL)" \
		-o $(RAW_DIR)

# ============================================================================
# D4D Pipeline: Step 1 - Preprocess source documents
# ============================================================================

# Preprocess raw sources into text-ready format for D4D generation
# - .txt, .json, .md: Copied as-is
# - .pdf: Extracted to text using pdfminer
# - .html: Skipped (downloader already creates .txt versions)
preprocess-sources:
	$(RUN) python src/download/preprocess_sources.py \
		-i $(RAW_DIR) \
		-o $(PREPROCESSED_INDIVIDUAL_DIR) \
		-p $(PROJECTS)

# Full download + preprocess pipeline
download-and-preprocess:
	$(MAKE) download-sources
	$(MAKE) preprocess-sources

# Generate minimal example files for all classes
# For each file in the list, populate it with an id field
gen-minimal-examples:
	printf "# Example data file\n---\nid: \"data_sheets_schema:123\"\n" | tee -a $(patsubst %, $(VALID_EXAMPLEDIR)/%-minimal.yaml, $(SCHEMA_CLASSES))
	printf "# Example data file - needs more contents\n---\nid: \"data_sheets_schema:123\"\n" | tee -a $(patsubst %, $(VALID_EXAMPLEDIR)/%-valid.yaml, $(SCHEMA_CLASSES))
	printf "# Example invalid data file\n---\nid: 123\n" | tee -a $(patsubst %, $(INVALID_EXAMPLEDIR)/%-invalid.yaml, $(SCHEMA_CLASSES))

# Generate HTML from current D4D YAML files
gen-html:
	$(RUN) python src/html/human_readable_renderer.py

# Concatenate documents from a directory
# Usage: make concat-docs INPUT_DIR=path/to/dir OUTPUT_FILE=path/to/output.txt
# Optional: EXTENSIONS=".txt .md" RECURSIVE=true
concat-docs:
ifndef INPUT_DIR
	$(error INPUT_DIR is not defined. Usage: make concat-docs INPUT_DIR=path/to/dir OUTPUT_FILE=path/to/output.txt)
endif
ifndef OUTPUT_FILE
	$(error OUTPUT_FILE is not defined. Usage: make concat-docs INPUT_DIR=path/to/dir OUTPUT_FILE=path/to/output.txt)
endif
	@echo "Concatenating documents from $(INPUT_DIR) to $(OUTPUT_FILE)"
	$(RUN) python src/download/concatenate_documents.py -i $(INPUT_DIR) -o $(OUTPUT_FILE) \
		$(if $(EXTENSIONS),-e $(EXTENSIONS),) \
		$(if $(RECURSIVE),-r,)

# ============================================================================
# D4D Pipeline: Data Structure Assessment
# ============================================================================

# Show file counts across all data directories and flag empty directories
data-status:
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  D4D Pipeline Data Status Report"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "─────────────────────────────────────────────────────────────────"
	@echo "RAW DOWNLOADS (data/raw/)"
	@echo "─────────────────────────────────────────────────────────────────"
	@for project in $(PROJECTS); do \
		dir="$(RAW_DIR)/$$project"; \
		if [ -d "$$dir" ]; then \
			count=$$(ls -1 "$$dir" 2>/dev/null | wc -l | tr -d ' '); \
			if [ "$$count" -eq 0 ]; then \
				printf "  %-12s : %3d files  ⚠️  EMPTY\n" "$$project" "$$count"; \
			else \
				printf "  %-12s : %3d files\n" "$$project" "$$count"; \
			fi; \
		else \
			printf "  %-12s : ❌ DIRECTORY MISSING\n" "$$project"; \
		fi; \
	done
	@echo ""
	@echo "─────────────────────────────────────────────────────────────────"
	@echo "PREPROCESSED INDIVIDUAL (data/preprocessed/individual/)"
	@echo "─────────────────────────────────────────────────────────────────"
	@for project in $(PROJECTS); do \
		dir="$(PREPROCESSED_INDIVIDUAL_DIR)/$$project"; \
		if [ -d "$$dir" ]; then \
			count=$$(ls -1 "$$dir" 2>/dev/null | wc -l | tr -d ' '); \
			if [ "$$count" -eq 0 ]; then \
				printf "  %-12s : %3d files  ⚠️  EMPTY\n" "$$project" "$$count"; \
			else \
				printf "  %-12s : %3d files\n" "$$project" "$$count"; \
			fi; \
		else \
			printf "  %-12s : ❌ DIRECTORY MISSING\n" "$$project"; \
		fi; \
	done
	@echo ""
	@echo "─────────────────────────────────────────────────────────────────"
	@echo "PREPROCESSED CONCATENATED (data/preprocessed/concatenated/)"
	@echo "─────────────────────────────────────────────────────────────────"
	@if [ -d "$(PREPROCESSED_CONCAT_DIR)" ]; then \
		for project in $(PROJECTS); do \
			file="$(PREPROCESSED_CONCAT_DIR)/$${project}_concatenated.txt"; \
			if [ -f "$$file" ]; then \
				lines=$$(wc -l < "$$file" | tr -d ' '); \
				size=$$(ls -lh "$$file" | awk '{print $$5}'); \
				printf "  %-12s : ✓ exists (%s, %s lines)\n" "$$project" "$$size" "$$lines"; \
			else \
				printf "  %-12s : ❌ MISSING\n" "$$project"; \
			fi; \
		done; \
	else \
		echo "  ❌ DIRECTORY MISSING"; \
	fi
	@echo ""
	@echo "─────────────────────────────────────────────────────────────────"
	@echo "D4D INDIVIDUAL - GPT-5 (data/d4d_individual/gpt5/)"
	@echo "─────────────────────────────────────────────────────────────────"
	@for project in $(PROJECTS); do \
		dir="$(D4D_INDIVIDUAL_DIR)/gpt5/$$project"; \
		if [ -d "$$dir" ]; then \
			count=$$(ls -1 "$$dir"/*_d4d.yaml 2>/dev/null | wc -l | tr -d ' '); \
			if [ "$$count" -eq 0 ]; then \
				printf "  %-12s : %3d YAMLs  ⚠️  EMPTY\n" "$$project" "$$count"; \
			else \
				printf "  %-12s : %3d YAMLs\n" "$$project" "$$count"; \
			fi; \
		else \
			printf "  %-12s : ❌ DIRECTORY MISSING\n" "$$project"; \
		fi; \
	done
	@echo ""
	@echo "─────────────────────────────────────────────────────────────────"
	@echo "D4D INDIVIDUAL - CLAUDE CODE (data/d4d_individual/claudecode/)"
	@echo "─────────────────────────────────────────────────────────────────"
	@for project in $(PROJECTS); do \
		dir="$(D4D_INDIVIDUAL_DIR)/claudecode/$$project"; \
		if [ -d "$$dir" ]; then \
			count=$$(ls -1 "$$dir"/*_d4d.yaml 2>/dev/null | wc -l | tr -d ' '); \
			if [ "$$count" -eq 0 ]; then \
				printf "  %-12s : %3d YAMLs  ⚠️  EMPTY\n" "$$project" "$$count"; \
			else \
				printf "  %-12s : %3d YAMLs\n" "$$project" "$$count"; \
			fi; \
		else \
			printf "  %-12s : ❌ DIRECTORY MISSING\n" "$$project"; \
		fi; \
	done
	@echo ""
	@echo "─────────────────────────────────────────────────────────────────"
	@echo "D4D CONCATENATED (data/d4d_concatenated/)"
	@echo "─────────────────────────────────────────────────────────────────"
	@echo "GPT-5:"
	@if [ -d "$(D4D_CONCAT_DIR)/gpt5" ]; then \
		for project in $(PROJECTS); do \
			file="$(D4D_CONCAT_DIR)/gpt5/$${project}_d4d.yaml"; \
			if [ -f "$$file" ]; then \
				lines=$$(wc -l < "$$file" | tr -d ' '); \
				size=$$(ls -lh "$$file" | awk '{print $$5}'); \
				printf "    %-12s : ✓ exists (%s, %s lines)\n" "$$project" "$$size" "$$lines"; \
			else \
				printf "    %-12s : ❌ MISSING\n" "$$project"; \
			fi; \
		done; \
	else \
		echo "    ❌ DIRECTORY MISSING"; \
	fi
	@echo "Claude Code:"
	@if [ -d "$(D4D_CONCAT_DIR)/claudecode" ]; then \
		for project in $(PROJECTS); do \
			file="$(D4D_CONCAT_DIR)/claudecode/$${project}_d4d.yaml"; \
			if [ -f "$$file" ]; then \
				lines=$$(wc -l < "$$file" | tr -d ' '); \
				size=$$(ls -lh "$$file" | awk '{print $$5}'); \
				printf "    %-12s : ✓ exists (%s, %s lines)\n" "$$project" "$$size" "$$lines"; \
			else \
				printf "    %-12s : ❌ MISSING\n" "$$project"; \
			fi; \
		done; \
	else \
		echo "    ❌ DIRECTORY MISSING"; \
	fi
	@echo "Curated:"
	@if [ -d "$(D4D_CONCAT_DIR)/curated" ]; then \
		curated_count=$$(ls -1 "$(D4D_CONCAT_DIR)/curated"/*_curated.yaml 2>/dev/null | wc -l | tr -d ' '); \
		if [ "$$curated_count" -eq 0 ]; then \
			echo "    ⚠️  No curated files"; \
		else \
			for file in "$(D4D_CONCAT_DIR)/curated"/*_curated.yaml; do \
				if [ -f "$$file" ]; then \
					project=$$(basename "$$file" _curated.yaml); \
					lines=$$(wc -l < "$$file" | tr -d ' '); \
					size=$$(ls -lh "$$file" | awk '{print $$5}'); \
					printf "    %-12s : ✓ exists (%s, %s lines)\n" "$$project" "$$size" "$$lines"; \
				fi; \
			done; \
		fi; \
	else \
		echo "    ❌ DIRECTORY MISSING"; \
	fi
	@echo ""
	@echo "─────────────────────────────────────────────────────────────────"
	@echo "D4D HTML (data/d4d_html/)"
	@echo "─────────────────────────────────────────────────────────────────"
	@for subdir in "concatenated/gpt5" "concatenated/claudecode" "concatenated/curated" "individual/gpt5" "individual/claudecode"; do \
		dir="$(D4D_HTML_DIR)/$$subdir"; \
		label=$$(echo "$$subdir" | sed 's/\// - /'); \
		if [ -d "$$dir" ]; then \
			count=$$(ls -1 "$$dir"/*.html 2>/dev/null | wc -l | tr -d ' '); \
			if [ "$$count" -eq 0 ]; then \
				printf "  %-30s : %3d files  ⚠️  EMPTY\n" "$$label" "$$count"; \
			else \
				printf "  %-30s : %3d files\n" "$$label" "$$count"; \
			fi; \
		else \
			printf "  %-30s : ❌ DIRECTORY MISSING\n" "$$label"; \
		fi; \
	done
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  Summary"
	@echo "════════════════════════════════════════════════════════════════"
	@total_raw=0; \
	total_preprocessed=0; \
	total_d4d_individual_gpt5=0; \
	total_d4d_concat_gpt5=0; \
	total_html=0; \
	for project in $(PROJECTS); do \
		if [ -d "$(RAW_DIR)/$$project" ]; then \
			count=$$(ls -1 "$(RAW_DIR)/$$project" 2>/dev/null | wc -l | tr -d ' '); \
			total_raw=$$((total_raw + count)); \
		fi; \
		if [ -d "$(PREPROCESSED_INDIVIDUAL_DIR)/$$project" ]; then \
			count=$$(ls -1 "$(PREPROCESSED_INDIVIDUAL_DIR)/$$project" 2>/dev/null | wc -l | tr -d ' '); \
			total_preprocessed=$$((total_preprocessed + count)); \
		fi; \
		if [ -d "$(D4D_INDIVIDUAL_DIR)/gpt5/$$project" ]; then \
			count=$$(ls -1 "$(D4D_INDIVIDUAL_DIR)/gpt5/$$project"/*_d4d.yaml 2>/dev/null | wc -l | tr -d ' '); \
			total_d4d_individual_gpt5=$$((total_d4d_individual_gpt5 + count)); \
		fi; \
		if [ -f "$(D4D_CONCAT_DIR)/gpt5/$${project}_d4d.yaml" ]; then \
			total_d4d_concat_gpt5=$$((total_d4d_concat_gpt5 + 1)); \
		fi; \
	done; \
	if [ -d "$(D4D_HTML_DIR)/concatenated/curated" ]; then \
		total_html=$$(ls -1 "$(D4D_HTML_DIR)/concatenated/curated"/*.html 2>/dev/null | wc -l | tr -d ' '); \
	fi; \
	echo "Total raw downloads:           $$total_raw files"; \
	echo "Total preprocessed individual: $$total_preprocessed files"; \
	echo "Total D4D individual (GPT-5):  $$total_d4d_individual_gpt5 YAMLs"; \
	echo "Total D4D concatenated (GPT-5): $$total_d4d_concat_gpt5 YAMLs"; \
	echo "Total curated HTML:            $$total_html files"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  D4D YAML Size Breakdown"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Individual D4D YAMLs (GPT-5)"
	@echo "────────────────────────────────────────────────────────────────"
	@printf "  %-12s  %5s  %10s  %10s  %s\n" "PROJECT" "FILES" "TOTAL SIZE" "AVG SIZE" "LARGEST"
	@echo "────────────────────────────────────────────────────────────────"
	@for project in $(PROJECTS); do \
		dir="$(D4D_INDIVIDUAL_DIR)/gpt5/$$project"; \
		if [ -d "$$dir" ]; then \
			files=$$(ls -1 "$$dir"/*_d4d.yaml 2>/dev/null | wc -l | tr -d ' '); \
			if [ "$$files" -gt 0 ]; then \
				total_bytes=$$(find "$$dir" -name "*_d4d.yaml" -exec stat -f%z {} \; 2>/dev/null | awk '{s+=$$1} END {print s}'); \
				total_kb=$$(echo "scale=1; $$total_bytes/1024" | bc 2>/dev/null || echo "0"); \
				avg_bytes=$$(echo "scale=0; $$total_bytes/$$files" | bc 2>/dev/null || echo "0"); \
				avg_kb=$$(echo "scale=1; $$avg_bytes/1024" | bc 2>/dev/null || echo "0"); \
				largest=$$(ls -lS "$$dir"/*_d4d.yaml 2>/dev/null | head -1 | awk '{print $$5}'); \
				largest_kb=$$(echo "scale=1; $$largest/1024" | bc 2>/dev/null || echo "0"); \
				printf "  %-12s  %5d  %8s KB  %8s KB  %8s KB\n" \
					"$$project" "$$files" "$$total_kb" "$$avg_kb" "$$largest_kb"; \
			else \
				printf "  %-12s  %5s  %10s  %10s  %s\n" "$$project" "0" "-" "-" "-"; \
			fi; \
		else \
			printf "  %-12s  %5s  %10s  %10s  %s\n" "$$project" "N/A" "-" "-" "-"; \
		fi; \
	done
	@echo ""
	@echo "Concatenated D4D YAMLs"
	@echo "────────────────────────────────────────────────────────────────"
	@printf "  %-12s  %10s  %7s  %10s  %7s  %10s  %7s\n" \
		"PROJECT" "GPT-5" "LINES" "CLAUDE" "LINES" "CURATED" "LINES"
	@echo "────────────────────────────────────────────────────────────────"
	@for project in $(PROJECTS); do \
		gpt5_file="$(D4D_CONCAT_DIR)/gpt5/$${project}_d4d.yaml"; \
		claude_file="$(D4D_CONCAT_DIR)/claudecode/$${project}_d4d.yaml"; \
		curated_file="$(D4D_CONCAT_DIR)/curated/$${project}_curated.yaml"; \
		gpt5_size="-"; gpt5_lines="-"; \
		claude_size="-"; claude_lines="-"; \
		curated_size="-"; curated_lines="-"; \
		if [ -f "$$gpt5_file" ]; then \
			gpt5_bytes=$$(stat -f%z "$$gpt5_file" 2>/dev/null || echo "0"); \
			gpt5_kb=$$(echo "scale=1; $$gpt5_bytes/1024" | bc 2>/dev/null || echo "0"); \
			gpt5_size="$${gpt5_kb}K"; \
			gpt5_lines=$$(wc -l < "$$gpt5_file" 2>/dev/null | tr -d ' ' || echo "0"); \
		fi; \
		if [ -f "$$claude_file" ]; then \
			claude_bytes=$$(stat -f%z "$$claude_file" 2>/dev/null || echo "0"); \
			claude_kb=$$(echo "scale=1; $$claude_bytes/1024" | bc 2>/dev/null || echo "0"); \
			claude_size="$${claude_kb}K"; \
			claude_lines=$$(wc -l < "$$claude_file" 2>/dev/null | tr -d ' ' || echo "0"); \
		fi; \
		if [ -f "$$curated_file" ]; then \
			curated_bytes=$$(stat -f%z "$$curated_file" 2>/dev/null || echo "0"); \
			curated_kb=$$(echo "scale=1; $$curated_bytes/1024" | bc 2>/dev/null || echo "0"); \
			curated_size="$${curated_kb}K"; \
			curated_lines=$$(wc -l < "$$curated_file" 2>/dev/null | tr -d ' ' || echo "0"); \
		fi; \
		printf "  %-12s  %10s  %7s  %10s  %7s  %10s  %7s\n" \
			"$$project" "$$gpt5_size" "$$gpt5_lines" "$$claude_size" "$$claude_lines" "$$curated_size" "$$curated_lines"; \
	done
	@echo ""
	@echo "Size Comparison Summary"
	@echo "────────────────────────────────────────────────────────────────"
	@total_individual=0; \
	total_concat_gpt5=0; \
	total_concat_curated=0; \
	for project in $(PROJECTS); do \
		dir="$(D4D_INDIVIDUAL_DIR)/gpt5/$$project"; \
		if [ -d "$$dir" ]; then \
			bytes=$$(find "$$dir" -name "*_d4d.yaml" -exec stat -f%z {} \; 2>/dev/null | awk '{s+=$$1} END {print s}'); \
			total_individual=$$((total_individual + bytes)); \
		fi; \
		gpt5_file="$(D4D_CONCAT_DIR)/gpt5/$${project}_d4d.yaml"; \
		if [ -f "$$gpt5_file" ]; then \
			bytes=$$(stat -f%z "$$gpt5_file" 2>/dev/null || echo "0"); \
			total_concat_gpt5=$$((total_concat_gpt5 + bytes)); \
		fi; \
		curated_file="$(D4D_CONCAT_DIR)/curated/$${project}_curated.yaml"; \
		if [ -f "$$curated_file" ]; then \
			bytes=$$(stat -f%z "$$curated_file" 2>/dev/null || echo "0"); \
			total_concat_curated=$$((total_concat_curated + bytes)); \
		fi; \
	done; \
	total_individual_kb=$$(echo "scale=1; $$total_individual/1024" | bc); \
	total_concat_gpt5_kb=$$(echo "scale=1; $$total_concat_gpt5/1024" | bc); \
	total_concat_curated_kb=$$(echo "scale=1; $$total_concat_curated/1024" | bc); \
	echo "Total Individual D4D YAMLs (GPT-5):      $${total_individual_kb} KB"; \
	echo "Total Concatenated D4D YAMLs (GPT-5):    $${total_concat_gpt5_kb} KB"; \
	echo "Total Curated D4D YAMLs:                 $${total_concat_curated_kb} KB"
	@echo ""

# Quick data status - compact version
data-status-quick:
	@echo "D4D Pipeline Status:"
	@for project in $(PROJECTS); do \
		raw_count=$$(ls -1 "$(RAW_DIR)/$$project" 2>/dev/null | wc -l | tr -d ' '); \
		prep_count=$$(ls -1 "$(PREPROCESSED_INDIVIDUAL_DIR)/$$project" 2>/dev/null | wc -l | tr -d ' '); \
		d4d_count=$$(ls -1 "$(D4D_INDIVIDUAL_DIR)/gpt5/$$project"/*_d4d.yaml 2>/dev/null | wc -l | tr -d ' '); \
		concat_exists="❌"; \
		if [ -f "$(D4D_CONCAT_DIR)/gpt5/$${project}_d4d.yaml" ]; then \
			concat_exists="✓"; \
		fi; \
		printf "  %-12s : raw=%2d  prep=%2d  d4d=%2d  concat=%s\n" \
			"$$project" "$$raw_count" "$$prep_count" "$$d4d_count" "$$concat_exists"; \
	done

# D4D YAML Size Report - detailed table of all D4D YAML files
data-d4d-sizes:
	@echo "════════════════════════════════════════════════════════════════════════════════"
	@echo "  D4D YAML File Size Report"
	@echo "════════════════════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Individual D4D YAMLs (GPT-5)"
	@echo "────────────────────────────────────────────────────────────────────────────────"
	@printf "  %-12s  %5s  %10s  %10s  %s\n" "PROJECT" "FILES" "TOTAL SIZE" "AVG SIZE" "LARGEST"
	@echo "────────────────────────────────────────────────────────────────────────────────"
	@for project in $(PROJECTS); do \
		dir="$(D4D_INDIVIDUAL_DIR)/gpt5/$$project"; \
		if [ -d "$$dir" ]; then \
			files=$$(ls -1 "$$dir"/*_d4d.yaml 2>/dev/null | wc -l | tr -d ' '); \
			if [ "$$files" -gt 0 ]; then \
				total_bytes=$$(find "$$dir" -name "*_d4d.yaml" -exec stat -f%z {} \; 2>/dev/null | awk '{s+=$$1} END {print s}'); \
				total_kb=$$(echo "scale=1; $$total_bytes/1024" | bc 2>/dev/null || echo "0"); \
				avg_bytes=$$(echo "scale=0; $$total_bytes/$$files" | bc 2>/dev/null || echo "0"); \
				avg_kb=$$(echo "scale=1; $$avg_bytes/1024" | bc 2>/dev/null || echo "0"); \
				largest=$$(ls -lS "$$dir"/*_d4d.yaml 2>/dev/null | head -1 | awk '{print $$5}'); \
				largest_kb=$$(echo "scale=1; $$largest/1024" | bc 2>/dev/null || echo "0"); \
				printf "  %-12s  %5d  %8s KB  %8s KB  %8s KB\n" \
					"$$project" "$$files" "$$total_kb" "$$avg_kb" "$$largest_kb"; \
			else \
				printf "  %-12s  %5s  %10s  %10s  %s\n" "$$project" "0" "-" "-" "-"; \
			fi; \
		else \
			printf "  %-12s  %5s  %10s  %10s  %s\n" "$$project" "N/A" "-" "-" "-"; \
		fi; \
	done
	@echo ""
	@echo "Concatenated D4D YAMLs"
	@echo "────────────────────────────────────────────────────────────────────────────────"
	@printf "  %-12s  %10s  %7s  %10s  %7s  %10s  %7s\n" \
		"PROJECT" "GPT-5" "LINES" "CLAUDE" "LINES" "CURATED" "LINES"
	@echo "────────────────────────────────────────────────────────────────────────────────"
	@for project in $(PROJECTS); do \
		gpt5_file="$(D4D_CONCAT_DIR)/gpt5/$${project}_d4d.yaml"; \
		claude_file="$(D4D_CONCAT_DIR)/claudecode/$${project}_d4d.yaml"; \
		curated_file="$(D4D_CONCAT_DIR)/curated/$${project}_curated.yaml"; \
		gpt5_size="-"; gpt5_lines="-"; \
		claude_size="-"; claude_lines="-"; \
		curated_size="-"; curated_lines="-"; \
		if [ -f "$$gpt5_file" ]; then \
			gpt5_bytes=$$(stat -f%z "$$gpt5_file" 2>/dev/null || echo "0"); \
			gpt5_kb=$$(echo "scale=1; $$gpt5_bytes/1024" | bc 2>/dev/null || echo "0"); \
			gpt5_size="$${gpt5_kb}K"; \
			gpt5_lines=$$(wc -l < "$$gpt5_file" 2>/dev/null | tr -d ' ' || echo "0"); \
		fi; \
		if [ -f "$$claude_file" ]; then \
			claude_bytes=$$(stat -f%z "$$claude_file" 2>/dev/null || echo "0"); \
			claude_kb=$$(echo "scale=1; $$claude_bytes/1024" | bc 2>/dev/null || echo "0"); \
			claude_size="$${claude_kb}K"; \
			claude_lines=$$(wc -l < "$$claude_file" 2>/dev/null | tr -d ' ' || echo "0"); \
		fi; \
		if [ -f "$$curated_file" ]; then \
			curated_bytes=$$(stat -f%z "$$curated_file" 2>/dev/null || echo "0"); \
			curated_kb=$$(echo "scale=1; $$curated_bytes/1024" | bc 2>/dev/null || echo "0"); \
			curated_size="$${curated_kb}K"; \
			curated_lines=$$(wc -l < "$$curated_file" 2>/dev/null | tr -d ' ' || echo "0"); \
		fi; \
		printf "  %-12s  %10s  %7s  %10s  %7s  %10s  %7s\n" \
			"$$project" "$$gpt5_size" "$$gpt5_lines" "$$claude_size" "$$claude_lines" "$$curated_size" "$$curated_lines"; \
	done
	@echo ""
	@echo "Size Comparison Summary"
	@echo "────────────────────────────────────────────────────────────────────────────────"
	@total_individual=0; \
	total_concat_gpt5=0; \
	total_concat_curated=0; \
	for project in $(PROJECTS); do \
		dir="$(D4D_INDIVIDUAL_DIR)/gpt5/$$project"; \
		if [ -d "$$dir" ]; then \
			bytes=$$(find "$$dir" -name "*_d4d.yaml" -exec stat -f%z {} \; 2>/dev/null | awk '{s+=$$1} END {print s}'); \
			total_individual=$$((total_individual + bytes)); \
		fi; \
		gpt5_file="$(D4D_CONCAT_DIR)/gpt5/$${project}_d4d.yaml"; \
		if [ -f "$$gpt5_file" ]; then \
			bytes=$$(stat -f%z "$$gpt5_file" 2>/dev/null || echo "0"); \
			total_concat_gpt5=$$((total_concat_gpt5 + bytes)); \
		fi; \
		curated_file="$(D4D_CONCAT_DIR)/curated/$${project}_curated.yaml"; \
		if [ -f "$$curated_file" ]; then \
			bytes=$$(stat -f%z "$$curated_file" 2>/dev/null || echo "0"); \
			total_concat_curated=$$((total_concat_curated + bytes)); \
		fi; \
	done; \
	total_individual_kb=$$(echo "scale=1; $$total_individual/1024" | bc); \
	total_concat_gpt5_kb=$$(echo "scale=1; $$total_concat_gpt5/1024" | bc); \
	total_concat_curated_kb=$$(echo "scale=1; $$total_concat_curated/1024" | bc); \
	echo "Total Individual D4D YAMLs (GPT-5):      $${total_individual_kb} KB"; \
	echo "Total Concatenated D4D YAMLs (GPT-5):    $${total_concat_gpt5_kb} KB"; \
	echo "Total Curated D4D YAMLs:                 $${total_concat_curated_kb} KB"; \
	echo ""

# D4D Output Diagnostic - comprehensive analysis of input vs output sizes
# Identifies thin outputs and potential input document problems
d4d-output-diagnostic:
	@echo "════════════════════════════════════════════════════════════════════════════════"
	@echo "  D4D Output Diagnostic Report"
	@echo "  Analyzes input sources and output completeness"
	@echo "════════════════════════════════════════════════════════════════════════════════"
	@echo ""
	@printf "%-10s | %6s | %8s | %10s | %10s | %10s | %10s | %10s | %s\n" \
		"PROJECT" "FILES" "IND.SIZE" "CONCAT.IN" "GPT5 YAML" "CC YAML" "GPT5 HTML" "CC HTML" "STATUS"
	@echo "────────────────────────────────────────────────────────────────────────────────"
	@for project in $(PROJECTS); do \
		ind_dir="$(D4D_INDIVIDUAL_DIR)/gpt5/$$project"; \
		concat_file="$(PREPROCESSED_CONCAT_DIR)/$${project}_concatenated.txt"; \
		gpt5_yaml="$(D4D_CONCAT_DIR)/gpt5/$${project}_d4d.yaml"; \
		cc_yaml="$(D4D_CONCAT_DIR)/claudecode/$${project}_d4d.yaml"; \
		gpt5_html="docs/html_output/concatenated/$${project}_d4d_gpt5.html"; \
		cc_html="docs/html_output/concatenated/claudecode/$${project}.html"; \
		\
		file_count="-"; \
		ind_size="-"; \
		concat_size="-"; \
		gpt5_yaml_size="-"; \
		cc_yaml_size="-"; \
		gpt5_html_size="-"; \
		cc_html_size="-"; \
		status="✅"; \
		\
		if [ -d "$$ind_dir" ]; then \
			file_count=$$(ls -1 "$$ind_dir"/*.yaml 2>/dev/null | wc -l | tr -d ' '); \
			ind_bytes=$$(du -sk "$$ind_dir" 2>/dev/null | awk '{print $$1}'); \
			ind_size="$${ind_bytes}K"; \
		fi; \
		if [ -f "$$concat_file" ]; then \
			concat_bytes=$$(stat -f%z "$$concat_file" 2>/dev/null | awk '{printf "%.1f", $$1/1024}'); \
			concat_size="$${concat_bytes}K"; \
		fi; \
		if [ -f "$$gpt5_yaml" ]; then \
			gpt5_bytes=$$(stat -f%z "$$gpt5_yaml" 2>/dev/null | awk '{printf "%.1f", $$1/1024}'); \
			gpt5_yaml_size="$${gpt5_bytes}K"; \
		fi; \
		if [ -f "$$cc_yaml" ]; then \
			cc_bytes=$$(stat -f%z "$$cc_yaml" 2>/dev/null | awk '{printf "%.1f", $$1/1024}'); \
			cc_yaml_size="$${cc_bytes}K"; \
		fi; \
		if [ -f "$$gpt5_html" ]; then \
			gpt5_html_bytes=$$(stat -f%z "$$gpt5_html" 2>/dev/null | awk '{printf "%.1f", $$1/1024}'); \
			gpt5_html_size="$${gpt5_html_bytes}K"; \
		fi; \
		if [ -f "$$cc_html" ]; then \
			cc_html_bytes=$$(stat -f%z "$$cc_html" 2>/dev/null | awk '{printf "%.1f", $$1/1024}'); \
			cc_html_size="$${cc_html_bytes}K"; \
		fi; \
		\
		if [ "$$file_count" != "-" ] && [ "$$file_count" -le 2 ]; then \
			status="⚠️  FEW"; \
		fi; \
		if [ -f "$$concat_file" ]; then \
			concat_kb=$$(stat -f%z "$$concat_file" 2>/dev/null | awk '{print int($$1/1024)}'); \
			if [ "$$concat_kb" -lt 5 ]; then \
				status="⚠️  THIN"; \
			fi; \
		fi; \
		\
		printf "%-10s | %6s | %8s | %10s | %10s | %10s | %10s | %10s | %s\n" \
			"$$project" "$$file_count" "$$ind_size" "$$concat_size" "$$gpt5_yaml_size" "$$cc_yaml_size" \
			"$$gpt5_html_size" "$$cc_html_size" "$$status"; \
	done
	@echo ""
	@echo "Legend:"
	@echo "  FILES      = Number of individual D4D YAML files for this project"
	@echo "  IND.SIZE   = Total size of individual D4D files"
	@echo "  CONCAT.IN  = Size of concatenated input document"
	@echo "  GPT5 YAML  = Size of GPT-5 synthesized D4D YAML output"
	@echo "  CC YAML    = Size of Claude Code synthesized D4D YAML output"
	@echo "  GPT5 HTML  = Size of GPT-5 HTML rendering"
	@echo "  CC HTML    = Size of Claude Code HTML rendering"
	@echo "  STATUS:"
	@echo "    ✅        = Normal output"
	@echo "    ⚠️  FEW   = Only 1-2 input files (may indicate limited source documentation)"
	@echo "    ⚠️  THIN  = Concatenated input <5KB (likely insufficient source material)"
	@echo ""
	@echo "Assessment:"
	@echo "  - Projects with ⚠️  FEW or ⚠️  THIN likely have limited source documentation"
	@echo "  - This is an INPUT PROBLEM, not a processing issue"
	@echo "  - To improve: add more comprehensive source documentation for these projects"
	@echo ""

# ============================================================================
# D4D Pipeline: Step 2 - Concatenate preprocessed files
# ============================================================================

# Concatenate individual D4D YAMLs by project
# This creates a single file per project from data/d4d_individual/gpt5/
concat-extracted:
	@echo "Concatenating individual D4D YAMLs by project..."
	@mkdir -p $(PREPROCESSED_CONCAT_DIR)
	@for project in $(PROJECTS); do \
		input_dir="$(D4D_INDIVIDUAL_DIR)/gpt5/$$project"; \
		output_file="$(PREPROCESSED_CONCAT_DIR)/$${project}_concatenated.txt"; \
		if [ -d "$$input_dir" ] && [ -n "$$(ls -A $$input_dir 2>/dev/null)" ]; then \
			echo "Processing $$project..."; \
			$(RUN) python src/download/concatenate_documents.py -i "$$input_dir" -o "$$output_file" || exit 1; \
		else \
			echo "⚠️  Skipping $$project (no D4D files found)"; \
		fi \
	done
	@echo "✅ All D4D YAMLs concatenated to $(PREPROCESSED_CONCAT_DIR)/"

# Concatenate preprocessed individual files (for creating input to D4D agent)
# This creates a single file per project from data/preprocessed/individual/
concat-preprocessed:
	@echo "Concatenating preprocessed individual files by project..."
	@mkdir -p $(PREPROCESSED_CONCAT_DIR)
	@for project in $(PROJECTS); do \
		input_dir="$(PREPROCESSED_INDIVIDUAL_DIR)/$$project"; \
		output_file="$(PREPROCESSED_CONCAT_DIR)/$${project}_preprocessed.txt"; \
		if [ -d "$$input_dir" ] && [ -n "$$(ls -A $$input_dir 2>/dev/null)" ]; then \
			echo "Processing $$project..."; \
			$(RUN) python src/download/concatenate_documents.py -i "$$input_dir" -o "$$output_file" || exit 1; \
		else \
			echo "⚠️  Skipping $$project (no preprocessed files found)"; \
		fi \
	done
	@echo "✅ All preprocessed files concatenated to $(PREPROCESSED_CONCAT_DIR)/"

# Concatenate raw downloads by project
# This creates a single file per project from data/raw/
concat-raw:
	@echo "Concatenating raw download files by project..."
	@mkdir -p $(PREPROCESSED_CONCAT_DIR)
	@for project in $(PROJECTS); do \
		input_dir="$(RAW_DIR)/$$project"; \
		output_file="$(PREPROCESSED_CONCAT_DIR)/$${project}_raw.txt"; \
		if [ -d "$$input_dir" ] && [ -n "$$(ls -A $$input_dir 2>/dev/null)" ]; then \
			echo "Processing $$project..."; \
			$(RUN) python src/download/concatenate_documents.py -i "$$input_dir" -o "$$output_file" || exit 1; \
		else \
			echo "⚠️  Skipping $$project (no raw files found)"; \
		fi \
	done
	@echo "✅ All raw files concatenated to $(PREPROCESSED_CONCAT_DIR)/"

# Legacy target for backward compatibility
concat-downloads: concat-raw

# Process concatenated D4D documents with D4D agent
# Usage: make process-concat INPUT_FILE=data/sheets_concatenated/AI_READI_concatenated.txt
process-concat:
ifndef INPUT_FILE
	$(error INPUT_FILE is not defined. Usage: make process-concat INPUT_FILE=data/sheets_concatenated/AI_READI_concatenated.txt)
endif
	@echo "Processing concatenated document: $(INPUT_FILE)"
	@if [ ! -d "aurelian" ]; then \
		echo "❌ Error: aurelian directory not found"; \
		echo "Please ensure the aurelian submodule is initialized"; \
		exit 1; \
	fi
	cd aurelian && uv run python ../src/download/process_concatenated_d4d.py -i ../$(INPUT_FILE) \
		$(if $(OUTPUT_FILE),-o ../$(OUTPUT_FILE),) \
		$(if $(MODEL),-m $(MODEL),)

# Process all concatenated files
# This creates comprehensive D4D YAML files for each project
process-all-concat:
	@echo "Processing all concatenated files..."
	@mkdir -p $(D4D_CONCAT_DIR)/gpt5
	@if [ ! -d "aurelian" ]; then \
		echo "❌ Error: aurelian directory not found"; \
		echo "Please ensure the aurelian submodule is initialized"; \
		exit 1; \
	fi
	cd aurelian && uv run python ../src/download/process_concatenated_d4d.py \
		-d ../$(PREPROCESSED_CONCAT_DIR) \
		--output-dir ../$(D4D_CONCAT_DIR)/gpt5
	@echo "✅ All concatenated files processed to $(D4D_CONCAT_DIR)/gpt5/"

# ============================================================================
# D4D Pipeline: Step 3 - Extract D4D metadata from individual files
# ============================================================================

# Extract D4D metadata from individual files using GPT-5 (with validation)
# Usage: make extract-d4d-individual-gpt5 PROJECT=AI_READI
extract-d4d-individual-gpt5:
ifndef PROJECT
	$(error PROJECT is not defined. Usage: make extract-d4d-individual-gpt5 PROJECT=AI_READI)
endif
	@echo "Extracting D4D metadata for $(PROJECT) using GPT-5..."
	@mkdir -p $(D4D_INDIVIDUAL_DIR)/gpt5/$(PROJECT)
	@if [ ! -d "aurelian" ]; then \
		echo "❌ Error: aurelian directory not found"; \
		echo "Please ensure the aurelian submodule is initialized"; \
		exit 1; \
	fi
	cd aurelian && uv run python ../src/download/interactive_d4d_wrapper.py \
		-i ../$(RAW_DIR)/$(PROJECT) \
		-o ../$(D4D_INDIVIDUAL_DIR)/gpt5/$(PROJECT)
	@echo "✅ D4D extraction complete for $(PROJECT)"

# Extract D4D metadata from all projects using GPT-5
extract-d4d-individual-all-gpt5:
	@echo "Extracting D4D metadata for all projects using GPT-5..."
	@for project in $(PROJECTS); do \
		echo ""; \
		echo "═══════════════════════════════════════"; \
		echo "Processing $$project..."; \
		echo "═══════════════════════════════════════"; \
		$(MAKE) extract-d4d-individual-gpt5 PROJECT=$$project || exit 1; \
	done
	@echo ""
	@echo "✅ All projects processed successfully!"

# Extract D4D metadata from individual files using Claude Code (validated)
# Usage: make extract-d4d-individual-claude
#
# NOTE: Current files (generated 2025-11-15) were validated from GPT-5 outputs
# This target documents the validation process and can regenerate metadata
#
extract-d4d-individual-claude:
	@echo "Claude Code individual D4D files:"
	@echo "Current implementation: GPT-5 generated, Claude Code validated"
	@echo "Files location: data/d4d_individual/claudecode/"
	@echo ""
	@find data/d4d_individual/claudecode -name '*_d4d.yaml' | wc -l | xargs echo "Total D4D YAMLs:"
	@find data/d4d_individual/claudecode -name '*_metadata.yaml' | wc -l | xargs echo "Total metadata files:"
	@echo ""
	@echo "To regenerate metadata for existing D4D YAMLs, use:"
	@echo "  python3 src/download/process_individual_d4d_claude_direct.py -i INPUT -o OUTPUT -p PROJECT"

# List all Claude Code individual D4D files
list-d4d-individual-claude:
	@echo "Individual D4D YAMLs (Claude Code validated):"
	@echo ""
	@for project in $(PROJECTS); do \
		echo "$$project:"; \
		find data/d4d_individual/claudecode/$$project -name '*_d4d.yaml' 2>/dev/null | sed 's|.*/||' | sed 's/^/  /' || echo "  (none)"; \
		echo ""; \
	done

# ============================================================================
# D4D Pipeline: Step 4 - Extract D4D from concatenated files
# ============================================================================

# Extract D4D from a single concatenated file using GPT-5
# Usage: make extract-d4d-concat-gpt5 PROJECT=AI_READI
extract-d4d-concat-gpt5:
ifndef PROJECT
	$(error PROJECT is not defined. Usage: make extract-d4d-concat-gpt5 PROJECT=AI_READI)
endif
	@echo "Extracting D4D from concatenated $(PROJECT) files using GPT-5..."
	@mkdir -p $(D4D_CONCAT_DIR)/gpt5
	@if [ ! -d "aurelian" ]; then \
		echo "❌ Error: aurelian directory not found"; \
		echo "Please ensure the aurelian submodule is initialized"; \
		exit 1; \
	fi
	@input_file="$(PREPROCESSED_CONCAT_DIR)/$(PROJECT)_concatenated.txt"; \
	output_file="$(D4D_CONCAT_DIR)/gpt5/$(PROJECT)_d4d.yaml"; \
	if [ -f "$$input_file" ]; then \
		cd aurelian && uv run python ../src/download/process_concatenated_d4d.py \
			-i ../$$input_file -o ../$$output_file; \
		echo "✅ D4D concatenated extraction complete: $$output_file"; \
	else \
		echo "❌ Error: Input file not found: $$input_file"; \
		echo "Run 'make concat-extracted PROJECT=$(PROJECT)' first"; \
		exit 1; \
	fi

# Extract D4D from all concatenated files using GPT-5
extract-d4d-concat-all-gpt5:
	@echo "Extracting D4D from all concatenated files using GPT-5..."
	@for project in $(PROJECTS); do \
		echo ""; \
		echo "═══════════════════════════════════════"; \
		echo "Processing $$project..."; \
		echo "═══════════════════════════════════════"; \
		$(MAKE) extract-d4d-concat-gpt5 PROJECT=$$project || true; \
	done
	@echo ""
	@echo "✅ All concatenated files processed!"

# Extract D4D from a single concatenated file using Claude Code (deterministic)
# Usage: make extract-d4d-concat-claude PROJECT=AI_READI
#
# IMPLEMENTATION NOTES:
# - Uses process_d4d_deterministic.py with Claude Sonnet 4.5 API (temperature=0.0)
# - Standalone script with minimal dependencies (anthropic, pyyaml)
# - Requires ANTHROPIC_API_KEY environment variable
# - Alternative: Claude Code assistant can generate D4D YAMLs directly (see notes/DETERMINISM.md)
# - Current files in data/d4d_concatenated/claudecode/ were generated using Claude Code assistant
#   direct synthesis (2025-11-15) following the same deterministic principles
# - To regenerate using API: run this target with ANTHROPIC_API_KEY set
#
# Deterministic settings:
# - Temperature: 0.0 (maximum determinism)
# - Model: claude-sonnet-4-5-20250929 (date-pinned)
# - Schema: Local file (version-controlled)
# - Prompts: External files (version-controlled)
# - Metadata: Comprehensive provenance tracking with SHA-256 hashes
#
# Limitations:
# - Requires ANTHROPIC_API_KEY and incurs API costs
# - Requires network connectivity
# - Rate limits may apply for batch processing
# - Alternative direct synthesis approach available (no API key needed)
#
extract-d4d-concat-claude:
ifndef PROJECT
	$(error PROJECT is not defined. Usage: make extract-d4d-concat-claude PROJECT=AI_READI)
endif
	@echo "Extracting D4D from concatenated $(PROJECT) files using Claude Code..."
	@echo "Note: This uses Claude Sonnet 4.5 API with deterministic settings (temperature=0.0)"
	@mkdir -p $(D4D_CONCAT_DIR)/claudecode
	@python3 src/download/process_d4d_deterministic.py \
		-i $(PREPROCESSED_CONCAT_DIR)/$(PROJECT)_concatenated.txt \
		-o $(D4D_CONCAT_DIR)/claudecode/$(PROJECT)_d4d.yaml \
		-p $(PROJECT)

# Extract D4D from all concatenated files using Claude Code (deterministic)
# Usage: make extract-d4d-concat-all-claude
#
# IMPLEMENTATION NOTES:
# - Uses process_d4d_deterministic.py --all to process all projects
# - Current files (generated 2025-11-15) used Claude Code assistant direct synthesis
# - To regenerate using API, ensure ANTHROPIC_API_KEY is set before running this target
#
# Limitations (documented in script):
# - Requires ANTHROPIC_API_KEY and incurs API costs
# - Requires network connectivity
# - Rate limits may apply for batch processing
# - Alternative: Claude Code assistant direct synthesis (see notes/DETERMINISM.md)
#
extract-d4d-concat-all-claude:
	@mkdir -p $(D4D_CONCAT_DIR)/claudecode
	@python3 src/download/process_d4d_deterministic.py --all

# ============================================================================
# D4D Pipeline: Interactive Claude Code Approaches (Slash Commands)
# ============================================================================

# D4D Agent Approach - Uses Task tool with parallel agents
# This is an interactive Claude Code approach using the /d4d-agent slash command
# Usage: make d4d-agent PROJECT=AI_READI (or run /d4d-agent in Claude Code)
#
# IMPLEMENTATION NOTES:
# - Uses Task tool with subagent_type='general-purpose' for parallel processing
# - Reads preprocessed source documents
# - Outputs to data/d4d_concatenated/claudecode_agent/
# - Requires running in Claude Code session
#
d4d-agent:
ifndef PROJECT
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  D4D Agent Approach"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "This is an INTERACTIVE Claude Code approach."
	@echo "Use the /d4d-agent slash command in Claude Code, or specify a project:"
	@echo ""
	@echo "Usage: make d4d-agent PROJECT=AI_READI"
	@echo ""
	@echo "Projects available:"
	@for project in $(PROJECTS); do \
		input_file="$(PREPROCESSED_CONCAT_DIR)/$${project}_preprocessed.txt"; \
		if [ -f "$$input_file" ]; then \
			size=$$(ls -lh "$$input_file" | awk '{print $$5}'); \
			echo "  ✓ $$project ($$size)"; \
		else \
			echo "  ✗ $$project (no input file)"; \
		fi; \
	done
	@echo ""
	@echo "Or run in Claude Code: /d4d-agent"
else
	@echo "Setting up D4D Agent extraction for $(PROJECT)..."
	@mkdir -p $(D4D_CONCAT_DIR)/claudecode_agent
	@input_file="$(PREPROCESSED_CONCAT_DIR)/$(PROJECT)_preprocessed.txt"; \
	output_file="$(D4D_CONCAT_DIR)/claudecode_agent/$(PROJECT)_d4d.yaml"; \
	if [ -f "$$input_file" ]; then \
		echo ""; \
		echo "Input:  $$input_file"; \
		echo "Output: $$output_file"; \
		echo ""; \
		echo "To generate D4D, run in Claude Code:"; \
		echo "  /d4d-agent"; \
		echo ""; \
		echo "Or read the input and follow the prompt:"; \
		echo "  1. Read: $$input_file"; \
		echo "  2. Read: src/data_sheets_schema/schema/data_sheets_schema_all.yaml"; \
		echo "  3. Extract D4D metadata using Task tool with parallel agents"; \
		echo "  4. Validate and save to: $$output_file"; \
	else \
		echo "❌ Error: Input file not found: $$input_file"; \
		echo "Run 'make concat-preprocessed' first"; \
		exit 1; \
	fi
endif

# D4D Assistant Approach - Uses in-session synthesis following GitHub Actions workflow
# This is an interactive Claude Code approach using the /d4d-assistant slash command
# Usage: make d4d-assistant PROJECT=AI_READI (or run /d4d-assistant in Claude Code)
#
# IMPLEMENTATION NOTES:
# - Uses in-session synthesis following .github/workflows/d4d_assistant_create.md
# - Sequential processing with Read tool
# - Outputs to data/d4d_concatenated/claudecode_assistant/
# - Requires running in Claude Code session
#
d4d-assistant:
ifndef PROJECT
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  D4D Assistant Approach"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "This is an INTERACTIVE Claude Code approach."
	@echo "Use the /d4d-assistant slash command in Claude Code, or specify a project:"
	@echo ""
	@echo "Usage: make d4d-assistant PROJECT=AI_READI"
	@echo ""
	@echo "Projects available:"
	@for project in $(PROJECTS); do \
		input_file="$(PREPROCESSED_CONCAT_DIR)/$${project}_preprocessed.txt"; \
		if [ -f "$$input_file" ]; then \
			size=$$(ls -lh "$$input_file" | awk '{print $$5}'); \
			echo "  ✓ $$project ($$size)"; \
		else \
			echo "  ✗ $$project (no input file)"; \
		fi; \
	done
	@echo ""
	@echo "Or run in Claude Code: /d4d-assistant"
else
	@echo "Setting up D4D Assistant extraction for $(PROJECT)..."
	@mkdir -p $(D4D_CONCAT_DIR)/claudecode_assistant
	@input_file="$(PREPROCESSED_CONCAT_DIR)/$(PROJECT)_preprocessed.txt"; \
	output_file="$(D4D_CONCAT_DIR)/claudecode_assistant/$(PROJECT)_d4d.yaml"; \
	if [ -f "$$input_file" ]; then \
		echo ""; \
		echo "Input:  $$input_file"; \
		echo "Output: $$output_file"; \
		echo ""; \
		echo "To generate D4D, run in Claude Code:"; \
		echo "  /d4d-assistant"; \
		echo ""; \
		echo "Or follow the workflow manually:"; \
		echo "  1. Read: .github/workflows/d4d_assistant_create.md"; \
		echo "  2. Read: $$input_file"; \
		echo "  3. Read: src/data_sheets_schema/schema/data_sheets_schema_all.yaml"; \
		echo "  4. Extract D4D metadata following the workflow"; \
		echo "  5. Validate and save to: $$output_file"; \
	else \
		echo "❌ Error: Input file not found: $$input_file"; \
		echo "Run 'make concat-preprocessed' first"; \
		exit 1; \
	fi
endif

# Run D4D Agent approach for all projects (interactive)
d4d-agent-all:
	@echo "D4D Agent approach for all projects..."
	@echo ""
	@mkdir -p $(D4D_CONCAT_DIR)/claudecode_agent
	@for project in $(PROJECTS); do \
		$(MAKE) d4d-agent PROJECT=$$project; \
		echo ""; \
	done

# Run D4D Assistant approach for all projects (interactive)
d4d-assistant-all:
	@echo "D4D Assistant approach for all projects..."
	@echo ""
	@mkdir -p $(D4D_CONCAT_DIR)/claudecode_assistant
	@for project in $(PROJECTS); do \
		$(MAKE) d4d-assistant PROJECT=$$project; \
		echo ""; \
	done

# ============================================================================
# D4D Pipeline: Step 5 - Validate D4D YAML files
# ============================================================================

# Validate a single D4D YAML file against the schema
# Usage: make validate-d4d FILE=data/d4d_individual/gpt5/AI_READI/file_d4d.yaml
validate-d4d:
ifndef FILE
	$(error FILE is not defined. Usage: make validate-d4d FILE=path/to/file_d4d.yaml)
endif
	@echo "Validating $(FILE) against D4D schema..."
	$(RUN) linkml-validate -s $(SOURCE_SCHEMA_PATH) -C Dataset $(FILE)
	@echo "✅ Validation successful!"

# Validate all D4D YAMLs for a specific project
# Usage: make validate-d4d-project PROJECT=AI_READI GENERATOR=gpt5
validate-d4d-project:
ifndef PROJECT
	$(error PROJECT is not defined. Usage: make validate-d4d-project PROJECT=AI_READI GENERATOR=gpt5)
endif
ifndef GENERATOR
	GENERATOR := gpt5
endif
	@echo "Validating all D4D YAMLs for $(PROJECT) ($(GENERATOR))..."
	@project_dir="$(D4D_INDIVIDUAL_DIR)/$(GENERATOR)/$(PROJECT)"; \
	if [ -d "$$project_dir" ]; then \
		error_count=0; \
		file_count=0; \
		for file in $$project_dir/*_d4d.yaml; do \
			if [ -f "$$file" ]; then \
				file_count=$$((file_count + 1)); \
				echo "Validating $$(basename $$file)..."; \
				if ! $(RUN) linkml-validate -s $(SOURCE_SCHEMA_PATH) -C Dataset $$file 2>&1; then \
					error_count=$$((error_count + 1)); \
				fi; \
			fi; \
		done; \
		echo ""; \
		echo "═══════════════════════════════════════"; \
		echo "Validation Summary for $(PROJECT):"; \
		echo "  Files checked: $$file_count"; \
		echo "  Errors: $$error_count"; \
		if [ $$error_count -eq 0 ]; then \
			echo "✅ All files valid!"; \
		else \
			echo "❌ $$error_count file(s) failed validation"; \
			exit 1; \
		fi; \
	else \
		echo "❌ Error: Directory not found: $$project_dir"; \
		exit 1; \
	fi

# Validate all D4D YAMLs across all projects
validate-d4d-all:
	@echo "Validating all D4D YAMLs..."
	@GENERATOR=${GENERATOR:-gpt5}; \
	for project in $(PROJECTS); do \
		echo ""; \
		$(MAKE) validate-d4d-project PROJECT=$$project GENERATOR=$$GENERATOR || true; \
	done
	@echo ""
	@echo "✅ Validation complete for all projects!"

# ============================================================================
# D4D Pipeline: Step 6 - Generate HTML from D4D YAMLs
# ============================================================================

# Generate HTML from D4D YAMLs (human-readable format)
gen-d4d-html:
	@echo "Generating HTML from D4D YAMLs..."
	@mkdir -p $(D4D_HTML_DIR)/individual/gpt5
	@mkdir -p $(D4D_HTML_DIR)/individual/claudecode
	@mkdir -p $(D4D_HTML_DIR)/concatenated/gpt5
	@mkdir -p $(D4D_HTML_DIR)/concatenated/claudecode
	$(RUN) python src/html/human_readable_renderer.py
	@echo "✅ HTML generation complete!"

# ============================================================================
# D4D Pipeline: Complete workflows
# ============================================================================

# Complete pipeline for individual files (GPT-5)
d4d-pipeline-individual-gpt5:
	@echo "Running complete D4D pipeline for individual files (GPT-5)..."
	@echo ""
	@echo "Step 1: Extract D4D metadata from individual files"
	$(MAKE) extract-d4d-individual-all-gpt5
	@echo ""
	@echo "Step 2: Validate extracted D4D YAMLs"
	$(MAKE) validate-d4d-all GENERATOR=gpt5
	@echo ""
	@echo "✅ Individual D4D pipeline complete!"

# Complete pipeline for concatenated files (GPT-5)
d4d-pipeline-concatenated-gpt5:
	@echo "Running complete D4D pipeline for concatenated files (GPT-5)..."
	@echo ""
	@echo "Step 1: Concatenate individual D4D YAMLs"
	$(MAKE) concat-extracted
	@echo ""
	@echo "Step 2: Extract D4D from concatenated files"
	$(MAKE) extract-d4d-concat-all-gpt5
	@echo ""
	@echo "Step 3: Validate concatenated D4D YAMLs"
	@for project in $(PROJECTS); do \
		file="$(D4D_CONCAT_DIR)/gpt5/$${project}_d4d.yaml"; \
		if [ -f "$$file" ]; then \
			echo "Validating $$file..."; \
			$(MAKE) validate-d4d FILE=$$file || true; \
		fi; \
	done
	@echo ""
	@echo "Step 4: Generate HTML"
	$(MAKE) gen-d4d-html
	@echo ""
	@echo "✅ Concatenated D4D pipeline complete!"

# Complete end-to-end D4D pipeline (GPT-5)
d4d-pipeline-full-gpt5:
	@echo "Running complete end-to-end D4D pipeline (GPT-5)..."
	@echo ""
	$(MAKE) d4d-pipeline-individual-gpt5
	@echo ""
	$(MAKE) d4d-pipeline-concatenated-gpt5
	@echo ""
	@echo "✅ Complete D4D pipeline finished successfully!"

# ============================================================================
# D4D Pipeline: Step 7 - Evaluation and Comparison
# ============================================================================

# Directories for evaluation
EVAL_DIR = data/evaluation
RUBRIC_DIR = data/rubric

# Evaluate all D4D concatenated files across all methods
evaluate-d4d:
	@echo "Evaluating all D4D concatenated files..."
	@mkdir -p $(EVAL_DIR)
	$(RUN) python src/evaluation/evaluate_d4d.py \
		--base-dir data \
		--rubric10 $(RUBRIC_DIR)/rubric10.txt \
		--rubric20 $(RUBRIC_DIR)/rubric20.txt \
		--projects AI_READI CM4AI VOICE CHORUS \
		--methods curated gpt5 claudecode \
		--output-dir $(EVAL_DIR)
	@echo "✅ Evaluation complete! Results in $(EVAL_DIR)"

# Evaluate a single project
evaluate-d4d-project:
ifndef PROJECT
	$(error PROJECT is not defined. Usage: make evaluate-d4d-project PROJECT=AI_READI)
endif
	@echo "Evaluating project: $(PROJECT)"
	@mkdir -p $(EVAL_DIR)
	$(RUN) python src/evaluation/evaluate_d4d.py \
		--base-dir data \
		--rubric10 $(RUBRIC_DIR)/rubric10.txt \
		--rubric20 $(RUBRIC_DIR)/rubric20.txt \
		--project $(PROJECT) \
		--methods curated gpt5 claudecode \
		--output-dir $(EVAL_DIR)
	@echo "✅ Evaluation complete for $(PROJECT)!"

# View evaluation summary
eval-summary:
	@if [ -f "$(EVAL_DIR)/summary_report.md" ]; then \
		cat $(EVAL_DIR)/summary_report.md; \
	else \
		echo "No summary report found. Run 'make evaluate-d4d' first."; \
	fi

# View detailed evaluation for a specific project and method
eval-details:
ifndef PROJECT
	$(error PROJECT is not defined. Usage: make eval-details PROJECT=AI_READI METHOD=curated)
endif
ifndef METHOD
	$(error METHOD is not defined. Usage: make eval-details PROJECT=AI_READI METHOD=curated)
endif
	@if [ -f "$(EVAL_DIR)/detailed_analysis/$(PROJECT)_$(METHOD)_evaluation.md" ]; then \
		cat $(EVAL_DIR)/detailed_analysis/$(PROJECT)_$(METHOD)_evaluation.md; \
	else \
		echo "No detailed report found for $(PROJECT)/$(METHOD). Run 'make evaluate-d4d' first."; \
	fi

# Clean evaluation results
clean-eval:
	@echo "Cleaning evaluation results..."
	rm -rf $(EVAL_DIR)
	@echo "✅ Evaluation results cleaned!"

# Evaluate individual D4D files (not concatenated)
evaluate-d4d-individual:
	@echo "Evaluating individual D4D files..."
	@mkdir -p $(EVAL_DIR)_individual
	$(RUN) python src/evaluation/evaluate_d4d.py \
		--base-dir data \
		--rubric10 $(RUBRIC_DIR)/rubric10.txt \
		--rubric20 $(RUBRIC_DIR)/rubric20.txt \
		--methods gpt5 claudecode \
		--output-dir $(EVAL_DIR)_individual \
		--individual
	@echo "✅ Individual file evaluation complete! Results in $(EVAL_DIR)_individual"

# View individual evaluation summary
eval-summary-individual:
	@if [ -f "$(EVAL_DIR)_individual/summary_report.md" ]; then \
		cat $(EVAL_DIR)_individual/summary_report.md; \
	else \
		echo "No individual summary report found. Run 'make evaluate-d4d-individual' first."; \
	fi

# Clean individual evaluation results
clean-eval-individual:
	@echo "Cleaning individual evaluation results..."
	rm -rf $(EVAL_DIR)_individual
	@echo "✅ Individual evaluation results cleaned!"

# ============================================================================
# D4D Pipeline: LLM-based Evaluation (Quality Assessment)
# ============================================================================

# Directories for LLM evaluation
EVAL_LLM_DIR = data/evaluation_llm

# LLM-based evaluation of single file
evaluate-d4d-llm:
ifndef FILE
	$(error FILE is not defined. Usage: make evaluate-d4d-llm FILE=data/d4d_concatenated/claudecode/VOICE_d4d.yaml PROJECT=VOICE METHOD=claudecode)
endif
ifndef PROJECT
	$(error PROJECT is not defined)
endif
ifndef METHOD
	$(error METHOD is not defined)
endif
	@echo "🔍 Evaluating $(FILE) with LLM-as-judge..."
	@mkdir -p $(EVAL_LLM_DIR)
	$(RUN) python src/evaluation/evaluate_d4d_llm.py \
		--file $(FILE) \
		--project $(PROJECT) \
		--method $(METHOD) \
		--rubric $(RUBRIC) \
		--output-dir $(EVAL_LLM_DIR)
	@echo "✅ LLM evaluation complete!"

# Batch evaluation with rubric10
evaluate-d4d-llm-rubric10:
	@echo "🔍 Evaluating all D4D files with Rubric10 (LLM)..."
	@mkdir -p $(EVAL_LLM_DIR)/rubric10
	$(RUN) python src/evaluation/evaluate_d4d_llm.py \
		--all \
		--rubric rubric10 \
		--output-dir $(EVAL_LLM_DIR)
	@echo "✅ Rubric10 LLM evaluation complete! Results in $(EVAL_LLM_DIR)/rubric10"

# Batch evaluation with rubric20
evaluate-d4d-llm-rubric20:
	@echo "🔍 Evaluating all D4D files with Rubric20 (LLM)..."
	@mkdir -p $(EVAL_LLM_DIR)/rubric20
	$(RUN) python src/evaluation/evaluate_d4d_llm.py \
		--all \
		--rubric rubric20 \
		--output-dir $(EVAL_LLM_DIR)
	@echo "✅ Rubric20 LLM evaluation complete! Results in $(EVAL_LLM_DIR)/rubric20"

# Evaluate with both rubrics
evaluate-d4d-llm-both:
	@echo "🔍 Evaluating all D4D files with both rubrics (LLM)..."
	@mkdir -p $(EVAL_LLM_DIR)
	$(RUN) python src/evaluation/evaluate_d4d_llm.py \
		--all \
		--rubric both \
		--output-dir $(EVAL_LLM_DIR)
	@echo "✅ LLM evaluation complete! Results in $(EVAL_LLM_DIR)"

# Compare LLM vs presence-based evaluation
compare-evaluations:
	@echo "📊 Comparing LLM-based vs presence-based evaluation..."
	$(RUN) python src/evaluation/compare_evaluation_methods.py \
		--llm-dir $(EVAL_LLM_DIR) \
		--presence-dir $(EVAL_DIR) \
		--output-dir data/evaluation_comparison
	@echo "✅ Comparison complete! Results in data/evaluation_comparison"

# View LLM evaluation summaries
eval-llm-summary:
	@echo "📋 LLM-based Evaluation Summary (Rubric10):"
	@echo "==========================================="
	@if [ -f "$(EVAL_LLM_DIR)/rubric10/summary_report.md" ]; then \
		cat $(EVAL_LLM_DIR)/rubric10/summary_report.md; \
	else \
		echo "No rubric10 summary found. Run 'make evaluate-d4d-llm-rubric10' first."; \
	fi
	@echo ""
	@echo "📋 LLM-based Evaluation Summary (Rubric20):"
	@echo "==========================================="
	@if [ -f "$(EVAL_LLM_DIR)/rubric20/summary_report.md" ]; then \
		cat $(EVAL_LLM_DIR)/rubric20/summary_report.md; \
	else \
		echo "No rubric20 summary found. Run 'make evaluate-d4d-llm-rubric20' first."; \
	fi

# Clean LLM evaluation results
clean-eval-llm:
	@echo "Cleaning LLM evaluation results..."
	rm -rf $(EVAL_LLM_DIR)
	@echo "✅ LLM evaluation results cleaned!"

# ==================================================================================
# LLM Evaluation - Batch Processing (Reproducible Workflows)
# ==================================================================================

# Batch evaluate all concatenated D4D files
evaluate-d4d-llm-batch-concatenated:
	@echo "Running batch LLM evaluation on concatenated D4D files..."
	@echo "This will evaluate all projects (AI_READI, CHORUS, CM4AI, VOICE)"
	@echo "across all methods (curated, gpt5, claudecode_agent, claudecode_assistant)"
	@echo "with both rubrics (rubric10, rubric20)"
	@echo ""
	@if [ -z "$$ANTHROPIC_API_KEY" ]; then \
		echo "❌ ERROR: ANTHROPIC_API_KEY environment variable is not set"; \
		echo ""; \
		echo "Please set your Anthropic API key:"; \
		echo "  export ANTHROPIC_API_KEY=sk-ant-your-key-here"; \
		echo ""; \
		exit 1; \
	fi
	./src/evaluation/batch_evaluate_concatenated.sh --output-dir $(EVAL_LLM_DIR)

# Batch evaluate with dry-run (preview what would be evaluated)
evaluate-d4d-llm-batch-dry-run:
	@echo "Dry run: showing files that would be evaluated..."
	./src/evaluation/batch_evaluate_concatenated.sh --dry-run

# Batch evaluate all individual D4D files
evaluate-d4d-llm-batch-individual:
	@echo "⚠️  WARNING: This will evaluate ~85 individual D4D files"
	@echo "   Estimated time: ~2 hours"
	@echo "   Estimated cost: ~$$34"
	@echo ""
	@if [ -z "$$ANTHROPIC_API_KEY" ]; then \
		echo "❌ ERROR: ANTHROPIC_API_KEY environment variable is not set"; \
		echo ""; \
		echo "Please set your Anthropic API key:"; \
		echo "  export ANTHROPIC_API_KEY=sk-ant-your-key-here"; \
		echo ""; \
		exit 1; \
	fi
	./src/evaluation/batch_evaluate_individual.sh --output-dir data/evaluation_llm_individual

# Batch evaluate individual files (specific project or method)
evaluate-d4d-llm-batch-individual-filtered:
	@echo "Evaluating individual D4D files with filters..."
	@if [ -z "$$ANTHROPIC_API_KEY" ]; then \
		echo "❌ ERROR: ANTHROPIC_API_KEY environment variable is not set"; \
		exit 1; \
	fi
	@if [ -n "$(PROJECT)" ]; then \
		./src/evaluation/batch_evaluate_individual.sh --project $(PROJECT) --output-dir data/evaluation_llm_individual; \
	elif [ -n "$(METHOD)" ]; then \
		./src/evaluation/batch_evaluate_individual.sh --method $(METHOD) --output-dir data/evaluation_llm_individual; \
	else \
		echo "❌ ERROR: Specify PROJECT=name or METHOD=name"; \
		echo "Example: make evaluate-d4d-llm-batch-individual-filtered PROJECT=VOICE"; \
		echo "Example: make evaluate-d4d-llm-batch-individual-filtered METHOD=claudecode_agent"; \
		exit 1; \
	fi

# Complete batch evaluation (concatenated + individual)
evaluate-d4d-llm-batch-all:
	@echo "═══════════════════════════════════════════════════════════"
	@echo "COMPLETE BATCH LLM EVALUATION"
	@echo "═══════════════════════════════════════════════════════════"
	@echo ""
	@echo "This will run:"
	@echo "  1. Concatenated files (~15 files, ~25 min, ~$$6)"
	@echo "  2. Individual files (~85 files, ~2 hours, ~$$34)"
	@echo "  Total: ~100 files, ~2.5 hours, ~$$40"
	@echo ""
	@if [ -z "$$ANTHROPIC_API_KEY" ]; then \
		echo "❌ ERROR: ANTHROPIC_API_KEY environment variable is not set"; \
		exit 1; \
	fi
	@read -p "Proceed with complete evaluation? [y/N] " -n 1 -r; \
	echo ""; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(MAKE) evaluate-d4d-llm-batch-concatenated && \
		$(MAKE) evaluate-d4d-llm-batch-individual; \
	else \
		echo "Evaluation cancelled"; \
		exit 1; \
	fi
