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
