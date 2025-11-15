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
	@echo "make extract-d4d-concat-gpt5       -- extract D4D from concatenated file"
	@echo "                                      (usage: PROJECT=AI_READI)"
	@echo "make extract-d4d-concat-all-gpt5   -- extract D4D from all concatenated"
	@echo "make process-concat                -- process single concatenated doc"
	@echo "                                      (usage: INPUT_FILE=file)"
	@echo "make process-all-concat            -- process all concatenated docs"
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

test-examples: examples/output

examples/output: src/data_sheets_schema/schema/data_sheets_schema.yaml
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
	cp -r $(SRC)/html/output/*.html $(DOCDIR)/html_output/ 2>/dev/null || true ; \
	cp -r $(SRC)/html/output/concatenated/*.html $(DOCDIR)/html_output/concatenated/ 2>/dev/null || true ; \
	cp $(SRC)/html/output/*.css $(DOCDIR)/html_output/ 2>/dev/null || true

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

include project.Makefile
