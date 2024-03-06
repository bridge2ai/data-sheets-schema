## Add your own custom Makefile targets here

IMPORTS = standards-schema standards-organization-schema

all: update-imports site

update-imports: $(IMPORTS)

standards-schema:
	curl -s https://raw.githubusercontent.com/bridge2ai/standards-schemas/main/src/standards_schemas/schema/standards_schema.yaml \
		-o $(SOURCE_SCHEMA_DIR)standards_schema.yaml -z $(SOURCE_SCHEMA_DIR)standards-schema_yaml

standards-organization-schema:
	curl -s https://raw.githubusercontent.com/bridge2ai/standards-schemas/main/src/standards_schemas/schema/standards_organization_schema.yaml \
		-o $(SOURCE_SCHEMA_DIR)standards_organization_schema.yaml -z $(SOURCE_SCHEMA_DIR)standards_organization_schema.yaml
