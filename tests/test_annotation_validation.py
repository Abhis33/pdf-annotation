"""Validates a minimal annotation document against the schema, plus three
targeted negative cases.

Deliberately not a full fixture suite: these three negative cases were chosen
as the highest-value regressions to guard (document shape, the binding
grammar, and the unevaluatedProperties bug once fixed in
schema/annotation.schema.json), not as exhaustive coverage of every field
type, enum, or format option. See SPEC.md for the full set of rules.
"""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "annotation.schema.json"

MINIMAL_VALID_DOC = {
    "specVersion": "1.0",
    "form": {"id": "test-form", "revision": "2025"},
    "pages": [{"number": 1, "width": 612, "height": 792}],
    "fields": [
        {
            "id": "first-name",
            "type": "text",
            "page": 1,
            "binding": "$.taxpayer.firstName",
            "rect": {"x": 0, "y": 0, "w": 10, "h": 10},
        }
    ],
}


@pytest.fixture(scope="module")
def validator():
    schema = json.loads(SCHEMA_PATH.read_text())
    return Draft202012Validator(schema)


def test_minimal_document_is_valid(validator):
    validator.validate(MINIMAL_VALID_DOC)


def test_missing_required_top_level_key_is_rejected(validator):
    doc = copy.deepcopy(MINIMAL_VALID_DOC)
    del doc["fields"]
    with pytest.raises(ValidationError):
        validator.validate(doc)


def test_binding_without_dollar_root_is_rejected(validator):
    doc = copy.deepcopy(MINIMAL_VALID_DOC)
    doc["fields"][0]["binding"] = "taxpayer.ssn"
    with pytest.raises(ValidationError):
        validator.validate(doc)


def test_field_with_unrecognized_property_is_rejected(validator):
    doc = copy.deepcopy(MINIMAL_VALID_DOC)
    doc["fields"][0]["bogus"] = True
    with pytest.raises(ValidationError):
        validator.validate(doc)
