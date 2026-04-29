import json
import os

from llm import call_llm_pdf

def read_cv_file(path: str) -> str:
    """
    Tool: Read a CV file from disk.
    Supports .md, .txt, .json, .pdf formats.
    Returns the content as a string suitable for LLM parsing.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"CV file not found: {path}")

    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        return read_pdf_file(path)

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if ext == ".json":
        # Pretty-print JSON for the LLM
        data = json.loads(content)
        return json.dumps(data, indent=2)

    return content  # .md and .txt returned as-is


def read_pdf_file(path: str) -> str:
    """Extract text from a PDF file and transcribe it with the LLM."""
    return call_llm_pdf(pdf_path=path)


def read_pdf_bytes(data: bytes) -> str:
    """Extract text from uploaded PDF bytes and transcribe it with the LLM."""
    return call_llm_pdf(pdf_bytes=data)
