MAKEFLAGS += --warn-undefined-variables
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help
.DELETE_ON_ERROR:
.SUFFIXES:
.SECONDARY:

RUN = poetry run
# get values from about.yaml file
SCHEMA_NAME = $(shell ${SHELL} ./utils/get-value.sh name)
SOURCE_SCHEMA_PATH = $(shell ${SHELL} ./utils/get-value.sh source_schema_path)
SOURCE_SCHEMA_DIR = $(dir $(SOURCE_SCHEMA_PATH))
SOURCE_SCHEMA_ALL = $(SOURCE_SCHEMA_DIR)$(patsubst %.yaml,%_all.yaml,$(notdir $(SOURCE_SCHEMA_PATH)))
SRC = src
DEST = project
PYMODEL = $(SRC)/$(SCHEMA_NAME)/datamodel
DOCDIR = docs
EXAMPLEDIR = examples
SHEET_MODULE = personinfo_enums
SHEET_ID = $(shell ${SHELL} ./utils/get-value.sh google_sheet_id)
SHEET_TABS = $(shell ${SHELL} ./utils/get-value.sh google_sheet_tabs)
SHEET_MODULE_PATH = $(SOURCE_SCHEMA_DIR)/$(SHEET_MODULE).yaml

# environment variables
include config.env

GEN_PARGS =
ifdef LINKML_GENERATORS_PROJECT_ARGS
GEN_PARGS = ${LINKML_GENERATORS_PROJECT_ARGS}
endif

GEN_DARGS =
ifdef LINKML_GENERATORS_MARKDOWN_ARGS
GEN_DARGS = ${LINKML_GENERATORS_MARKDOWN_ARGS}
endif


# basename of a YAML file in model/
.PHONY: all clean

