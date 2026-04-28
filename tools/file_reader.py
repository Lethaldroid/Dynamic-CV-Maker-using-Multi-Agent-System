import json
import os

def read_cv_file(path: str) -> str:
    """
    Tool: Read a CV file from disk.
    Supports .md, .txt, .json formats.
    Returns the raw content as a string.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"CV file not found: {path}")

    ext = os.path.splitext(path)[1].lower()

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if ext == ".json":
        # Pretty-print JSON for the LLM
        data = json.loads(content)
        return json.dumps(data, indent=2)

    return content  # .md and .txt returned as-is
