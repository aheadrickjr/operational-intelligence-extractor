"""
Operational Intelligence Extractor
-----------------------------------
Reads job postings from data/job_posts.csv, sends each to the OpenAI API,
extracts structured operational signals, and writes results to
results/operational_signals.csv.

Usage:
    python scripts/extract_operational_signals.py

Environment variable required:
    OPENAI_API_KEY — your OpenAI API key
"""

import csv
import json
import os
import re
import sys
import time
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: 'openai' package not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_CSV = BASE_DIR / "data" / "job_posts.csv"
OUTPUT_CSV = BASE_DIR / "results" / "operational_signals.csv"

OUTPUT_FIELDS = [
    "job_title",
    "company",
    "industry",
    "workflow",
    "manual_tasks",
    "pain_points",
    "systems_or_tools",
    "human_judgment_required",
    "document_heavy",
    "compliance_or_audit_pressure",
    "ai_opportunity",
    "ai_opportunity_score_1_to_10",
    "reasoning_summary",
    "extraction_status",
]

EXTRACTION_FIELDS = [
    "workflow",
    "manual_tasks",
    "pain_points",
    "systems_or_tools",
    "human_judgment_required",
    "document_heavy",
    "compliance_or_audit_pressure",
    "ai_opportunity",
    "ai_opportunity_score_1_to_10",
    "reasoning_summary",
]

SYSTEM_PROMPT = """You are an expert operational intelligence analyst.
Your job is to analyze job postings and extract structured signals about
operational friction, manual work, and automation opportunities.

You must respond with a single valid JSON object — no markdown, no explanation,
no code fences. The JSON must contain exactly these keys:

{
  "workflow": "short description of the primary operational workflow this role supports",
  "manual_tasks": "comma-separated list of specific manual or repetitive tasks mentioned",
  "pain_points": "comma-separated list of operational friction points or inefficiencies implied",
  "systems_or_tools": "comma-separated list of named systems, platforms, or tools mentioned",
  "human_judgment_required": "yes or no — does the role require frequent human judgment on exceptions or edge cases?",
  "document_heavy": "yes or no — does the role involve processing, reviewing, or routing high volumes of documents?",
  "compliance_or_audit_pressure": "yes or no — is there significant regulatory compliance or audit documentation burden?",
  "ai_opportunity": "1-2 sentence description of the highest-value AI automation opportunity in this role",
  "ai_opportunity_score_1_to_10": <integer 1-10 where 10 means extremely high AI automation potential>,
  "reasoning_summary": "2-3 sentence summary of why this role has operational friction and what patterns are most significant"
}

Be specific and factual — only extract what is actually present in the job description.
Do not invent or infer beyond what is written."""


def build_user_prompt(row: dict) -> str:
    return (
        f"Job Title: {row.get('job_title', '')}\n"
        f"Company: {row.get('company', '')}\n"
        f"Industry: {row.get('industry', '')}\n\n"
        f"Job Description:\n{row.get('job_description', '')}"
    )


def strip_json_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped the JSON in them."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_signals(client: OpenAI, row: dict, model: str, retry_delay: float = 5.0) -> dict:
    """Call the OpenAI API and return a dict of extracted signals."""
    prompt = build_user_prompt(row)

    for attempt in range(1, 4):
        try:
            response = client.responses.create(
                model=model,
                instructions=SYSTEM_PROMPT,
                input=prompt,
            )
            raw = response.output_text.strip()
            raw = strip_json_fences(raw)
            data = json.loads(raw)

            result = {}
            for field in EXTRACTION_FIELDS:
                result[field] = data.get(field, "")

            score = result.get("ai_opportunity_score_1_to_10", "")
            if isinstance(score, (int, float)):
                result["ai_opportunity_score_1_to_10"] = int(score)
            elif isinstance(score, str) and score.strip().isdigit():
                result["ai_opportunity_score_1_to_10"] = int(score.strip())

            result["extraction_status"] = "ok"
            return result

        except json.JSONDecodeError as e:
            print(f"  [WARNING] JSON parse error on attempt {attempt}: {e}")
            if attempt < 3:
                time.sleep(retry_delay)
            else:
                return _error_result(f"JSON parse error after 3 attempts: {e}")

        except Exception as e:
            err_str = str(e)
            print(f"  [WARNING] API error on attempt {attempt}: {err_str}")
            if "rate_limit" in err_str.lower() or "429" in err_str:
                wait = retry_delay * (2 ** (attempt - 1))
                print(f"  Rate limited — waiting {wait:.0f}s before retry...")
                time.sleep(wait)
            elif attempt < 3:
                time.sleep(retry_delay)
            else:
                return _error_result(f"API error after 3 attempts: {err_str}")

    return _error_result("Unknown failure after retries")


def _error_result(message: str) -> dict:
    result = {field: "" for field in EXTRACTION_FIELDS}
    result["extraction_status"] = f"error: {message}"
    return result


def main():
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.")
        sys.exit(1)

    if not INPUT_CSV.exists():
        print(f"ERROR: Input file not found: {INPUT_CSV}")
        sys.exit(1)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    client = OpenAI(api_key=api_key)
    model = "gpt-4o"

    print(f"Reading job postings from: {INPUT_CSV}")
    print(f"Writing results to:        {OUTPUT_CSV}")
    print(f"Model:                     {model}")
    print()

    rows = []
    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        print("ERROR: Input CSV is empty or has no data rows.")
        sys.exit(1)

    print(f"Found {len(rows)} job posting(s) to process.\n")

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()

        ok_count = 0
        error_count = 0

        for i, row in enumerate(rows, start=1):
            title = row.get("job_title", f"Row {i}")
            company = row.get("company", "")
            print(f"[{i}/{len(rows)}] Processing: {title} @ {company} ...")

            signals = extract_signals(client, row, model)

            output_row = {
                "job_title": row.get("job_title", ""),
                "company": row.get("company", ""),
                "industry": row.get("industry", ""),
            }
            output_row.update(signals)
            writer.writerow(output_row)
            out_f.flush()

            status = signals.get("extraction_status", "")
            if status == "ok":
                ok_count += 1
                score = signals.get("ai_opportunity_score_1_to_10", "")
                print(f"  OK — AI opportunity score: {score}/10")
            else:
                error_count += 1
                print(f"  FAILED — {status}")

            if i < len(rows):
                time.sleep(0.5)

    print()
    print(f"Done. {ok_count} succeeded, {error_count} failed.")
    print(f"Results saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
