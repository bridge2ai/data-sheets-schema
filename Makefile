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

## ------------------------------------------------------------------
## SSSOM Alignment Generation
## ------------------------------------------------------------------

SSSOM_SCRIPT = src/semantic_exchange/generate_sssom_mapping.py
SSSOM_URI_SCRIPT = src/semantic_exchange/generate_sssom_uri_mapping.py
SSSOM_URI_COMPREHENSIVE_SCRIPT = src/semantic_exchange/generate_comprehensive_sssom_uri.py
SSSOM_COMPREHENSIVE_SCRIPT = src/semantic_exchange/generate_comprehensive_sssom.py
SSSOM_STRUCTURAL_SCRIPT = src/semantic_exchange/generate_structural_mapping.py
SKOS_ALIGNMENT = src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl
ROCRATE_JSON = data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json
INTERFACE_MAPPING = data/ro-crate_mapping/d4d_rocrate_interface_mapping.tsv
D4D_SCHEMA_ALL = src/data_sheets_schema/schema/data_sheets_schema_all.yaml
D4D_CORE_SCHEMA = src/data_sheets_schema/schema/data_sheets_schema_core.yaml
D4D_CORE_SCHEMA_ALL = src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml
URI_RECOMMENDATIONS = notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv
SSSOM_FULL = src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_mapping.tsv
SSSOM_SUBSET = src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_mapping_subset.tsv
SSSOM_URI = src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_uri_mapping.tsv
SSSOM_URI_COMPREHENSIVE = src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_uri_comprehensive.tsv
SSSOM_COMPREHENSIVE = src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv
SSSOM_STRUCTURAL = data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv

.PHONY: gen-core-schema validate-core lint-core gen-sssom gen-sssom-full gen-sssom-subset gen-sssom-uri gen-sssom-uri-comprehensive gen-sssom-comprehensive gen-sssom-structural gen-sssom-all clean-sssom

gen-core-schema: $(D4D_CORE_SCHEMA_ALL) ## Generate merged core exchange schema (data_sheets_schema_core_all.yaml)

$(D4D_CORE_SCHEMA_ALL): $(D4D_CORE_SCHEMA) src/data_sheets_schema/schema/D4D_Core.yaml
	@echo "Generating merged core exchange schema..."
	$(RUN) gen-linkml -o $(D4D_CORE_SCHEMA_ALL) -f yaml $(D4D_CORE_SCHEMA)
	@echo "✓ Core schema: $(D4D_CORE_SCHEMA_ALL)"

validate-core: ## Validate the core exchange schema with linkml-validate
	$(RUN) linkml-validate -s $(D4D_CORE_SCHEMA) --validate-schema

lint-core: ## Lint the core exchange schema files
	$(RUN) linkml-lint src/data_sheets_schema/schema/D4D_Core.yaml
	$(RUN) linkml-lint $(D4D_CORE_SCHEMA)

gen-sssom: gen-sssom-full gen-sssom-subset ## Generate SSSOM property-level mappings (full and subset)

gen-sssom-all: gen-sssom gen-sssom-uri gen-sssom-uri-comprehensive gen-sssom-comprehensive gen-sssom-structural ## Generate all SSSOM mappings (property + URI + comprehensive + structural)

gen-sssom-full: $(SSSOM_FULL) ## Generate full SSSOM mapping from SKOS alignment

$(SSSOM_FULL): $(SKOS_ALIGNMENT) $(ROCRATE_JSON) $(INTERFACE_MAPPING) $(SSSOM_SCRIPT)
	@echo "Generating full SSSOM mapping..."
	$(RUN) python $(SSSOM_SCRIPT) \
		--skos $(SKOS_ALIGNMENT) \
		--rocrate $(ROCRATE_JSON) \
		--mapping $(INTERFACE_MAPPING) \
		--output $(SSSOM_FULL) \
		--output-subset $(SSSOM_SUBSET)