# note: "help" MUST be the first target in the file,
# when the user types "make" they should get help info
help: status
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  Setup & Development"
	@echo "════════════════════════════════════════════════════════════════"
	@echo "make setup           -- initial setup (run this first)"
	@echo "make install         -- install dependencies"
	@echo "make test            -- runs tests"
	@echo "make test-modules    -- validate all D4D module schemas"
	@echo "make check-sync      -- check if schema files are in sync"
	@echo "make regen-all       -- force regenerate all schema artifacts"
	@echo "make lint            -- perform linting"
	@echo "make lint-modules    -- lint all D4D module schemas"
	@echo "make site            -- makes site locally"
	@echo "make testdoc         -- builds docs and runs local test server"
	@echo "make deploy          -- deploys site"
	@echo "make update          -- updates linkml version"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  D4D Pipeline: Status & Monitoring"
	@echo "════════════════════════════════════════════════════════════════"
	@echo "make data-status                       -- full data status report with counts"
	@echo "make data-status-quick                 -- compact status overview"
	@echo "make data-d4d-sizes                    -- detailed D4D YAML size report"
	@echo "make d4d-output-diagnostic             -- diagnose thin outputs and input problems"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  D4D Pipeline: Download & Preprocess Sources"
	@echo "════════════════════════════════════════════════════════════════"
	@echo "make download-sources          -- download from Bridge2AI Google Sheet"
	@echo "make download-sources-dry-run  -- analyze sheet without downloading"
	@echo "make download-sheet            -- download from custom sheet"
	@echo "                                  (usage: SHEET_URL=\"https://...\")"
	@echo "make preprocess-sources        -- copy text files to preprocessed/"
	@echo "make download-and-preprocess   -- full download + preprocess pipeline"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  D4D Pipeline: Concatenation"
	@echo "════════════════════════════════════════════════════════════════"
	@echo "make concat-extracted      -- concatenate individual D4D YAMLs by project"
	@echo "make concat-preprocessed   -- concatenate preprocessed files by project"
	@echo "make concat-raw            -- concatenate raw downloads by project"
	@echo "make concat-docs           -- concatenate documents from directory"
	@echo "                              (usage: INPUT_DIR=dir OUTPUT_FILE=file)"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  D4D Pipeline: Extraction (Individual Files)"
	@echo "════════════════════════════════════════════════════════════════"
	@echo "make extract-d4d-individual-gpt5       -- extract D4D for one project"
	@echo "                                          (usage: PROJECT=AI_READI)"
	@echo "make extract-d4d-individual-all-gpt5   -- extract D4D for all projects"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  D4D Pipeline: Extraction (Concatenated Files)"
	@echo "════════════════════════════════════════════════════════════════"
	@echo "make extract-d4d-concat-gpt5       -- extract D4D from concatenated file (GPT-5)"
	@echo "                                      (usage: PROJECT=AI_READI)"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  D4D Pipeline: RO-Crate Transformation"
	@echo "════════════════════════════════════════════════════════════════"
	@echo "make rocrate-to-d4d           -- transform single RO-Crate to D4D YAML"
	@echo "                                 (usage: INPUT=rocrate.json OUTPUT=d4d.yaml)"
	@echo "make merge-rocrates           -- merge multiple RO-Crates into comprehensive D4D"
	@echo "                                 (usage: INPUTS=\"file1.json file2.json\" OUTPUT=d4d.yaml)"
	@echo "make auto-process-rocrates    -- auto-discover and process all RO-Crates in directory"
	@echo "                                 (usage: DIR=data/ro-crate/PROJECT OUTPUT=d4d.yaml)"
	@echo "make merge-cm4ai-rocrates     -- merge all CM4AI RO-Crates (release + 2 sub-crates)"
	@echo "make test-rocrate-transform   -- test single-file transformation"
	@echo "make test-rocrate-merge       -- test multi-file merge (CM4AI top 2)"
	@echo "make extract-d4d-concat-all-gpt5   -- extract D4D from all concatenated (GPT-5)"
	@echo "make extract-d4d-concat-claude     -- extract D4D from concatenated file (Claude API)"
	@echo "                                      (usage: PROJECT=AI_READI)"
	@echo "make extract-d4d-concat-all-claude -- extract D4D from all concatenated (Claude API)"
	@echo "make process-concat                -- process single concatenated doc"
	@echo "                                      (usage: INPUT_FILE=file)"
	@echo "make process-all-concat            -- process all concatenated docs"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  D4D Pipeline: Interactive Claude Code (Slash Commands)"
	@echo "════════════════════════════════════════════════════════════════"
	@echo "make d4d-agent                     -- show D4D Agent approach info"
	@echo "                                      (usage: PROJECT=AI_READI)"
	@echo "make d4d-agent-all                 -- setup all projects for Agent approach"
	@echo "make d4d-assistant                 -- show D4D Assistant approach info"
	@echo "                                      (usage: PROJECT=AI_READI)"
	@echo "make d4d-assistant-all             -- setup all projects for Assistant approach"
	@echo ""
	@echo "  Interactive commands (run in Claude Code):"
	@echo "    /d4d-agent                     -- parallel agents with Task tool"
	@echo "    /d4d-assistant                 -- in-session synthesis"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  D4D Pipeline: Validation"
	@echo "════════════════════════════════════════════════════════════════"
	@echo "make validate-d4d                  -- validate single D4D YAML"
	@echo "                                      (usage: FILE=path/to/file.yaml)"
	@echo "make validate-d4d-project          -- validate all YAMLs for project"
	@echo "                                      (usage: PROJECT=AI_READI GENERATOR=gpt5)"
	@echo "make validate-d4d-all              -- validate all D4D YAMLs"
	@echo "                                      (usage: GENERATOR=gpt5)"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  D4D Pipeline: HTML Generation"
	@echo "════════════════════════════════════════════════════════════════"
	@echo "make gen-d4d-html                  -- generate HTML from D4D YAMLs"
	@echo "make gen-html                      -- alias for gen-d4d-html"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  D4D Pipeline: Complete Workflows"
	@echo "════════════════════════════════════════════════════════════════"
	@echo "make d4d-pipeline-individual-gpt5     -- full pipeline for individual files"
	@echo "make d4d-pipeline-concatenated-gpt5   -- full pipeline for concatenated files"
	@echo "make d4d-pipeline-full-gpt5           -- complete end-to-end pipeline"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "make help            -- show this help"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""

status: check-config
	@echo "Project: $(SCHEMA_NAME)"
	@echo "Source: $(SOURCE_SCHEMA_PATH)"

# generate products and add everything to github
setup: install gen-project gen-examples gendoc git-init-add

# install any dependencies required for building
install:
	git init
	poetry install
.PHONY: install

# ---
# Project Syncronization
# ---
#
# check we are up to date
check: cruft-check
cruft-check:
	cruft check
cruft-diff:
	cruft diff

update: update-template update-linkml
update-template:
	cruft update

# todo: consider pinning to template
update-linkml:
	poetry add -D linkml@latest

# EXPERIMENTAL
create-data-harmonizer:
	npm init data-harmonizer $(SOURCE_SCHEMA_PATH)

