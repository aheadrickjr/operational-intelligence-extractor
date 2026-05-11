# Operational Intelligence Extractor

A lightweight Python CLI tool that reads job postings from a CSV file, sends each posting to the OpenAI API, extracts structured operational signals, and writes the results to an output CSV.

The goal is to identify repeated operational friction patterns across industries — particularly lending operations, healthcare operations, compliance workflows, reconciliation, exception handling, and document-heavy work.

---

## Directory Structure

```
/data
    job_posts.csv          # Input: job postings to analyze
/results
    operational_signals.csv  # Output: extracted signals (created on run)
/scripts
    extract_operational_signals.py  # Main extraction script
requirements.txt
README.md
```

---

## Prerequisites

- Python 3.9 or higher
- An OpenAI API key

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your OpenAI API key

Export your API key as an environment variable:

```bash
export OPENAI_API_KEY=sk-...your-key-here...
```

On Windows (Command Prompt):

```cmd
set OPENAI_API_KEY=sk-...your-key-here...
```

---

## Running the Script

```bash
python scripts/extract_operational_signals.py
```

The script will:
1. Read all rows from `data/job_posts.csv`
2. Send each job posting to the OpenAI API (`gpt-4o` model)
3. Parse the structured JSON response
4. Write results to `results/operational_signals.csv`

Progress is printed to the console. Failed rows are written with an `extraction_status` of `error: ...` and the script continues to the next posting.

---

## Input CSV Format

File: `data/job_posts.csv`

| Column | Description |
|---|---|
| `job_title` | Job title of the posting |
| `company` | Company name |
| `industry` | Industry or operational domain |
| `job_description` | Full text of the job description |

A sample file with 14 realistic postings across lending ops, healthcare, compliance, reconciliation, and exception handling is included.

---

## Output CSV Format

File: `results/operational_signals.csv`

| Column | Description |
|---|---|
| `job_title` | Passed through from input |
| `company` | Passed through from input |
| `industry` | Passed through from input |
| `workflow` | Primary operational workflow this role supports |
| `manual_tasks` | Comma-separated list of specific manual or repetitive tasks |
| `pain_points` | Comma-separated list of operational friction points or inefficiencies |
| `systems_or_tools` | Comma-separated list of named systems, platforms, or tools mentioned |
| `human_judgment_required` | `yes` or `no` — does the role require frequent exception judgment? |
| `document_heavy` | `yes` or `no` — does the role involve high document volume? |
| `compliance_or_audit_pressure` | `yes` or `no` — significant regulatory/audit documentation burden? |
| `ai_opportunity` | 1-2 sentence description of the highest-value AI automation opportunity |
| `ai_opportunity_score_1_to_10` | Integer 1–10, where 10 = extremely high AI automation potential |
| `reasoning_summary` | 2-3 sentence summary of friction patterns and operational significance |
| `extraction_status` | `ok` if successful, or `error: <message>` if extraction failed |

---

## Error Handling

- **API errors** (network, rate limits, etc.): retried up to 3 times with exponential backoff. If all retries fail, the row is written with `extraction_status = error: ...` and processing continues.
- **JSON parse errors**: retried up to 3 times. The script strips markdown code fences if the model accidentally wraps the response.
- **Missing input file**: the script exits immediately with a clear error message.
- **Missing API key**: the script exits immediately with a clear error message.
- Results are flushed to disk after each row so partial results are preserved if the script is interrupted.

---

## Target Industries and Use Cases

This tool is designed to surface operational friction in:

- **Lending Operations** — loan processing, underwriting coordination, mortgage servicing, exception handling
- **Healthcare Operations** — revenue cycle, prior authorization, clinical documentation, medical records
- **Compliance & Regulatory** — BSA/AML, sanctions screening, SAR filing, regulatory reporting
- **Financial Operations** — trade reconciliation, collateral management, AP/GL reconciliation
- **Insurance Operations** — claims examination, coverage determination, regulatory compliance

---

## Model

Uses `gpt-4o` via the OpenAI Responses API. To change the model, update the `model` variable in `scripts/extract_operational_signals.py`.
