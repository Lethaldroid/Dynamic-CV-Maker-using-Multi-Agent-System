import json
from llm import call_llm

SYSTEM_PROMPT = """You are an expert ATS resume writer. Rewrite the candidate profile into a tailored Markdown CV.

Hard rules:
- TRUTHFULNESS: Only use information present in the candidate profile. Never invent metrics, technologies, or experiences.
- If critic feedback asks you to add something not in the profile, find the closest real equivalent instead.
- KEYWORDS: Mirror the job description's exact phrasing where truthful (e.g. if JD says 'retrieval-augmented generation', use that phrase, not 'RAG system').
- DENSITY: Target 600-900 words. Every bullet must justify its existence.
- BULLETS: Each experience bullet = Action verb + specific task + quantified outcome (if available).
- STRUCTURE: Summary (3 sentences max) → Skills → Experience → Projects (top 3 most relevant only) → Education → Certifications.
- OUTPUT: Clean Markdown only. No explanations, no comments.

Skill section format — group by category:
**AI/ML:** skill1, skill2, skill3
**Backend:** skill1, skill2
(etc.)
"""

def run_cv_maker_agent(candidate_profile: dict, job_description: str, critic_feedback: str = "", missing_keywords: list = None, iteration: int = 1) -> str:
    
    temperature = max(0.1, 0.5 - (iteration * 0.1))
    feedback_section = ""
    if critic_feedback:
        feedback_section = (
            f"\n\n--- CRITIC FEEDBACK (address all points, but stay truthful) ---\n"
            f"{critic_feedback}\n"
            f"--- END FEEDBACK ---"
        )

    user_msg = (
        f"Candidate Profile (JSON):\n```json\n{json.dumps(candidate_profile, indent=2)}\n```\n\n" 
        f"Job Description:\n{job_description}"
        f"{feedback_section}"
    )

    if missing_keywords:
        user_msg += (
            f"\n\n--- KEYWORDS TO INCLUDE (from JD analysis) ---\n"
            f"These exact terms appear in the JD but are weak/absent in the current draft. "
            f"Weave them in naturally where truthful:\n"
            + "\n".join(f"- {kw}" for kw in missing_keywords)
        )
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    return call_llm(messages, temperature=temperature)