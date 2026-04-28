from llm import call_llm

SYSTEM_PROMPT = """You are an expert cover letter writer.
Write a professional, personalized cover letter based on the provided CV and job description.

Guidelines:
- 3-4 paragraphs, no longer than one page.
- Opening: Hook + role you're applying for.
- Body: 2 specific examples of achievements or skills that directly match JD requirements.
- Closing: Enthusiasm + call to action.
- Tone: Professional but warm. Avoid clichés like "I am writing to express my interest".
- Output clean Markdown only.
"""


def run_cover_letter_agent(cv_markdown: str, job_description: str) -> str:
    """
    Agent 5 — Cover Letter Agent
    Generates a personalized cover letter after ATS target is achieved.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Final CV:\n{cv_markdown}\n\n"
                f"Job Description:\n{job_description}"
            ),
        },
    ]

    return call_llm(messages, temperature=0.7)
