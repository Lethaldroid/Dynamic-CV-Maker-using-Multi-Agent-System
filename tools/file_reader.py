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
    """Parse a PDF file with the LLM's vision input."""
    return call_llm_pdf(pdf_path=path)


def read_pdf_bytes(data: bytes) -> str:
    """Parse uploaded PDF bytes with the LLM's vision input."""
    return call_llm_pdf(pdf_bytes=data)


def read_uploaded_cv_bytes(data: bytes, filename: str) -> str:
    """Read an uploaded CV file from bytes and return parsed content."""
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        return read_pdf_bytes(data)

    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Text CV uploads must be UTF-8 encoded.") from exc

    if ext == ".json":
        parsed = json.loads(content)
        return json.dumps(parsed, indent=2)

    return content