gen-sssom-subset: $(SSSOM_SUBSET) ## Generate subset SSSOM mapping (interface fields only)

$(SSSOM_SUBSET): $(SSSOM_FULL)
	@echo "Subset SSSOM generated alongside full mapping"

gen-sssom-uri: $(SSSOM_URI) ## Generate URI-level SSSOM mapping (33 slots with slot_uri)

$(SSSOM_URI): $(D4D_SCHEMA_ALL) $(SKOS_ALIGNMENT) $(ROCRATE_JSON) $(SSSOM_URI_SCRIPT)
	@echo "Generating URI-level SSSOM mapping (slots with slot_uri only)..."
	$(RUN) python $(SSSOM_URI_SCRIPT) \
		--schema $(D4D_SCHEMA_ALL) \
		--skos $(SKOS_ALIGNMENT) \
		--rocrate $(ROCRATE_JSON) \
		--output $(SSSOM_URI)

gen-sssom-uri-comprehensive: $(SSSOM_URI_COMPREHENSIVE) ## Generate comprehensive URI-level SSSOM for ALL 270 attributes

$(SSSOM_URI_COMPREHENSIVE): $(D4D_SCHEMA_ALL) $(SKOS_ALIGNMENT) $(URI_RECOMMENDATIONS) $(SSSOM_URI_COMPREHENSIVE_SCRIPT)
	@echo "Generating comprehensive URI-level SSSOM (all attributes)..."
	$(RUN) python $(SSSOM_URI_COMPREHENSIVE_SCRIPT) \
		--schema $(D4D_SCHEMA_ALL) \
		--skos $(SKOS_ALIGNMENT) \
		--recommendations $(URI_RECOMMENDATIONS) \
		--output $(SSSOM_URI_COMPREHENSIVE)

gen-sssom-comprehensive: $(SSSOM_COMPREHENSIVE) ## Generate comprehensive SSSOM for ALL 270 D4D attributes

$(SSSOM_COMPREHENSIVE): $(D4D_SCHEMA_ALL) $(SKOS_ALIGNMENT) $(URI_RECOMMENDATIONS) $(SSSOM_COMPREHENSIVE_SCRIPT)
	@echo "Generating comprehensive SSSOM mapping (all D4D attributes)..."
	$(RUN) python $(SSSOM_COMPREHENSIVE_SCRIPT) \
		--schema $(D4D_SCHEMA_ALL) \
		--skos $(SKOS_ALIGNMENT) \
		--recommendations $(URI_RECOMMENDATIONS) \
		--output $(SSSOM_COMPREHENSIVE)

gen-sssom-structural: $(SSSOM_STRUCTURAL) ## Generate structure-aware D4D ↔ RO-Crate SSSOM mapping

$(SSSOM_STRUCTURAL): $(D4D_SCHEMA_ALL) $(ROCRATE_JSON) $(SSSOM_STRUCTURAL_SCRIPT)
	@echo "Generating structural SSSOM mapping..."
	$(RUN) python $(SSSOM_STRUCTURAL_SCRIPT)
	@echo "✓ Structural mapping: $(SSSOM_STRUCTURAL)"

clean-sssom: ## Remove generated SSSOM files
	rm -f $(SSSOM_FULL) $(SSSOM_SUBSET) $(SSSOM_URI) $(SSSOM_URI_COMPREHENSIVE) $(SSSOM_COMPREHENSIVE) $(SSSOM_STRUCTURAL)

## ------------------------------------------------------------------
## FAIRSCAPE ↔ D4D Bidirectional Conversion
## ------------------------------------------------------------------

D4D_TO_FAIRSCAPE = src/fairscape_integration/d4d_to_fairscape.py
FAIRSCAPE_TO_D4D = src/fairscape_integration/fairscape_to_d4d.py

.PHONY: test-fairscape-conversion test-d4d-to-fairscape test-fairscape-to-d4d

test-fairscape-conversion: test-d4d-to-fairscape test-fairscape-to-d4d ## Test bidirectional FAIRSCAPE ↔ D4D conversion

