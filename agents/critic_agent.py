from llm import call_llm

SYSTEM_PROMPT = """You are a brutal, precise ATS optimization expert doing a gap analysis.

You will receive: an ATS score breakdown, the job description, and the current CV.

Your job:
1. Identify the LOWEST scoring dimension and focus 50% of your recommendations there.
2. Extract the top 10 keywords/phrases from the JD that are ABSENT or WEAK in the CV.
3. Output exactly 5 recommendations, ordered by impact (highest first).

Format each recommendation as:
[DIMENSION] Specific action → Expected score gain

Examples:
[KEYWORD] Add 'Kubernetes' to skills and mention it in the GoSaaS bullet — appears 3x in JD, 0x in CV → +8 keyword_match
[IMPACT] Bullet 2 in GoSaaS: replace 'built dashboards' with 'built real-time KPI dashboards reducing reporting lag by 60%' → +6 experience_match
[STRUCTURE] Move RAG project above QAOA — far more relevant to this ML Engineer role → +4 skills_match

Do NOT repeat recommendations from previous feedback if provided.
No preamble. No summary. Just the 5 recommendations.
"""

def run_critic_agent(cv_markdown: str, score_report: dict, job_description: str, 
                     previous_feedback: list[str] = None, iteration: int = 1) -> str:
    score_text = "\n".join(f"  {k}: {v}" for k, v in score_report.items())
    
    # Find the weakest dimension to focus on
    scoreable = {k: v for k, v in score_report.items() 
                 if k not in ("overall_score", "brief_reasoning") and isinstance(v, (int, float))}
    weakest = min(scoreable, key=scoreable.get) if scoreable else "keyword_match"

    prev_section = ""
    if previous_feedback:
        joined = "\n".join(f"- {f}" for f in previous_feedback)
        prev_section = f"\n\nPREVIOUS FEEDBACK ALREADY GIVEN (do NOT repeat):\n{joined}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Iteration: {iteration}\n"
                f"Weakest dimension: {weakest} ({scoreable.get(weakest, '?')})\n\n"
                f"ATS Scores:\n{score_text}\n\n"
                f"Job Description:\n{job_description}\n\n"
                f"Current CV:\n{cv_markdown}"
                f"{prev_section}"
            ),
        },
    ]

    return call_llm(messages, temperature=0.2)