all: site
site: gen-project gendoc
%.yaml: gen-project
deploy: all mkd-gh-deploy

compile-sheets:
	$(RUN) sheets2linkml --gsheet-id $(SHEET_ID) $(SHEET_TABS) > $(SHEET_MODULE_PATH).tmp && mv $(SHEET_MODULE_PATH).tmp $(SHEET_MODULE_PATH)

# In future this will be done by conversion
gen-examples:
	cp src/data/examples/* $(EXAMPLEDIR)

# Build the combined schema
# Also write proper yaml header to it
.PHONY: full-schema
full-schema: $(SOURCE_SCHEMA_ALL)

$(SOURCE_SCHEMA_ALL):
	@echo "Generating D4D-Full schema with merged imports..."
	$(RUN) gen-linkml -o $@ -f 'yaml' $(SOURCE_SCHEMA_PATH)
	@echo '---' | cat - $@ > $@.tmp && mv $@.tmp $@

# generates all project files

gen-project: $(PYMODEL) $(SOURCE_SCHEMA_ALL)
	$(RUN) gen-project -I python -I jsonschema -I jsonld -I owl ${GEN_PARGS} -d $(DEST) $(SOURCE_SCHEMA_PATH) && mv $(DEST)/*.py $(PYMODEL)


test: test-schema test-python test-examples

# Test the schema - use the full materialized version
test-schema: $(SOURCE_SCHEMA_ALL)
	$(RUN) gen-project ${GEN_PARGS} -d tmp $(SOURCE_SCHEMA_ALL)

# Test individual D4D module schemas
test-modules:
	@echo "Validating all D4D module schemas..."
	@for module in $(SOURCE_SCHEMA_DIR)D4D_*.yaml; do \
		echo "Validating $$module..."; \
		$(RUN) gen-project -d tmp $$module || exit 1; \
	done
	@echo "All D4D module schemas validated successfully!"

test-python:
	$(RUN) python -m unittest discover

lint:
	$(RUN) linkml-lint $(SOURCE_SCHEMA_PATH)

# Lint all D4D module schemas
lint-modules:
	@echo "Linting all D4D module schemas..."
	@for module in $(SOURCE_SCHEMA_DIR)D4D_*.yaml; do \
		echo "Linting $$module..."; \
		$(RUN) linkml-lint $$module || exit 1; \
	done
	@echo "All D4D module schemas linted successfully!"

# Check if schema files are in sync (source, merged, Python model)
check-sync:
	@./utils/check-schema-sync.sh

# Force regenerate all schema artifacts (merged YAML + Python model + all exports)
regen-all:
	@echo "Force regenerating all schema artifacts..."
	@rm -f $(SOURCE_SCHEMA_ALL)
	@$(MAKE) full-schema
	@$(MAKE) gen-project
	@echo "All schema artifacts regenerated successfully!"

check-config:
	@(grep my-datamodel about.yaml > /dev/null && printf "\n**Project not configured**:\n\n  - Remember to edit 'about.yaml'\n\n" || exit 0)

convert-examples-to-%:
	$(patsubst %, $(RUN) linkml-convert  % -s $(SOURCE_SCHEMA_PATH) -C Person, $(shell ${SHELL} find src/data/examples -name "*.yaml"))

examples/%.yaml: src/data/examples/%.yaml
	$(RUN) linkml-convert -s $(SOURCE_SCHEMA_PATH) -C Person $< -o $@
examples/%.json: src/data/examples/%.yaml
	$(RUN) linkml-convert -s $(SOURCE_SCHEMA_PATH) -C Person $< -o $@
examples/%.ttl: src/data/examples/%.yaml
	$(RUN) linkml-convert -P EXAMPLE=http://example.org/ -s $(SOURCE_SCHEMA_PATH) -C Person $< -o $@

test-examples: full-schema examples/output

examples/output: src/data_sheets_schema/schema/data_sheets_schema_all.yaml
	mkdir -p $@
	$(RUN) linkml-run-examples \
		--output-formats json \
		--output-formats yaml \
		--counter-example-input-directory src/data/examples/invalid \
		--input-directory src/data/examples/valid \
		--output-directory $@ \
		--schema $< > $@/README.md

# Test documentation locally
serve: mkd-serve

# Python datamodel
$(PYMODEL):
	mkdir -p $@


$(DOCDIR):
	mkdir -p $@

gendoc: $(DOCDIR)
	cp $(SRC)/docs/*md $(DOCDIR) ; \
	$(RUN) gen-doc ${GEN_DARGS} -d $(DOCDIR) $(SOURCE_SCHEMA_PATH) ; \
	mkdir -p $(DOCDIR)/html_output/concatenated ; \
	mkdir -p $(DOCDIR)/html_output/concatenated/curated ; \
	mkdir -p $(DOCDIR)/html_output/concatenated/claudecode ; \
	mkdir -p $(DOCDIR)/yaml_output/concatenated/gpt5 ; \
	mkdir -p $(DOCDIR)/yaml_output/concatenated/curated ; \
	mkdir -p $(DOCDIR)/yaml_output/concatenated/claudecode ; \
	cp -r $(SRC)/html/output/*.html $(DOCDIR)/html_output/ 2>/dev/null || true ; \
	cp -r $(SRC)/html/output/concatenated/*.html $(DOCDIR)/html_output/concatenated/ 2>/dev/null || true ; \
	cp $(SRC)/html/output/*.css $(DOCDIR)/html_output/ 2>/dev/null || true ; \
	cp -r data/d4d_html/concatenated/curated/*.html $(DOCDIR)/html_output/concatenated/curated/ 2>/dev/null || true ; \
	cp -r data/d4d_html/concatenated/claudecode/*.html $(DOCDIR)/html_output/concatenated/claudecode/ 2>/dev/null || true ; \
	cp -r data/d4d_html/concatenated/claudecode_agent/*.html $(DOCDIR)/html_output/ 2>/dev/null || true ; \
	cp data/d4d_concatenated/gpt5/*_d4d.yaml $(DOCDIR)/yaml_output/concatenated/gpt5/ 2>/dev/null || true ; \
	cp data/d4d_concatenated/curated/*_curated.yaml $(DOCDIR)/yaml_output/concatenated/curated/ 2>/dev/null || true ; \
	cp data/d4d_concatenated/claudecode/*_d4d.yaml $(DOCDIR)/yaml_output/concatenated/claudecode/ 2>/dev/null || true ; \
	cp data/d4d_concatenated/claudecode/*_metadata.yaml $(DOCDIR)/yaml_output/concatenated/claudecode/ 2>/dev/null || true

testdoc: gendoc serve

MKDOCS = $(RUN) mkdocs
mkd-%:
	$(MKDOCS) $*

PROJECT_FOLDERS = sqlschema shex shacl protobuf prefixmap owl jsonschema jsonld graphql excel
git-init-add: git-init git-add git-commit git-status
git-init:
	git init
git-add: .cruft.json
	git add .gitignore .github .cruft.json Makefile LICENSE *.md examples utils about.yaml mkdocs.yml poetry.lock project.Makefile pyproject.toml src/data_sheets_schema/schema/*yaml src/*/datamodel/*py src/data src/docs tests src/*/_version.py
	git add $(patsubst %, project/%, $(PROJECT_FOLDERS))
