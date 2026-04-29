#!/usr/bin/env python3
"""Smoke test for PDF CV parsing.

Looks for the first PDF in `inputs/`, extracts text with the PDF reader,
then sends that text through the CV parser agent and prints the result.
"""

from __future__ import annotations

import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.parser_agent import run_parser_agent
from tools.file_reader import read_pdf_file


INPUT_DIR = os.path.join(PROJECT_ROOT, "inputs")


def find_pdf_file(input_dir: str = INPUT_DIR) -> str:
    """Return the first PDF file found in inputs/."""
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"Inputs folder not found: {input_dir}")

    pdf_files = sorted(
        os.path.join(input_dir, name)
        for name in os.listdir(input_dir)
        if name.lower().endswith(".pdf")
        and os.path.isfile(os.path.join(input_dir, name))
    )

    if not pdf_files:
        raise FileNotFoundError(
            f"No PDF found in {input_dir}. Add a CV PDF as inputs/cv.pdf or any .pdf file."
        )

    return pdf_files[0]


def main() -> int:
    pdf_path = find_pdf_file()
    print(f"PDF file: {pdf_path}")

    extracted_text = read_pdf_file(pdf_path)
    print("\n--- Extracted Text ---")
    print(extracted_text)

    print("\n--- Parsed JSON ---")
    parsed_profile = run_parser_agent(extracted_text)
    print(parsed_profile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
