"""Schema validity checks for schema/annotation.schema.json.

These tests check that the schema *file itself* is well-formed: valid JSON,
a legal JSON Schema (draft 2020-12), and free of dangling internal `$ref`s.
They do not validate any annotation document against the schema; that is a
separate concern (see progress.md for what's deferred).
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "annotation.schema.json"


@pytest.fixture(scope="module")
def schema_text():
    return SCHEMA_PATH.read_text()


@pytest.fixture(scope="module")
def schema(schema_text):
    return json.loads(schema_text)


def test_schema_file_is_valid_json(schema_text):
    json.loads(schema_text)


def test_schema_conforms_to_draft_2020_12(schema):
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        pytest.fail(f"schema is not a valid draft 2020-12 JSON Schema: {exc}")


def test_schema_has_no_dangling_local_refs(schema):
    """Every "$ref": "#/$defs/x" must point at a key that actually exists."""
    defs = schema.get("$defs", {})
    dangling = []

    def walk(node, path):
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                def_name = ref[len("#/$defs/") :]
                if def_name not in defs:
                    dangling.append((path, ref))
            for key, value in node.items():
                walk(value, f"{path}/{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(schema, "$")

    assert not dangling, "dangling $ref(s) found: " + ", ".join(
        f"{path} -> {ref}" for path, ref in dangling
    )