test-d4d-to-fairscape: ## Test D4D → FAIRSCAPE conversion (VOICE example)
	@echo "Testing D4D → FAIRSCAPE conversion..."
	$(RUN) python -c "import sys; sys.path.insert(0, 'src'); \
		from fairscape_integration.d4d_to_fairscape import convert_d4d_to_fairscape; \
		import yaml, json; \
		d4d = yaml.safe_load(open('data/d4d_concatenated/claudecode_agent/VOICE_d4d.yaml')); \
		rocrate, (valid, errors) = convert_d4d_to_fairscape(d4d); \
		print('✓ D4D → FAIRSCAPE: PASSED' if valid else '✗ D4D → FAIRSCAPE: FAILED'); \
		json.dump(rocrate.model_dump(exclude_none=True, by_alias=True), \
		          open('data/ro-crate/examples/voice_d4d_to_fairscape.json', 'w'), indent=2)"

test-fairscape-to-d4d: ## Test FAIRSCAPE → D4D conversion (CM4AI example)
	@echo "Testing FAIRSCAPE → D4D conversion..."
	$(RUN) python $(FAIRSCAPE_TO_D4D) \
		--input $(ROCRATE_JSON) \
		--output data/d4d_concatenated/fairscape_reverse/CM4AI_from_fairscape.yaml \
		--sssom $(SSSOM_FULL)

fairscape-to-d4d: ## Convert FAIRSCAPE RO-Crate to D4D YAML (INPUT=, OUTPUT=)
	@if [ -z "$(INPUT)" ] || [ -z "$(OUTPUT)" ]; then \
		echo "Usage: make fairscape-to-d4d INPUT=<rocrate.json> OUTPUT=<d4d.yaml>"; \
		exit 1; \
	fi
	$(RUN) python $(FAIRSCAPE_TO_D4D) \
		--input $(INPUT) \
		--output $(OUTPUT) \
		--sssom $(SSSOM_FULL)

## ------------------------------------------------------------------
## Semantic Review Tools
## ------------------------------------------------------------------

.PHONY: semantic-review semantic-review-conflicts semantic-review-ranges semantic-review-data semantic-review-report

semantic-review: semantic-review-conflicts semantic-review-ranges semantic-review-data semantic-review-report ## Run full semantic review

semantic-review-conflicts: ## Detect slot_uri conflicts
	@echo "Detecting slot_uri conflicts..."
	$(RUN) python scripts/slot_uri_conflict_detector.py --output reports/slot_uri_conflicts.json || true
	@echo "✓ Conflicts report: reports/slot_uri_conflicts.json"

semantic-review-ranges: ## Check range-description alignment
	@echo "Checking range-description alignment..."
	$(RUN) python scripts/range_description_checker.py --output reports/range_mismatches.json || true
	@echo "✓ Range mismatches report: reports/range_mismatches.json"

semantic-review-data: ## Analyze actual data values
	@echo "Analyzing actual D4D data values..."
	$(RUN) python scripts/data_value_analyzer.py --output reports/data_value_analysis.json
	@echo "✓ Data analysis report: reports/data_value_analysis.json"

semantic-review-report: reports/slot_uri_conflicts.json reports/range_mismatches.json reports/data_value_analysis.json ## Generate consolidated report
	@echo "Generating comprehensive semantic review report..."
	$(RUN) python scripts/generate_semantic_review_report.py \
		reports/slot_uri_conflicts.json \
		reports/range_mismatches.json \
		reports/data_value_analysis.json
	@echo "✓ Semantic review report: reports/semantic_review_report.md"
	@echo ""
	@echo "Summary:"
	@grep -A 5 "Executive Summary" reports/semantic_review_report.md || true

## ------------------------------------------------------------------

clean:
	rm -rf $(DEST)
	rm -rf tmp
	rm -fr docs/*
	rm -fr $(PYMODEL)/*

include project.Makefile
