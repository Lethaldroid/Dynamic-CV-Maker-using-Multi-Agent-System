"""
AutoHire Orchestration Workflow
Supervisor + Iterative Feedback Loop pattern
"""

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from typing import Callable, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MAX_ITERATIONS, TARGET_SCORE


ProgressCallback = Callable[[dict], None]


def filter_relevant_skills(profile: dict, job_description: str) -> dict:
    """Trim the skill list to the 20-30 most relevant skills for this JD."""
    from llm import call_llm

    all_skills = profile.get("skills", {})

    response = call_llm(
        [
            {
                "role": "system",
                "content": (
                    "You are a CV strategist. Given a job description and a candidate's full skill list, "
                    "return ONLY the 20-30 most relevant skills as a JSON object with the same category structure. "
                    "Preserve category names. Return only valid JSON, no explanation."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Job Description:\n{job_description}\n\n"
                    f"Full Skills:\n{json.dumps(all_skills, indent=2)}"
                ),
            },
        ],
        temperature=0.1,
    )

    clean = response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        filtered = json.loads(clean)
        return {**profile, "skills": filtered}
    except json.JSONDecodeError:
        return profile


def snapshot_state(state: "AutoHireState", stage: str, message: str = "", extra: Optional[dict] = None) -> dict:
    """Create a JSON-serializable snapshot for UI progress updates."""
    payload = asdict(state)
    payload["stage"] = stage
    payload["message"] = message
    if extra:
        payload.update(extra)
    return payload


def emit_progress(
    progress_callback: Optional[ProgressCallback],
    state: "AutoHireState",
    stage: str,
    message: str = "",
    extra: Optional[dict] = None,
) -> None:
    if progress_callback:
        progress_callback(snapshot_state(state, stage=stage, message=message, extra=extra))


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


def run_pipeline(
    raw_cv: str,
    job_description: str,
    verbose: bool = True,
    progress_callback: Optional[ProgressCallback] = None,
) -> AutoHireState:
    """
    Main orchestration controller.
    Runs the multi-agent pipeline with iterative feedback loop.
    """
    from agents.critic_agent import run_critic_agent
    from agents.cover_agent import run_cover_letter_agent
    from agents.cv_agent import run_cv_maker_agent
    from agents.parser_agent import run_parser_agent
    from agents.refiner_agent import run_refiner_agent
    from agents.scorer_agent import run_scorer_agent

    state = AutoHireState(raw_cv=raw_cv, job_description=job_description)

    def log(msg: str):
        if verbose:
            print(msg)

    log("\n[1/5] 🔍 CV Parser Agent — extracting structured profile...")
    emit_progress(progress_callback, state, "parsing", "Extracting structured profile")
    if raw_cv.lstrip().startswith("{"):
        try:
            state.parsed_profile = json.loads(raw_cv)
        except json.JSONDecodeError:
            state.parsed_profile = run_parser_agent(raw_cv)
    else:
        state.parsed_profile = run_parser_agent(raw_cv)
    log(f"      ✅ Extracted profile for: {state.parsed_profile.get('name', 'Unknown')}")
    emit_progress(
        progress_callback,
        state,
        "parsed",
        f"Extracted profile for {state.parsed_profile.get('name', 'Unknown')}",
        {"parsed_profile": state.parsed_profile},
    )

    log("\n[2/5] ✍️  CV Maker Agent — generating tailored resume (iteration 1)...")
    focused_profile = filter_relevant_skills(state.parsed_profile, job_description)
    emit_progress(progress_callback, state, "drafting", "Generating tailored resume", {"focused_profile": focused_profile})
    state.current_cv = run_cv_maker_agent(focused_profile, job_description, iteration=1)
    log("      ✅ Initial resume generated.")
    emit_progress(progress_callback, state, "drafted", "Initial resume generated", {"current_cv": state.current_cv})

    log(f"\n[3/5] 🔄 ATS Scorer + Critic Loop (target: {TARGET_SCORE}, max: {MAX_ITERATIONS} rounds)")

    while state.iteration < MAX_ITERATIONS:
        state.iteration += 1
        log(f"\n      ── Round {state.iteration} ──")

        emit_progress(progress_callback, state, "scoring", f"Scoring round {state.iteration}")
        scores = run_scorer_agent(state.current_cv, job_description)
        state.score_history.append(scores)
        overall = scores.get("overall_score", 0)
        if overall > state.best_score:
            state.best_score = overall
            state.best_cv = state.current_cv

        log(
            f"      📊 ATS Score: {overall} | kw={scores.get('keyword_match')} "
            f"sk={scores.get('skills_match')} ex={scores.get('experience_match')} "
            f"fmt={scores.get('formatting_quality')}"
        )
        log(f"         → {scores.get('brief_reasoning', '')}")
        emit_progress(
            progress_callback,
            state,
            "scored",
            f"Round {state.iteration} scored {overall}",
            {"latest_score": scores, "overall_score": overall},
        )

        if overall >= TARGET_SCORE:
            log(f"\n      🎯 Target score {TARGET_SCORE} reached! Score: {overall}")
            state.done = True
            emit_progress(progress_callback, state, "target_reached", f"Target score reached at {overall}", {"latest_score": scores})
            break

        if state.iteration < MAX_ITERATIONS:
            log("      🧠 Critic Agent — analyzing gaps...")
            emit_progress(progress_callback, state, "critic", "Analyzing gaps", {"latest_score": scores})
            state.critic_feedback = run_critic_agent(
                state.current_cv,
                scores,
                job_description,
                previous_feedback=state.feedback_history,
                iteration=state.iteration,
            )
            state.feedback_history.append(state.critic_feedback)
            log(f"      💬 Feedback:\n{_indent(state.critic_feedback)}")
            emit_progress(progress_callback, state, "critic_done", "Critic feedback prepared", {"critic_feedback": state.critic_feedback})

            updated_cv, change_log = run_refiner_agent(
                current_cv=state.current_cv,
                critic_feedback=state.critic_feedback,
                candidate_profile=focused_profile,
                job_description=job_description,
                missing_keywords=scores.get("missing_keywords", []),
            )
            state.current_cv = updated_cv
            log("      ✍️  Refined resume generated.")
            emit_progress(
                progress_callback,
                state,
                "refined",
                "Resume refined",
                {"change_log": change_log, "current_cv": state.current_cv},
            )
        else:
            log(f"\n      ⚠️  Max iterations ({MAX_ITERATIONS}) reached. Best score: {overall}")

    if state.best_cv:
        state.current_cv = state.best_cv

    log("\n[4/5] 📝 Cover Letter Agent — writing personalized cover letter...")
    emit_progress(progress_callback, state, "cover_letter", "Generating cover letter")
    state.cover_letter = run_cover_letter_agent(state.current_cv, job_description)
    log("      ✅ Cover letter generated.")
    emit_progress(progress_callback, state, "cover_letter_done", "Cover letter generated", {"cover_letter": state.cover_letter})

    log("\n[5/5] ✅ Pipeline complete!\n")
    emit_progress(progress_callback, state, "complete", "Pipeline complete")
    return state


def _indent(text: str, prefix: str = "         ") -> str:
    return "\n".join(prefix + line for line in text.splitlines())