git-commit:
	git commit -m 'chore: initial commit' -a
git-status:
	git status

# only necessary if setting up via cookiecutter
.cruft.json:
	echo "creating a stub for .cruft.json. IMPORTANT: setup via cruft not cookiecutter recommended!" ; \
	touch $@

clean:
	rm -rf $(DEST)
	rm -rf tmp
	rm -fr docs/*
	rm -fr $(PYMODEL)/*

# ════════════════════════════════════════════════════════════════
# RO-Crate to D4D Transformation
# ════════════════════════════════════════════════════════════════

# Default paths for RO-Crate transformation
ROCRATE_MAPPING = data/ro-crate_mapping/D4D - RO-Crate - RAI Mappings.xlsx - Class Alignment.tsv
ROCRATE_SCHEMA = $(SOURCE_SCHEMA_ALL)

# Transform RO-Crate JSON-LD to D4D YAML
# Usage: make rocrate-to-d4d INPUT=rocrate.json OUTPUT=d4d.yaml
rocrate-to-d4d:
ifndef INPUT
	$(error INPUT is required. Usage: make rocrate-to-d4d INPUT=rocrate.json OUTPUT=d4d.yaml)
endif
ifndef OUTPUT
	$(error OUTPUT is required. Usage: make rocrate-to-d4d INPUT=rocrate.json OUTPUT=d4d.yaml)
endif
	@echo "Transforming RO-Crate to D4D..."
	$(RUN) python .claude/agents/scripts/rocrate_to_d4d.py \
		--input $(INPUT) \
		--output $(OUTPUT) \
		--mapping "$(ROCRATE_MAPPING)" \
		--schema $(ROCRATE_SCHEMA) \
		--validate

# Test RO-Crate transformation with minimal example
test-rocrate-transform:
	@echo "Testing RO-Crate transformation with minimal example..."
	@mkdir -p data/test
	$(RUN) python .claude/agents/scripts/rocrate_to_d4d.py \
		--input data/test/minimal-ro-crate.json \
		--output data/test/minimal_d4d.yaml \
		--mapping "$(ROCRATE_MAPPING)" \
		--schema $(ROCRATE_SCHEMA) \
		--validate
	@echo ""
	@echo "Generated files:"
	@echo "  D4D YAML:            data/test/minimal_d4d.yaml"
	@echo "  Transformation report: data/test/transformation_report.txt"
	@echo "  Validation errors:    data/test/minimal_d4d_validation_errors.txt (if any)"

# Multi-RO-Crate Merging
# ════════════════════════════════════════════════════════════════

# Merge multiple RO-Crate files into comprehensive D4D
# Usage: make merge-rocrates INPUTS="file1.json file2.json file3.json" OUTPUT=merged.yaml
merge-rocrates:
ifndef INPUTS
	$(error INPUTS is required. Usage: make merge-rocrates INPUTS="file1.json file2.json" OUTPUT=merged.yaml)
endif
ifndef OUTPUT
	$(error OUTPUT is required. Usage: make merge-rocrates INPUTS="file1.json file2.json" OUTPUT=merged.yaml)
endif
	@echo "Merging multiple RO-Crates..."
	$(RUN) python .claude/agents/scripts/rocrate_to_d4d.py \
		--merge \
		--auto-prioritize \
		--inputs $(INPUTS) \
		--output $(OUTPUT) \
		--mapping "$(ROCRATE_MAPPING)" \
		--schema $(ROCRATE_SCHEMA) \
		--validate

# Automated RO-Crate processing (auto-discover and process all files in directory)
# Usage: make auto-process-rocrates DIR=data/ro-crate/CM4AI OUTPUT=output.yaml [STRATEGY=merge]
auto-process-rocrates:
ifndef DIR
	$(error DIR is required. Usage: make auto-process-rocrates DIR=data/ro-crate/CM4AI OUTPUT=output.yaml)
endif
ifndef OUTPUT
	$(error OUTPUT is required. Usage: make auto-process-rocrates DIR=data/ro-crate/CM4AI OUTPUT=output.yaml)
endif
	@echo "Auto-processing RO-Crates in $(DIR)..."
	$(RUN) python .claude/agents/scripts/auto_process_rocrates.py \
		--input-dir $(DIR) \
		--output $(OUTPUT) \
		--mapping "$(ROCRATE_MAPPING)" \
		--strategy $(or $(STRATEGY),merge) \
		$(if $(TOP_N),--top-n $(TOP_N)) \
		--validate \
		--schema $(ROCRATE_SCHEMA)

# CM4AI-specific comprehensive merge (all 3 RO-Crates)
merge-cm4ai-rocrates:
	@echo "Merging all CM4AI RO-Crates into comprehensive D4D..."
	@mkdir -p data/d4d_concatenated/rocrate
	$(MAKE) auto-process-rocrates \
		DIR=data/ro-crate/CM4AI \
		OUTPUT=data/d4d_concatenated/rocrate/CM4AI_comprehensive_d4d.yaml \
		STRATEGY=merge
	@echo ""
	@echo "✓ Generated: data/d4d_concatenated/rocrate/CM4AI_comprehensive_d4d.yaml"
	@echo "✓ Report:    data/d4d_concatenated/rocrate/CM4AI_comprehensive_d4d_merge_report.txt"

# Test multi-file merge with CM4AI RO-Crates (top 2 only)
test-rocrate-merge:
	@echo "Testing multi-RO-Crate merge with CM4AI (top 2 files)..."
	@mkdir -p data/test
	$(MAKE) auto-process-rocrates \
		DIR=data/ro-crate/CM4AI \
		OUTPUT=data/test/CM4AI_merge_test.yaml \
		STRATEGY=merge \
		TOP_N=2
	@echo ""
	@echo "Generated files:"
	@echo "  D4D YAML:     data/test/CM4AI_merge_test.yaml"
	@echo "  Merge report: data/test/CM4AI_merge_test_merge_report.txt"

include project.Makefile
