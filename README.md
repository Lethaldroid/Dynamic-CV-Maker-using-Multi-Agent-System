# AutoHire — Multi-Agent Resume & Cover Letter Optimizer

A multi-agent AI system that tailors your CV to a job description, iteratively improves it until it hits a target ATS score (≥90%), then generates a personalized cover letter.

## Architecture

```
User Input (CV + JD)
        ↓
   Coordinator (workflow/graph.py)
        ↓
 [Agent 1] CV Parser     → structured JSON profile
        ↓
 [Agent 2] CV Maker      → tailored Markdown resume
        ↓
 [Agent 3] ATS Scorer    → score report (keyword/skills/experience/formatting)
        ↓
  score < 90?
    YES → [Agent 4] Critic → feedback → back to CV Maker (loop)
    NO  → [Agent 5] Cover Letter Agent → final letter
        ↓
   Outputs (CV + Cover Letter + ATS Report)
```

## Agents

| Agent | File | Role |
|-------|------|------|
| CV Parser | `agents/parser_agent.py` | Extracts structured JSON from raw CV |
| CV Maker | `agents/cv_agent.py` | Writes tailored ATS-optimized resume |
| ATS Scorer | `agents/scorer_agent.py` | Hybrid LLM + fuzzy keyword scoring |
| Critic | `agents/critic_agent.py` | Identifies gaps, produces fix recommendations |
| Cover Letter | `agents/cover_agent.py` | Generates personalized cover letter |

## Tool Calls

- **`read_cv_file(path)`** — reads `.md`, `.txt`, `.json` CV files (mandatory)
- **`extract_keywords(job_description)`** — uses the LLM to extract the top 20–25 multi-word technical skills, tools and domain phrases from a job description; returns a JSON list of strings (see `tools/ats_tools.py`).
- **`keyword_overlap_score(cv_text, keywords)`** — deterministic, case-insensitive substring matching of extracted keywords against the CV; returns a tuple `(score, present_keywords, missing_keywords)` (see `tools/ats_tools.py`).
- **`run_scorer_agent(cv, jd)`** — orchestrates LLM scoring + deterministic keyword match and returns a result dict with these keys: `skills_match`, `experience_match`, `formatting_quality`, `brief_reasoning`, `keyword_match`, `present_keywords`, `missing_keywords`, `overall_score` (see `agents/scorer_agent.py`).

## Setup

```bash
pip install requests
```

## Usage
Put your source files in the `inputs/` folder:
- `inputs/cv.md`, `inputs/cv.txt`, or `inputs/cv.json`
- `inputs/jd.txt`, `inputs/jd.md`, or `inputs/jd.json`

Then run:
```bash
python main.py
```

The program automatically reads the first matching CV and JD file it finds in `inputs/`.
## Outputs

All files saved to `outputs/` with timestamps:
- `tailored_cv_<ts>.md` — ATS-optimized resume
- `cover_letter_<ts>.md` — personalized cover letter
- `ats_report_<ts>.json` — iteration history & score breakdown

## Scoring Formula

```
Overall = 30% keyword_match + 30% skills_match + 25% experience_match + 15% formatting_quality
```

How keyword matching works:
- `extract_keywords()` uses the LLM to produce a focused list of job keywords/phrases (top ~20).
- `keyword_overlap_score()` performs exact, case-insensitive substring checks of those phrases in the CV and returns a `keyword_match` percentage plus lists of present/missing keywords.

The scorer combines LLM-provided soft scores (`skills_match`, `experience_match`, `formatting_quality`) with the deterministic `keyword_match` to produce the final `overall_score` (see `agents/scorer_agent.py`). The agent falls back to conservative default scores if the LLM output cannot be parsed as JSON.

Note: the current implementation uses exact-substring matching for multi-word phrases (safer for phrases than naive fuzzy single-word matches).

## Project Structure

```
autohire/
├── main.py              # CLI entry point
├── config.py            # API URL, model, targets
├── llm.py               # LLM client (proxy + mock)
├── tools/
│   ├── file_reader.py   # Tool: read CV files
│   └── ats_tools.py     # Tool: keyword extraction & fuzzy matching
├── agents/
│   ├── parser_agent.py
│   ├── cv_agent.py
│   ├── scorer_agent.py
│   ├── critic_agent.py
│   └── cover_agent.py
├── workflow/
│   └── graph.py         # Orchestration controller
└── outputs/             # Generated files
```
