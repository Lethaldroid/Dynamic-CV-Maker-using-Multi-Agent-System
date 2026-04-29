from __future__ import annotations

import base64
import json
import os
import time

import fitz  # PyMuPDF
import requests

from config import BASE_URL, MODEL


PDF_VISION_SYSTEM_PROMPT = """You are a precise CV data extraction agent.
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


def call_llm(messages: list[dict], temperature: float = 0.3, timeout: int = 120, max_retries: int = 3) -> str:
    url = f"{BASE_URL}/chat/completions"
    payload = {"model": MODEL, "messages": messages, "temperature": temperature}
    retry_statuses = {429, 500, 502, 503, 504}

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=timeout,
            )

            if response.status_code == 403:
                deny = response.headers.get("x-deny-reason", "unknown")
                raise RuntimeError(f"Proxy rejected (403): {deny}.")

            if response.status_code in retry_statuses:
                body = response.text.strip()
                raise RuntimeError(
                    f"Transient proxy error {response.status_code} on attempt {attempt}/{max_retries}: "
                    f"{body or 'no response body'}"
                )

            response.raise_for_status()

            response_payload = response.json()
            try:
                return response_payload["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as exc:
                raise RuntimeError(f"Unexpected proxy response shape: {response_payload}") from exc

        except (requests.exceptions.RequestException, RuntimeError) as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(2 ** (attempt - 1))
                continue
            break

    raise RuntimeError(f"LLM proxy request failed after {max_retries} attempts: {last_error}") from last_error


def _pdf_to_base64_images(pdf_path: str | None = None, pdf_bytes: bytes | None = None, dpi: int = 150) -> list[str]:
    if not pdf_path and pdf_bytes is None:
        raise ValueError("Provide either pdf_path or pdf_bytes.")

    if pdf_path:
        document = fitz.open(pdf_path)
    else:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")

    images: list[str] = []
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    for page in document:
        pixmap = page.get_pixmap(matrix=matrix)
        png_bytes = pixmap.tobytes("png")
        images.append(base64.b64encode(png_bytes).decode("utf-8"))

    document.close()
    return images


def call_llm_pdf(
    pdf_path: str | None = None,
    pdf_bytes: bytes | None = None,
    temperature: float = 0.1,
    timeout: int = 120,
    max_retries: int = 3,
) -> str:
    """Parse a PDF CV through the LLM's vision input."""
    if not pdf_path and pdf_bytes is None:
        raise ValueError("Provide either pdf_path or pdf_bytes.")

    if pdf_path and not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    b64_images = _pdf_to_base64_images(pdf_path=pdf_path, pdf_bytes=pdf_bytes)
    if not b64_images:
        source = pdf_path or "uploaded PDF bytes"
        raise ValueError(f"Could not render any pages from {source}.")

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
        {"role": "system", "content": PDF_VISION_SYSTEM_PROMPT},
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

    raw_response = call_llm(messages, temperature=temperature, timeout=timeout, max_retries=max_retries)
    clean = raw_response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        json.loads(clean)
    except json.JSONDecodeError:
        pass

    return raw_response