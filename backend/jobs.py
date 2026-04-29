from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from io import BytesIO
from threading import Lock
from typing import Any
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from workflow.pipeline import run_pipeline

_EXECUTOR = ThreadPoolExecutor(max_workers=2)
_JOB_LOCK = Lock()
_JOB_STORE: dict[str, dict[str, Any]] = {}
_OUTPUT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs", "jobs")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _create_record(job_id: str, title: str | None, cv_text: str, jd_text: str) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "title": title,
        "status": "queued",
        "stage": "queued",
        "message": "Job queued",
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "iteration": 0,
        "done": False,
        "best_score": 0.0,
        "overall_score": 0.0,
        "latest_score": None,
        "parsed_profile": {},
        "current_cv": "",
        "critic_feedback": "",
        "cover_letter": "",
        "score_history": [],
        "progress": None,
        "output_dir": None,
        "output_files": {},
        "result": None,
        "error": None,
        "cv_text": cv_text,
        "jd_text": jd_text,
        "progress_events": [],
    }


def _update_record(job_id: str, **updates: Any) -> dict[str, Any] | None:
    with _JOB_LOCK:
        record = _JOB_STORE.get(job_id)
        if not record:
            return None
        record.update(updates)
        record["updated_at"] = _utc_now()
        return deepcopy(record)


def _push_progress(job_id: str, snapshot: dict[str, Any]) -> None:
    with _JOB_LOCK:
        record = _JOB_STORE.get(job_id)
        if not record:
            return
        record["progress"] = snapshot
        record["stage"] = snapshot.get("stage", record["stage"])
        record["message"] = snapshot.get("message", record["message"])
        record["iteration"] = snapshot.get("iteration", record["iteration"])
        record["done"] = snapshot.get("done", record["done"])
        record["best_score"] = snapshot.get("best_score", record["best_score"])
        record["overall_score"] = snapshot.get("overall_score", record["overall_score"])
        record["latest_score"] = snapshot.get("latest_score", record["latest_score"])
        record["parsed_profile"] = snapshot.get("parsed_profile", record["parsed_profile"])
        record["current_cv"] = snapshot.get("current_cv", record["current_cv"])
        record["critic_feedback"] = snapshot.get("critic_feedback", record["critic_feedback"])
        record["cover_letter"] = snapshot.get("cover_letter", record["cover_letter"])
        record["score_history"] = snapshot.get("score_history", record["score_history"])
        record["progress_events"].append(snapshot)
        record["progress_events"] = record["progress_events"][-25:]
        record["updated_at"] = _utc_now()


def _serialize_state(state) -> dict[str, Any]:
    payload = asdict(state) if hasattr(state, "__dataclass_fields__") else dict(getattr(state, "__dict__", {}))
    payload["final_score"] = state.score_history[-1] if state.score_history else {}
    payload["best_score"] = state.best_score
    payload["best_cv"] = state.best_cv
    return payload


def _write_job_outputs(job_id: str, state) -> tuple[str, dict[str, str], dict[str, Any]]:
    output_dir = os.path.join(_OUTPUT_ROOT, job_id)
    os.makedirs(output_dir, exist_ok=True)

    final_score = state.score_history[-1] if state.score_history else {}
    report = {
        "job_id": job_id,
        "candidate": state.parsed_profile.get("name", "Unknown"),
        "iterations": state.iteration,
        "target_reached": state.done,
        "best_score": state.best_score,
        "final_score": final_score,
        "score_history": state.score_history,
        "parsed_profile": state.parsed_profile,
    }

    cv_path = os.path.join(output_dir, "tailored_cv.md")
    cover_path = os.path.join(output_dir, "cover_letter.md")
    report_path = os.path.join(output_dir, "ats_report.json")
    state_path = os.path.join(output_dir, "state.json")

    with open(cv_path, "w", encoding="utf-8") as handle:
        handle.write(state.current_cv)

    with open(cover_path, "w", encoding="utf-8") as handle:
        handle.write(state.cover_letter)

    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    with open(state_path, "w", encoding="utf-8") as handle:
        json.dump(_serialize_state(state), handle, indent=2)

    return output_dir, {
        "tailored_cv": cv_path,
        "cover_letter": cover_path,
        "ats_report": report_path,
        "state": state_path,
    }, report


