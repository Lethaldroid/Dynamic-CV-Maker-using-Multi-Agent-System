#!/usr/bin/env python3
"""Smoke test for CV PDF vision parsing.

Hardcoded to read `inputs/cv.pdf`, render each page as an image,
send the page images to the LLM, and print the parsed JSON result.
"""

from __future__ import annotations

import base64
import json
import os
import sys

import fitz  # PyMuPDF: only for rendering pages as images


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from llm import call_llm


PDF_PATH = os.path.join(PROJECT_ROOT, "inputs", "cv.pdf")

SYSTEM_PROMPT = """You are a precise CV data extraction agent.
You will receive one or more images of a CV document.
Extract ALL structured information into valid JSON.
Return ONLY the JSON object — no markdown fences, no explanation, no preamble.
Use null for any field not present. Do not omit fields. Preserve date ranges exactly as written.

Required format:
{
  "name": "string",
  "email": "string or null",
  "phone": "string or null",
  "location": "string or null",
  "linkedin": "string or null",
  "summary": "string or null",
  "skills": {
    "categories": [
      {
        "category": "Category Name",
        "items": ["skill1", "skill2"]
      }
    ],
    "flat": ["all", "skills", "in", "one", "list"]
  },
  "experience": [
    {
      "title": "Job Title",
      "company": "Company Name",
      "location": "string or null",
      "duration": "e.g. 07/2024 – 09/2025",
      "responsibilities": ["bullet points"]
    }
  ],
  "projects": [
    {
      "name": "Project Name",
      "institution": "string or null",
      "duration": "string or null",
      "description": "full description",
      "technologies": ["tech1", "tech2"]
    }
  ],
  "education": [
    {
      "degree": "Full degree title",
      "institution": "University Name",
      "location": "string or null",
      "duration": "e.g. 09/2025 – Present",
      "gpa": "string or null"
    }
  ],
  "certifications": ["cert1", "cert2"],
  "courses": ["course1", "course2"],
  "languages": ["English — Native"]
}
"""


def pdf_to_base64_images(pdf_path: str, dpi: int = 150) -> list[str]:
    """Render each PDF page as a base64-encoded PNG image."""
    doc = fitz.open(pdf_path)
    images: list[str] = []
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    for page in doc:
        pixmap = page.get_pixmap(matrix=matrix)
        png_bytes = pixmap.tobytes("png")
        images.append(base64.b64encode(png_bytes).decode("utf-8"))
    doc.close()
    return images


def parse_pdf_cv(pdf_path: str) -> dict:
    """Extract structured JSON profile from a PDF CV using the LLM's vision input."""
    b64_images = pdf_to_base64_images(pdf_path)

    if not b64_images:
        raise ValueError(f"Could not render any pages from PDF: {pdf_path}")

    image_blocks = [
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{b64}",
                "detail": "high",
            },
        }
        for b64 in b64_images
    ]

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                *image_blocks,
                {
                    "type": "text",
                    "text": "Extract all structured data from this CV. Return only the JSON object.",
                },
            ],
        },
    ]

    raw_response = call_llm(messages, temperature=0.1)
    clean = raw_response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return {
            "raw": raw_response,
            "name": "Unknown",
            "skills": {"categories": [], "flat": []},
            "experience": [],
            "projects": [],
            "education": [],
            "certifications": [],
            "courses": [],
            "languages": [],
        }


def main() -> int:
    print(f"PDF path: {PDF_PATH}")
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"Missing PDF: {PDF_PATH}")

    result = parse_pdf_cv(PDF_PATH)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
