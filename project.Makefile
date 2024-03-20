## Add your own custom Makefile targets here

SCHEMA_EXAMPLEDIR = src/data/examples
VALID_EXAMPLEDIR = $(SCHEMA_EXAMPLEDIR)/valid
INVALID_EXAMPLEDIR = $(SCHEMA_EXAMPLEDIR)/invalid
SCHEMA_CLASSES = $(shell $(RUN) yq -cr '.classes | keys | join(" ")' $(SOURCE_SCHEMA_PATH))

IMPORTS = standards-schema standards-organization-schema

all: update-imports site

update-imports: $(IMPORTS)

standards-schema:
	curl -s https://raw.githubusercontent.com/bridge2ai/standards-schemas/main/src/standards_schemas/schema/standards_schema.yaml \
		-o $(SOURCE_SCHEMA_DIR)standards_schema.yaml -z $(SOURCE_SCHEMA_DIR)standards_schema_yaml

standards-organization-schema:
	curl -s https://raw.githubusercontent.com/bridge2ai/standards-schemas/main/src/standards_schemas/schema/standards_organization_schema.yaml \
		-o $(SOURCE_SCHEMA_DIR)standards_organization_schema.yaml -z $(SOURCE_SCHEMA_DIR)standards_organization_schema.yaml

# Generate minimal example files for all classes
# For each file in the list, populate it with an id field
gen-minimal-examples:
	printf "# Example data file\n---\nid: \"data_sheets_schema:123\"\n" | tee -a $(patsubst %, $(VALID_EXAMPLEDIR)/%-minimal.yaml, $(SCHEMA_CLASSES))
	printf "# Example data file - needs more contents\n---\nid: \"data_sheets_schema:123\"\n" | tee -a $(patsubst %, $(VALID_EXAMPLEDIR)/%-valid.yaml, $(SCHEMA_CLASSES))
	printf "# Example invalid data file\n---\nid: 123\n" | tee -a $(patsubst %, $(INVALID_EXAMPLEDIR)/%-invalid.yaml, $(SCHEMA_CLASSES))