def _run_job(job_id: str) -> None:
    with _JOB_LOCK:
        record = _JOB_STORE.get(job_id)
        if not record:
            return
        record["status"] = "running"
        record["stage"] = "running"
        record["message"] = "Pipeline started"
        record["updated_at"] = _utc_now()

    def on_progress(snapshot: dict[str, Any]) -> None:
        _push_progress(job_id, snapshot)

    try:
        with _JOB_LOCK:
            record = _JOB_STORE[job_id]
            cv_text = record["cv_text"]
            jd_text = record["jd_text"]
        state = run_pipeline(cv_text, jd_text, verbose=False, progress_callback=on_progress)
        result = _serialize_state(state)
        output_dir, output_files, report = _write_job_outputs(job_id, state)
        _update_record(
            job_id,
            status="completed",
            stage="complete",
            message="Pipeline completed",
            done=state.done,
            best_score=state.best_score,
            overall_score=state.score_history[-1]["overall_score"] if state.score_history else 0.0,
            latest_score=state.score_history[-1] if state.score_history else None,
            parsed_profile=state.parsed_profile,
            current_cv=state.current_cv,
            critic_feedback=state.critic_feedback,
            cover_letter=state.cover_letter,
            score_history=state.score_history,
            output_dir=output_dir,
            output_files=output_files,
            result=result,
            error=None,
        )
    except Exception as exc:
        _update_record(job_id, status="failed", stage="failed", message="Pipeline failed", error=str(exc))


def submit_job(cv_text: str, jd_text: str, title: str | None = None) -> dict[str, Any]:
    job_id = uuid4().hex
    with _JOB_LOCK:
        _JOB_STORE[job_id] = _create_record(job_id, title, cv_text, jd_text)
    _EXECUTOR.submit(_run_job, job_id)
    return deepcopy(_JOB_STORE[job_id])


def get_job(job_id: str) -> dict[str, Any] | None:
    with _JOB_LOCK:
        record = _JOB_STORE.get(job_id)
        return deepcopy(record) if record else None


def list_jobs() -> list[dict[str, Any]]:
    with _JOB_LOCK:
        return [deepcopy(record) for record in _JOB_STORE.values()]


def build_archive(job: dict[str, Any]) -> bytes:
    result = job.get("result") or {}
    output_files = job.get("output_files") or {}
    cv_text = job.get("current_cv") or result.get("current_cv") or ""
    cover_letter = job.get("cover_letter") or result.get("cover_letter") or ""
    score_history = job.get("score_history") or result.get("score_history") or []
    report = {
        "job_id": job["job_id"],
        "title": job.get("title"),
        "status": job.get("status"),
        "stage": job.get("stage"),
        "message": job.get("message"),
        "best_score": job.get("best_score", 0.0),
        "overall_score": job.get("overall_score", 0.0),
        "score_history": score_history,
        "parsed_profile": job.get("parsed_profile", {}),
        "error": job.get("error"),
    }

    if output_files:
        try:
            cv_path = output_files.get("tailored_cv")
            cover_path = output_files.get("cover_letter")
            report_path = output_files.get("ats_report")
            if cv_path and os.path.exists(cv_path):
                with open(cv_path, "r", encoding="utf-8") as handle:
                    cv_text = handle.read()
            if cover_path and os.path.exists(cover_path):
                with open(cover_path, "r", encoding="utf-8") as handle:
                    cover_letter = handle.read()
            if report_path and os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as handle:
                    report = json.load(handle)
        except OSError:
            pass

    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("tailored_cv.md", cv_text)
        archive.writestr("cover_letter.md", cover_letter)
        archive.writestr("ats_report.json", json.dumps(report, indent=2))
    return buffer.getvalue()
