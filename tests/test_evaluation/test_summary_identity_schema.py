"""Generated summary schemas accept external identities and reject blanks."""
import json
from pathlib import Path

import jsonschema
import pytest
from linkml.generators.jsonschemagen import JsonSchemaGenerator


@pytest.fixture(scope="module")
def summary_schema():
    path = Path(__file__).resolve().parents[2] / "src/data_sheets_schema/schema/D4D_Evaluation_Summary.yaml"
    return json.loads(JsonSchemaGenerator(str(path)).serialize())


@pytest.mark.parametrize("class_name,field", [("MethodPerformance", "method"), ("ProjectPerformance", "project")])
def test_generated_schema_accepts_external_identity_but_rejects_blank(summary_schema, class_name, field):
    schema = {"$defs": summary_schema["$defs"], "$ref": f"#/$defs/{class_name}"}
    record = {field: "External clinical cohort / manual", "file_count": 1,
              "average_score": 0, "average_percentage": 0}
    jsonschema.validate(record, schema)
    for blank in ("", " ", "\n\t"):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({**record, field: blank}, schema)
