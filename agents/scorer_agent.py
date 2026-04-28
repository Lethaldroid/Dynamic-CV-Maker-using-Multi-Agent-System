# agents/scorer_agent.py

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm import call_llm
from tools.ats_tools import (
    extract_keywords,
    keyword_overlap_score
)

SYSTEM_PROMPT = """
You are a strict ATS resume evaluator.

Evaluate the CV against the Job Description.

Return ONLY valid JSON:

{
  "skills_match": <0-100>,
  "experience_match": <0-100>,
  "formatting_quality": <0-100>,
  "brief_reasoning": "one concise sentence"
}

SCORING RULES:

skills_match:
- Presence of required tools, frameworks, programming languages
- Relevant domain skills
- Strong relevance = 85+

experience_match:
- Relevant projects/work experience
- Impact, ownership, scale
- Domain alignment
- Student profile with strong matching projects can still score high

formatting_quality:
- Clear headings
- Bullet points
- ATS readable plain text
- Professional structure

Be realistic and strict:
90+ = excellent fit
80+ = strong fit
70+ = decent fit
60 = weak fit
below 60 = poor fit

No markdown.
No explanation outside JSON.
"""


def run_scorer_agent(cv_markdown: str, job_description: str) -> dict:
    """
    Main ATS scoring pipeline.
    Hybrid approach:
    - LLM scores soft dimensions
    - Deterministic keyword engine scores keyword match
    """

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"CV:\n{cv_markdown}\n\nJob Description:\n{job_description}",
        },
    ]

    raw = call_llm(messages, temperature=0.1)
    clean = (
        raw.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )

    try:
        llm_scores = json.loads(clean)
    except Exception:
        llm_scores = {
            "skills_match": 65,
            "experience_match": 65,
            "formatting_quality": 75,
            "brief_reasoning": "LLM parse fallback.",
        }

    # ----------------------------
    # Deterministic keyword scoring
    # ----------------------------
    jd_keywords = extract_keywords(job_description)

    keyword_score, present_keywords, missing_keywords = keyword_overlap_score(
        cv_markdown, jd_keywords
    )

    llm_scores["keyword_match"] = keyword_score
    llm_scores["present_keywords"] = present_keywords
    llm_scores["missing_keywords"] = missing_keywords

    # ----------------------------
    # Final weighted score
    # ----------------------------
    overall = (
        0.30 * llm_scores["keyword_match"]
        + 0.30 * llm_scores["skills_match"]
        + 0.25 * llm_scores["experience_match"]
        + 0.15 * llm_scores["formatting_quality"]
    )

    llm_scores["overall_score"] = round(overall, 1)

    return llm_scores