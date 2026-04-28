import json
from llm import call_llm # Ensure this is imported in ats_tools or pass the keywords from scorer_agent

def extract_keywords(job_description: str) -> list[str]:
    """
    Uses the LLM to extract actual, meaningful multi-word phrases and skills.
    """
    prompt = f"""
    Extract the core technical skills, tools, methodologies, and domain expertise from the following job description.
    Return ONLY a JSON list of strings. Do not include generic corporate words (e.g., 'teamwork', 'dynamic environment').
    Keep multi-word phrases intact (e.g., 'Large Language Models', 'Content Intelligence').
    Limit to the top 20-25 most critical keywords.
    
    JD: {job_description}
    """
    
    raw = call_llm([{"role": "user", "content": prompt}], temperature=0.1)
    
    try:
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except:
        return [] # Fallback

def keyword_overlap_score(cv_text: str, jd_keywords: list[str]) -> tuple[float, list[str], list[str]]:
    """
    Checks for the presence of exact phrases (case-insensitive) in the CV.
    Returns the score, present keywords, and missing keywords.
    """
    if not jd_keywords:
        return 100.0, [], []

    cv_lower = cv_text.lower()
    present = []
    missing = []

    for kw in jd_keywords:
        # Simple substring check is much safer for multi-word phrases than fuzzy matching single words
        if kw.lower() in cv_lower:
            present.append(kw)
        else:
            missing.append(kw)

    score = round((len(present) / len(jd_keywords)) * 100, 1)
    return score, present, missing