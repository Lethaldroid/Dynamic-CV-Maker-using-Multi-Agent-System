# AutoHire — FastAPI + SPA Resume Optimizer

AutoHire is a multi-agent system that tailors a CV to a job description, iterates on the resume until it reaches a target ATS score, and generates a cover letter. The project now has a FastAPI backend for job orchestration and a React + Vite SPA for submission, live progress, and results review.

## Architecture

```
React SPA (frontend/)
        ↓ POST /api/jobs
FastAPI backend (backend/main.py)
        ↓
Job runner + in-memory store (backend/jobs.py)
        ↓
Pipeline orchestration (workflow/pipeline.py)
        ↓
[Parser → CV Maker → Scorer → Critic/Refiner loop → Cover Letter]
        ↓
Job status + score history + final artifacts
```

## What The App Does

- Takes in a CV and a job description from the SPA.
- Supports PDF CV uploads, plus text/markdown/JSON fallback.
- Runs the full agent pipeline in the background.
- Streams progress through polling so the UI can show stage updates while work is running.
- Displays ATS stats, keyword coverage, score history, the tailored CV, and the generated cover letter.
- Provides a ZIP download containing the final resume, cover letter, and ATS report.

## Project Structure

```
autohire/
├── backend/
│   ├── main.py          # FastAPI app and routes
│   ├── jobs.py          # In-memory job store and background runner
│   ├── schemas.py       # Pydantic request/response models
│   └── smoke_test.py    # Tiny backend sanity script
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       ├── main.jsx
│       └── styles.css
├── agents/
├── tools/
├── workflow/
│   └── pipeline.py      # Shared orchestration logic used by CLI + API
├── main.py              # CLI entry point
├── llm.py               # Shared LLM client
├── config.py            # Proxy/model/target defaults
└── requirements.txt
```

## Backend API

### `POST /api/jobs`
Submit a job for processing.

Request body:

```json
{
  "title": "Data Analyst role",
  "cv_text": "...",
  "jd_text": "..."
}
```

Response:

```json
{
  "job_id": "8f4f...",
  "status": "queued",
  "stage": "queued",
  "message": "Job queued",
  "title": "Data Analyst role"
}
```

### `GET /api/jobs/{job_id}`
Returns the current job snapshot, including:

- `status`, `stage`, `message`
- `iteration`, `done`, `best_score`, `overall_score`
- `score_history`
- `parsed_profile`
- `current_cv`
- `critic_feedback`
- `cover_letter`
- `result`
- `error`

### `GET /api/jobs/{job_id}/download`
Downloads a ZIP with:

- `tailored_cv.md`
- `cover_letter.md`
- `ats_report.json`

### `POST /api/jobs/upload`
Submit a job with a CV file upload. This is the preferred path for PDF CVs.

Form fields:

- `cv_file`: PDF, TXT, MD, or JSON file
- `jd_text`: job description text
- `title`: optional label

In local development, the Vite frontend uses the `/api` proxy automatically if `VITE_API_BASE` is not set. For deployed static hosting, set `VITE_API_BASE` to your backend URL.

The backend renders PDF uploads into images and sends them through the LLM vision parser, while text-based CV uploads continue through the normal text pipeline.

## Setup

### Python backend

```bash
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Run Locally

### 1. Start the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

### 2. Start the frontend

```bash
cd frontend
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`.

## Inputs

The pipeline still supports the CLI flow by reading files from `inputs/`:

- `inputs/cv.pdf`, `inputs/cv.txt`, `inputs/cv.md`, or `inputs/cv.json`
- `inputs/jd.txt`, `inputs/jd.md`, or `inputs/jd.json`

## CLI Mode

```bash
python main.py
```

## Scoring

The backend and CLI share the same scoring pipeline.

```
Overall = 30% keyword_match + 30% skills_match + 25% experience_match + 15% formatting_quality
```

`keyword_match` is derived from LLM keyword extraction plus exact keyword overlap checks, and the overall score is calculated from the scorer output in `agents/scorer_agent.py`.

## Notes

- The backend uses an in-memory job store for now. It is great for local development and easy to replace with Redis or a database later.
- The frontend polls the backend for progress updates, which keeps the implementation simple and reliable.
- The pipeline logic itself is still in the existing agent modules; the new API wraps them rather than rewriting the core behavior.
