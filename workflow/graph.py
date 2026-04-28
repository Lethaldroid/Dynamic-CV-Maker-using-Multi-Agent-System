"""
AutoHire Orchestration Workflow
Supervisor + Iterative Feedback Loop pattern
"""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass, field
from typing import Optional
from config import TARGET_SCORE, MAX_ITERATIONS

def filter_relevant_skills(profile: dict, job_description: str) -> dict:
    """Trim the skill list to the 20-30 most relevant skills for this JD."""
    from llm import call_llm
    import json

    all_skills = profile.get("skills", {})
    
    response = call_llm([
        {"role": "system", "content": (
            "You are a CV strategist. Given a job description and a candidate's full skill list, "
            "return ONLY the 20-30 most relevant skills as a JSON object with the same category structure. "
            "Preserve category names. Return only valid JSON, no explanation."
        )},
        {"role": "user", "content": (
            f"Job Description:\n{job_description}\n\n"
            f"Full Skills:\n{json.dumps(all_skills, indent=2)}"
        )},
    ], temperature=0.1)

    clean = response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        filtered = json.loads(clean)
        focused_profile = {**profile, "skills": filtered}
        return focused_profile
    except json.JSONDecodeError:
        return profile  # fallback to full profile


@dataclass
class AutoHireState:
    """Shared state passed between agents in the pipeline."""
    raw_cv: str = ""
    job_description: str = ""
    feedback_history: list = field(default_factory=list)
    parsed_profile: dict = field(default_factory=dict)
    current_cv: str = ""
    score_history: list = field(default_factory=list)
    critic_feedback: str = ""
    cover_letter: str = ""
    iteration: int = 0
    done: bool = False
    best_cv: str = ""
    best_score: float = 0.0


def run_pipeline(raw_cv: str, job_description: str, verbose: bool = True) -> AutoHireState:
    """
    Main orchestration controller.
    Runs the multi-agent pipeline with iterative feedback loop.
    """
    from agents.parser_agent import run_parser_agent
    from agents.cv_agent import run_cv_maker_agent
    from agents.scorer_agent import run_scorer_agent
    from agents.critic_agent import run_critic_agent
    from agents.cover_agent import run_cover_letter_agent
    from agents.refiner_agent import run_refiner_agent

    state = AutoHireState(raw_cv=raw_cv, job_description=job_description)

    def log(msg: str):
        if verbose:
            print(msg)

    # ── Step 1: Parse CV ─────────────────────────────────────────────────────
    log("\n[1/5] 🔍 CV Parser Agent — extracting structured profile...")
    # if the cv is already in json format, we can skip parsing and use it directly as the profile
    if raw_cv.startswith("{"):
        state.parsed_profile = json.loads(raw_cv)
    else:
        state.parsed_profile = run_parser_agent(raw_cv)
    log(f"      ✅ Extracted profile for: {state.parsed_profile.get('name', 'Unknown')}")

    # ── Step 2: Initial CV Generation ────────────────────────────────────────
    log("\n[2/5] ✍️  CV Maker Agent — generating tailored resume (iteration 1)...")
    focused_profile = filter_relevant_skills(state.parsed_profile, job_description)
    state.current_cv = run_cv_maker_agent(focused_profile, job_description, iteration=1)
    log("      ✅ Initial resume generated.")

    # ── Step 3: Score + Iterative Improvement Loop ────────────────────────────
    log(f"\n[3/5] 🔄 ATS Scorer + Critic Loop (target: {TARGET_SCORE}, max: {MAX_ITERATIONS} rounds)")

    while state.iteration < MAX_ITERATIONS:
        state.iteration += 1
        log(f"\n      ── Round {state.iteration} ──")

        # Score current CV
        scores = run_scorer_agent(state.current_cv, job_description)
        state.score_history.append(scores)
        overall = scores.get("overall_score", 0)
        if overall > state.best_score:
            state.best_score = overall
            state.best_cv = state.current_cv

        log(f"      📊 ATS Score: {overall} | kw={scores.get('keyword_match')} "
            f"sk={scores.get('skills_match')} ex={scores.get('experience_match')} "
            f"fmt={scores.get('formatting_quality')}")
        log(f"         → {scores.get('brief_reasoning', '')}")

        # Check target BEFORE running critic (no point critiquing a passing CV)
        if overall >= TARGET_SCORE:
            log(f"\n      🎯 Target score {TARGET_SCORE} reached! Score: {overall}")
            state.done = True
            break

        # Only critique and improve if we have iterations left
        if state.iteration < MAX_ITERATIONS:
            log("      🧠 Critic Agent — analyzing gaps...")
            state.critic_feedback = run_critic_agent(
                state.current_cv, scores, job_description,
                previous_feedback=state.feedback_history,
                iteration=state.iteration
            )
            state.feedback_history.append(state.critic_feedback)
            log(f"      💬 Feedback:\n{_indent(state.critic_feedback)}")

            # ── Key change: refiner instead of full rewrite ──
            updated_cv, change_log = run_refiner_agent(
                current_cv=state.current_cv,
                critic_feedback=state.critic_feedback,
                candidate_profile=focused_profile,
                job_description=job_description,
                missing_keywords=scores.get("missing_keywords", [])
            )
            state.current_cv = updated_cv
        else:
            log(f"\n      ⚠️  Max iterations ({MAX_ITERATIONS}) reached. Best score: {overall}")

    # ── Step 4: Generate Cover Letter ────────────────────────────────────────
    log("\n[4/5] 📝 Cover Letter Agent — writing personalized cover letter...")
    state.cover_letter = run_cover_letter_agent(state.current_cv, job_description)
    log("      ✅ Cover letter generated.")

    log("\n[5/5] ✅ Pipeline complete!\n")
    return state


def _indent(text: str, prefix: str = "         ") -> str:
    return "\n".join(prefix + line for line in text.splitlines())
