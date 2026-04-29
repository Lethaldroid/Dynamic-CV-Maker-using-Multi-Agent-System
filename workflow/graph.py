"""Compatibility wrapper for the orchestration pipeline."""

from workflow.pipeline import AutoHireState, emit_progress, filter_relevant_skills, run_pipeline, snapshot_state

__all__ = [
    "AutoHireState",
    "emit_progress",
    "filter_relevant_skills",
    "run_pipeline",
    "snapshot_state",
]
