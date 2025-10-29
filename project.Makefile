## Add your own custom Makefile targets here

SCHEMA_EXAMPLEDIR = src/data/examples
VALID_EXAMPLEDIR = $(SCHEMA_EXAMPLEDIR)/valid
INVALID_EXAMPLEDIR = $(SCHEMA_EXAMPLEDIR)/invalid
SCHEMA_CLASSES = $(shell $(RUN) yq -cr '.classes | keys | join(" ")' $(SOURCE_SCHEMA_PATH))

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

# Concatenate extracted D4D documents by column
# This creates a single file per project column from data/extracted_by_column
concat-extracted:
	@echo "Concatenating extracted D4D documents by column..."
	@mkdir -p data/concatenated
	@for column_dir in data/extracted_by_column/*/; do \
		if [ -d "$$column_dir" ]; then \
			column_name=$$(basename "$$column_dir"); \
			output_file="data/concatenated/$${column_name}_d4d.txt"; \
			echo "Processing $$column_name..."; \
			$(RUN) python src/download/concatenate_documents.py -i "$$column_dir" -o "$$output_file" || exit 1; \
		fi \
	done
	@echo "✅ All columns concatenated to data/concatenated/"

# Concatenate documents from downloads_by_column subdirectories
# This creates a single file per project column from raw downloads
concat-downloads:
	@echo "Concatenating downloaded documents by column..."
	@mkdir -p data/concatenated
	@for column_dir in downloads_by_column/*/; do \
		if [ -d "$$column_dir" ]; then \
			column_name=$$(basename "$$column_dir"); \
			output_file="data/concatenated/$${column_name}_raw.txt"; \
			echo "Processing $$column_name..."; \
			$(RUN) python src/download/concatenate_documents.py -i "$$column_dir" -o "$$output_file" || exit 1; \
		fi \
	done
	@echo "✅ All downloads concatenated to data/concatenated/"

# Process concatenated D4D documents with D4D agent
# Usage: make process-concat INPUT_FILE=data/concatenated/AI_READI_d4d.txt
process-concat:
ifndef INPUT_FILE
	$(error INPUT_FILE is not defined. Usage: make process-concat INPUT_FILE=data/concatenated/AI_READI_d4d.txt)
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

# Process all concatenated D4D documents in data/concatenated/
# This creates synthesized D4D YAML files for each column
process-all-concat:
	@echo "Processing all concatenated D4D documents..."
	@mkdir -p data/synthesized
	@if [ ! -d "aurelian" ]; then \
		echo "❌ Error: aurelian directory not found"; \
		echo "Please ensure the aurelian submodule is initialized"; \
		exit 1; \
	fi
	cd aurelian && uv run python ../src/download/process_concatenated_d4d.py -d ../data/concatenated --output-dir ../data/synthesized
	@echo "✅ All concatenated files processed to data/synthesized/"
