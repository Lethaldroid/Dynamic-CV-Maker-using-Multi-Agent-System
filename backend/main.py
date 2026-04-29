from __future__ import annotations

from fastapi import FastAPI, HTTPException, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import os

from backend.jobs import build_archive, get_job, list_jobs, submit_job
from backend.schemas import JobCreateResponse, JobStatusResponse, JobSubmitRequest, JobSubmitUploadResponse
from tools.file_reader import read_pdf_bytes

app = FastAPI(title="AutoHire API", version="1.0.0")

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

extra_origins = os.getenv("CORS_ORIGINS", "")
if extra_origins:
    allowed_origins.extend(origin.strip() for origin in extra_origins.split(",") if origin.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/jobs", response_model=JobCreateResponse)
def create_job(payload: JobSubmitRequest) -> JobCreateResponse:
    job = submit_job(payload.cv_text, payload.jd_text, payload.title)
    return JobCreateResponse(
        job_id=job["job_id"],
        status=job["status"],
        stage=job["stage"],
        message=job["message"],
        title=job.get("title"),
    )


@app.post("/api/jobs/upload", response_model=JobSubmitUploadResponse)
async def create_job_upload(
    cv_file: UploadFile = File(...),
    jd_text: str = Form(...),
    title: str | None = Form(default=None),
) -> JobSubmitUploadResponse:
    filename = cv_file.filename or "uploaded_cv"
    ext = os.path.splitext(filename)[1].lower()
    raw_bytes = await cv_file.read()

    if ext == ".pdf":
        cv_text = read_pdf_bytes(raw_bytes)
    else:
        try:
            cv_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="Text CV uploads must be UTF-8 encoded.") from exc

    job = submit_job(cv_text, jd_text, title)
    return JobSubmitUploadResponse(
        job_id=job["job_id"],
        status=job["status"],
        stage=job["stage"],
        message=job["message"],
        title=job.get("title"),
        filename=filename,
    )


@app.get("/api/jobs", response_model=list[JobStatusResponse])
def get_jobs() -> list[JobStatusResponse]:
    return [JobStatusResponse(**job) for job in list_jobs()]


@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> JobStatusResponse:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(**job)


@app.get("/api/jobs/{job_id}/download")
def download_job(job_id: str) -> Response:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Job is not complete yet")

    archive = build_archive(job)
    headers = {"Content-Disposition": f'attachment; filename="autohire_{job_id}.zip"'}
    return Response(content=archive, media_type="application/zip", headers=headers)
