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
	@echo "make setup -- initial setup (run this first)"
	@echo "make site -- makes site locally"
	@echo "make install -- install dependencies"
	@echo "make test -- runs tests"
	@echo "make test-modules -- validate all D4D module schemas"
	@echo "make lint -- perfom linting"
	@echo "make lint-modules -- lint all D4D module schemas"
	@echo "make concat-docs INPUT_DIR=dir OUTPUT_FILE=file -- concatenate documents from directory"
	@echo "make concat-extracted -- concatenate extracted D4D documents by column"
	@echo "make concat-downloads -- concatenate raw downloads by column"
	@echo "make process-concat INPUT_FILE=file -- process concatenated doc with D4D agent"
	@echo "make process-all-concat -- process all concatenated docs with D4D agent"
	@echo "make testdoc -- builds docs and runs local test server"
	@echo "make deploy -- deploys site"
	@echo "make update -- updates linkml version"
	@echo "make help -- show this help"
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
