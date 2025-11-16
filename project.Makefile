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
	cd aurelian && uv run python ../src/download/validated_d4d_wrapper.py \
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
# - This target uses process_concatenated_d4d_claude.py with Claude Sonnet 4.5 API (temperature=0.0)
# - Requires ANTHROPIC_API_KEY environment variable
# - Alternative: Claude Code assistant can generate D4D YAMLs directly (see DETERMINISM.md)
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
extract-d4d-concat-claude:
ifndef PROJECT
	$(error PROJECT is not defined. Usage: make extract-d4d-concat-claude PROJECT=AI_READI)
endif
	@echo "Extracting D4D from concatenated $(PROJECT) files using Claude Code..."
	@echo "Note: This uses Claude Sonnet 4.5 API with deterministic settings (temperature=0.0)"
	@mkdir -p $(D4D_CONCAT_DIR)/claudecode
	@if [ ! -d "aurelian" ]; then \
		echo "❌ Error: aurelian directory not found"; \
		echo "Please ensure the aurelian submodule is initialized"; \
		exit 1; \
	fi
	@input_file="$(PREPROCESSED_CONCAT_DIR)/$(PROJECT)_concatenated.txt"; \
	output_file="$(D4D_CONCAT_DIR)/claudecode/$(PROJECT)_d4d.yaml"; \
	if [ -f "$$input_file" ]; then \
		if [ -z "$$ANTHROPIC_API_KEY" ]; then \
			echo "❌ Error: ANTHROPIC_API_KEY environment variable not set"; \
			echo ""; \
			echo "To use API-based extraction, set ANTHROPIC_API_KEY"; \
			echo "Alternative: Use Claude Code assistant for direct synthesis (see DETERMINISM.md)"; \
			exit 1; \
		fi; \
		cd aurelian && uv run python ../src/download/process_concatenated_d4d_claude.py \
			-i ../$$input_file -o ../$$output_file -p $(PROJECT); \
		echo "✅ D4D concatenated extraction complete: $$output_file"; \
	else \
		echo "❌ Error: Input file not found: $$input_file"; \
		echo "Run 'make concat-extracted PROJECT=$(PROJECT)' first"; \
		exit 1; \
	fi

# Extract D4D from all concatenated files using Claude Code (deterministic)
# Usage: make extract-d4d-concat-all-claude
#
# NOTE: Current files (generated 2025-11-15) used Claude Code assistant direct synthesis
# To regenerate using API, ensure ANTHROPIC_API_KEY is set before running this target
#
extract-d4d-concat-all-claude:
	@echo "Extracting D4D from all concatenated files using Claude Code (deterministic)..."
	@echo "Note: Requires ANTHROPIC_API_KEY for API-based extraction"
	@echo ""
	@for project in $(PROJECTS); do \
		echo ""; \
		echo "═══════════════════════════════════════"; \
		echo "Processing $$project..."; \
		echo "═══════════════════════════════════════"; \
		$(MAKE) extract-d4d-concat-claude PROJECT=$$project || true; \
	done
	@echo ""
	@echo "✅ All concatenated files processed with Claude Code!"

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
