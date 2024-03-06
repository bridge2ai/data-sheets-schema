## Add your own custom Makefile targets here

IMPORTS = standards-organization-schema

all: update-imports site

update-imports: $(IMPORTS)

standards-organization-schema:
	curl -s https://raw.githubusercontent.com/bridge2ai/standards-schemas/main/src/standards_schemas/schema/standards_organization_schema.yaml \
		-o $(SOURCE_SCHEMA_DIR)standards-organization-schema.yaml -z $(SOURCE_SCHEMA_DIR)standards-organization-schema.yaml
