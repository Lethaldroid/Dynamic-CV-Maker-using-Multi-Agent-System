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
- **`extract_keywords(jd)`** / **`keyword_overlap_score(cv, keywords)`** — deterministic ATS keyword matching using `rapidfuzz`

## Setup

```bash
pip install requests rapidfuzz
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
Overall = 40% keyword_match + 30% skills_match + 20% experience_match + 10% formatting_quality
```

Keyword match uses a hybrid: 60% LLM judgment + 40% deterministic fuzzy matching (`rapidfuzz`).

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
