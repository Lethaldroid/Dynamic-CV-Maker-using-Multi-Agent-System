import json
from llm import call_llm

SYSTEM_PROMPT = """You are a precise CV data extraction agent.
Extract ALL structured information from the provided CV into valid JSON.
Return ONLY the JSON object — no markdown fences, no explanation, no preamble.

Use null for any field not present in the CV. Do not omit fields.
Preserve date ranges exactly as written (e.g. "09/2025 – Present").

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
        "category": "Category Name (e.g. GenAI & Machine Learning)",
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
      "responsibilities": ["exact bullet points from CV"]
    }
  ],
  "projects": [
    {
      "name": "Project Name",
      "institution": "string or null",
      "duration": "string or null",
      "description": "Full description",
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


def run_parser_agent(raw_cv: str) -> dict:
    """
    Agent 1 — CV Parser Agent
    Converts raw CV text into a structured JSON profile.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Extract structured data from this CV:\n\n{raw_cv}"},
    ]

    raw_response = call_llm(messages, temperature=0.1)

    # Strip markdown fences if present
    clean = raw_response.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
        clean = clean.strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Fallback: return raw text in a wrapper so downstream agents can still use it
        return {"raw": raw_response, "name": "Unknown", "skills": [], "experience": [], "projects": [], "education": [], "certifications": []}
