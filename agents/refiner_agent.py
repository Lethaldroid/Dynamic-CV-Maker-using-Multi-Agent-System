# agents/refiner_agent.py

import json
from llm import call_llm

SYSTEM_PROMPT = """
You are a Senior Resume Optimization Strategist specializing in ATS systems.  You receive a CV that already exists and a list of specific improvements.

Your objective is to maximize ATS match score against the Job Description while remaining factually grounded.

CORE PRINCIPLE:
You may intelligently reinterpret, expand, reframe, and elevate existing candidate experience into stronger professional language, as long as it remains reasonably supported by the candidate profile.

TRUTHFULNESS POLICY:
- Do NOT invent employers, degrees, titles, certifications, or years.
- You MAY infer adjacent competencies from demonstrated work.
- You MAY convert academic/project experience into professional skill statements.
- You MAY rename internal jargon into standard industry terms.

OPTIMIZATION RULES:

1. SEMANTIC EQUIVALENCE
Translate related experience into JD terminology.

Examples:
- CNNs -> Computer Vision
- Flask API -> REST API development
- University group project -> Cross-functional collaboration
- SQL coursework -> Data querying and relational databases
- Dockerized app -> Containerization

2. KEYWORD MAXIMIZATION
Weave missing JD keywords naturally into:
- summary
- skills
- experience bullets
- project bullets

Use exact JD wording whenever truthful.

3. BULLET UPGRADE FRAMEWORK
Rewrite bullets as:

Action + Skill + Tool + Result + Business Impact

Weak:
Built chatbot.

Strong:
Developed NLP chatbot using Python and Transformers, improving automated response efficiency.

4. STRATEGIC REORDERING
Move most relevant skills/projects higher.

5. SAFE INFERENCE
If candidate built deployment pipelines, may mention CI/CD familiarity.
If candidate used cloud notebooks, may mention cloud-based ML workflows.
If candidate worked in teams, may mention collaboration/agile teamwork.

OUTPUT FORMAT:

## CHANGES MADE
(list every strategic change)

## UPDATED CV
(full improved CV)
"""

def run_refiner_agent(current_cv: str, critic_feedback: str, candidate_profile: dict,
                      job_description: str, missing_keywords: list = None) -> tuple[str, str]:
    """
    Agent 2b — CV Refiner Agent (used from iteration 2 onwards)
    Applies critic recommendations surgically rather than rewriting.
    Returns (updated_cv, change_log)
    """
    kw_section = ""
    if missing_keywords:
        kw_section = (
            f"\n\nMISSING KEYWORDS TO WEAVE IN (use JD's exact phrasing where truthful):\n"
            + "\n".join(f"- {kw}" for kw in missing_keywords[:15])
        )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Candidate Profile (for truthfulness checking):\n"
                f"```json\n{json.dumps(candidate_profile, indent=2)}\n```\n\n"
                f"Job Description:\n{job_description}\n\n"
                f"Critic Recommendations:\n{critic_feedback}"
                f"{kw_section}\n\n"
                f"Current CV to edit:\n{current_cv}"
            ),
        },
    ]

    response = call_llm(messages, temperature=0.3)

    # Split the response into change log and updated CV
    if "## UPDATED CV" in response:
        parts = response.split("## UPDATED CV", 1)
        change_log = parts[0].replace("## CHANGES MADE", "").strip()
        updated_cv = parts[1].strip()
    else:
        # Fallback if model didn't follow format
        change_log = "Could not parse change log."
        updated_cv = response

    return updated_cv, change_log