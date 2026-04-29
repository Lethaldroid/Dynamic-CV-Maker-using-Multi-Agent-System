#!/usr/bin/env python3
"""
AutoHire — Multi-Agent Resume & Cover Letter Optimizer
Usage:
    python main.py

Place the CV and job description in the inputs/ folder.
"""

import json
import os
import sys
from datetime import datetime

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.file_reader import read_cv_file
from workflow.pipeline import run_pipeline


INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inputs")


def find_input_file(prefix: str, input_dir: str = INPUT_DIR):
    """Find an exact cv/jd file in inputs/ with a supported extension."""
    supported_exts = (".txt", ".md", ".markdown", ".json")
    expected_names = [f"{prefix}{ext}" for ext in supported_exts]

    if os.path.isdir(input_dir):
        for name in sorted(os.listdir(input_dir)):
            path = os.path.join(input_dir, name)
            stem, ext = os.path.splitext(name)
            if os.path.isfile(path) and stem.lower() == prefix.lower() and ext.lower() in supported_exts:
                return path

    expected = ", ".join(expected_names)
    raise FileNotFoundError(f"Could not find a {prefix} file in {input_dir}. Expected one of: {expected}")


def save_outputs(state, output_dir: str = "outputs"):
    """Save all outputs to the outputs/ directory."""
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save tailored CV
    cv_path = os.path.join(output_dir, f"tailored_cv_{ts}.md")
    with open(cv_path, "w") as f:
        f.write(state.current_cv)

    # Save cover letter
    cl_path = os.path.join(output_dir, f"cover_letter_{ts}.md")
    with open(cl_path, "w") as f:
        f.write(state.cover_letter)

    # Save score history
    report = {
        "candidate": state.parsed_profile.get("name", "Unknown"),
        "iterations": state.iteration,
        "target_reached": state.done,
        "score_history": state.score_history,
        "final_score": state.score_history[-1] if state.score_history else {},
        "best_score": state.best_score,
        "best_cv": state.best_cv,
    }
    report_path = os.path.join(output_dir, f"ats_report_{ts}.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return cv_path, cl_path, report_path


def print_summary(state):
    sep = "─" * 60
    print(f"\n{'═'*60}")
    print("  AutoHire — Final Results")
    print(f"{'═'*60}")
    print(f"  Candidate : {state.parsed_profile.get('name', 'Unknown')}")
    print(f"  Iterations: {state.iteration}")
    print(f"  Target Met: {'✅ Yes' if state.done else '❌ No (max iterations reached)'}")
    print()

    print("  Score Progression:")
    for i, s in enumerate(state.score_history, 1):
        bar_len = int(s.get("overall_score", 0) / 2)
        bar = "█" * bar_len + "░" * (50 - bar_len)
        print(f"  Round {i}: [{bar}] {s.get('overall_score', 0):.1f}")

    if state.score_history:
        final = state.score_history[-1]
        print(f"\n  Final Breakdown:")
        print(f"    Keyword Match  : {final.get('keyword_match', 0):.1f}")
        print(f"    Skills Match   : {final.get('skills_match', 0):.1f}")
        print(f"    Experience     : {final.get('experience_match', 0):.1f}")
        print(f"    Formatting     : {final.get('formatting_quality', 0):.1f}")
        print(f"    OVERALL        : {final.get('overall_score', 0):.1f}")

    print(f"\n{'═'*60}\n")


def main():
    print("\n╔══════════════════════════════════════╗")
    print("║        AutoHire — v1.0               ║")
    print("║  Multi-Agent Resume Optimizer        ║")
    print("╚══════════════════════════════════════╝\n")

    # ── Load inputs ──────────────────────────────────────────────────────────
    cv_path = find_input_file("cv")
    jd_path = find_input_file("jd")

    print(f"📂 Reading CV from: {cv_path}")
    raw_cv = read_cv_file(cv_path)

    print(f"📂 Reading JD from: {jd_path}")
    job_description = read_cv_file(jd_path)

    # ── Run pipeline ─────────────────────────────────────────────────────────
    state = run_pipeline(raw_cv, job_description, verbose=True)

    # ── Print summary ─────────────────────────────────────────────────────────
    print_summary(state)

    # ── Save outputs ─────────────────────────────────────────────────────────
    cv_path, cl_path, report_path = save_outputs(state, "outputs")
    print(f"📄 Tailored CV     → {cv_path}")
    print(f"📝 Cover Letter    → {cl_path}")
    print(f"📊 ATS Report      → {report_path}")
    print()


if __name__ == "__main__":
    main()
