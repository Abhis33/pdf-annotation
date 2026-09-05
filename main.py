#!/usr/bin/env python3
"""Render a caller's data set onto a tax form PDF using an annotation document.

Usage:
    python main.py <annotation.json> <input_data.json> <source.pdf>

Given an annotation document (conforming to schema/annotation.schema.json), a
JSON data set, and the blank form PDF the annotation was measured against,
writes the completed form to output/output.pdf. See SPEC.md for the full
rendering contract this implements.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import jsonschema

from annotator.render import RenderError, render_pdf

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "schema" / "annotation.schema.json"
OUTPUT_DIR = ROOT / "output"
LOG_DIR = ROOT / "logs"


def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"run-{datetime.now():%Y%m%d-%H%M%S}.log"

    logger = logging.getLogger("annotator")
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(console_handler)

    return logger, log_path


def load_json(path, logger, fail):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("file not found: %s", path)
        fail()
    except json.JSONDecodeError as e:
        logger.error("invalid JSON in %s: %s", path, e)
        fail()


def main():
    parser = argparse.ArgumentParser(
        description="Render a data set onto a tax form PDF using an annotation document"
    )
    parser.add_argument("annotation", help="Path to the annotation document")
    parser.add_argument("data", help="Path to the input data set (JSON)")
    parser.add_argument("pdf", help="Path to the blank source form PDF")
    args = parser.parse_args()

    logger, log_path = setup_logging()

    def fail():
        logger.info("run failed")
        print(f"Failed - see {log_path}", file=sys.stderr)
        raise SystemExit(1)

    logger.info(
        "run started: annotation=%s data=%s pdf=%s",
        args.annotation,
        args.data,
        args.pdf,
    )

    if not Path(args.pdf).is_file():
        logger.error("PDF file not found: %s", args.pdf)
        fail()

    schema = load_json(SCHEMA_PATH, logger, fail)
    document = load_json(args.annotation, logger, fail)
    data = load_json(args.data, logger, fail)

    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(document))
    if errors:
        logger.error(
            "annotation document failed schema validation (%d error(s)):", len(errors)
        )
        for e in errors:
            location = "/".join(str(p) for p in e.path) or "<root>"
            logger.error("  %s: %s", location, e.message)
        fail()

    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / "output.pdf"

    try:
        render_pdf(document, data, args.pdf, output_path, logger.warning)
    except RenderError as e:
        for sub_error in getattr(e, "all_errors", [e]):
            logger.error(str(sub_error))
        fail()

    logger.info("wrote %s", output_path)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
