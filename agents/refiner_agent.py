import json
import re
from llm import call_llm

SYSTEM_PROMPT = '''
You are a Senior Resume Optimization Strategist specializing in ATS systems.
Your first priority is factual accuracy.
Your second priority is ATS optimization.
If these conflict, choose factual accuracy.

You receive a CV and recommendations. Improve it while staying fully grounded.

TRUTHFULNESS POLICY:
- Never add an employer, degree, title, certification, date, metric, or achievement not supported by evidence.
- Never add a tool, framework, cloud platform, language, methodology, or skill unless it appears in:
  (a) candidate_profile
  (b) current_cv
  (c) directly evidenced by a project/task description.
- Never infer specific tools from generic outcomes.
  Example: built model != TensorFlow.
- If evidence is indirect, use broader truthful wording.
  Example: Docker -> containerization exposure.
- Do not upgrade familiarity into expertise.
- Do not claim leadership/ownership/production use unless supported.
- If uncertain, preserve original wording.

OPTIMIZATION RULES:
1. Use JD keywords only when evidence supports them.
2. Prefer semantic equivalents grounded in evidence.
3. Rewrite bullets as: Action + Skill + Tool + Result + Impact.
4. Reorder most relevant truthful content higher.
5. Quantify only when numbers already exist.

SELF-CHECK:
Before finalizing, audit every newly added keyword or claim.
Remove anything not traceable to evidence.
Prefer underclaiming over overclaiming.

OUTPUT FORMAT:
## CHANGES MADE
(list strategic changes)

## UPDATED CV
(full improved CV)
'''


def _flatten(obj):
    values = []
    if isinstance(obj, dict):
        for v in obj.values():
            values.extend(_flatten(v))
    elif isinstance(obj, list):
        for v in obj:
            values.extend(_flatten(v))
    elif obj is not None:
        values.append(str(obj))
    return values


def extract_verified_terms(candidate_profile: dict, current_cv: str) -> list[str]:
    text = "\n".join(_flatten(candidate_profile)) + "\n" + current_cv
    # simple token harvesting of tech-like terms
    patterns = re.findall(r"[A-Za-z][A-Za-z0-9+#./-]{1,30}", text)
    common = {"and", "the", "with", "for", "using", "built", "project", "experience", "skills"}
    terms = sorted({p for p in patterns if p.lower() not in common})
    return terms[:250]


def parse_response(response: str) -> tuple[str, str]:
    if "## UPDATED CV" in response:
        parts = response.split("## UPDATED CV", 1)
        change_log = parts[0].replace("## CHANGES MADE", "").strip()
        updated_cv = parts[1].strip()
        return updated_cv, change_log
    return response.strip(), "Could not parse structured change log."


def run_refiner_agent(current_cv: str, critic_feedback: str, candidate_profile: dict,
                      job_description: str, missing_keywords: list = None) -> tuple[str, str]:
    verified_terms = extract_verified_terms(candidate_profile, current_cv)

    kw_section = ""
    if missing_keywords:
        kw_section = (
            "\nMISSING JD KEYWORDS (use only if evidence supports them):\n" +
            "\n".join(f"- {kw}" for kw in missing_keywords[:20])
        )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f'''Candidate Profile:\n```json\n{json.dumps(candidate_profile, indent=2)}\n```\n\nJob Description:\n{job_description}\n\nCritic Recommendations:\n{critic_feedback}\n{kw_section}\n\nVERIFIED TERMS (safe vocabulary source):\n{', '.join(verified_terms)}\n\nRULE: Prefer using VERIFIED TERMS for tools/skills. If a JD keyword is unsupported, use broader truthful wording instead.\n\nCurrent CV to edit:\n{current_cv}'''
        }
    ]

    response = call_llm(messages, temperature=0.2)
    return parse_response(response)
