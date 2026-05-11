"""
Operational Signals Summarizer
-------------------------------
Reads results/operational_signals.csv (produced by extract_operational_signals.py)
and writes a ranked summary report to results/summary_report.txt.

Summary sections:
  1. Top industries by average AI opportunity score
  2. Most frequently mentioned manual tasks
  3. Most common systems / tools
  4. Industries with highest compliance pressure
  5. Overall dataset statistics

Usage:
    python scripts/summarize_signals.py
"""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_CSV = BASE_DIR / "results" / "operational_signals.csv"
OUTPUT_TXT = BASE_DIR / "results" / "summary_report.txt"

TOP_N = 10


def parse_list_field(value: str) -> list[str]:
    """Split a comma-separated field into a cleaned list of non-empty strings."""
    if not value or not value.strip():
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def load_rows(path: Path) -> list[dict]:
    """Load and return only successfully extracted rows from the CSV."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("extraction_status", "").strip() == "ok":
                rows.append(row)
    return rows


def parse_score(value: str) -> float | None:
    """Parse ai_opportunity_score_1_to_10 to a float, or None if invalid."""
    try:
        score = float(str(value).strip())
        if 1.0 <= score <= 10.0:
            return score
    except (ValueError, TypeError):
        pass
    return None


def industry_ai_scores(rows: list[dict]) -> list[tuple[str, float, int]]:
    """Return list of (industry, avg_score, count) sorted by avg_score desc."""
    scores: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        industry = row.get("industry", "Unknown").strip() or "Unknown"
        score = parse_score(row.get("ai_opportunity_score_1_to_10", ""))
        if score is not None:
            scores[industry].append(score)
    result = [
        (industry, sum(vals) / len(vals), len(vals))
        for industry, vals in scores.items()
    ]
    result.sort(key=lambda x: (-x[1], -x[2]))
    return result


def top_terms(rows: list[dict], field: str, n: int = TOP_N) -> list[tuple[str, int]]:
    """Return the top-n most frequent terms from a comma-separated field."""
    counter: Counter = Counter()
    for row in rows:
        for term in parse_list_field(row.get(field, "")):
            normalized = term.lower()
            if normalized:
                counter[normalized] += 1
    return counter.most_common(n)


def compliance_by_industry(rows: list[dict]) -> list[tuple[str, int, int, float]]:
    """
    Return list of (industry, compliance_count, total, pct) sorted by pct desc.

    Industries with only one posting are excluded from the ranking because a
    single data point produces an untrustworthy 0% or 100% figure. The minimum
    threshold is 2 postings per industry; this is noted in the report output.
    """
    totals: Counter = Counter()
    compliant: Counter = Counter()
    for row in rows:
        industry = row.get("industry", "Unknown").strip() or "Unknown"
        totals[industry] += 1
        if row.get("compliance_or_audit_pressure", "").strip().lower() == "yes":
            compliant[industry] += 1
    result = []
    for industry, total in totals.items():
        if total < 2:
            continue
        count = compliant.get(industry, 0)
        pct = (count / total) * 100
        result.append((industry, count, total, pct))
    result.sort(key=lambda x: (-x[3], -x[1]))
    return result


def overall_stats(rows: list[dict]) -> dict:
    """Compute overall dataset statistics."""
    scores = [s for row in rows if (s := parse_score(row.get("ai_opportunity_score_1_to_10", ""))) is not None]
    yes_judgment = sum(1 for r in rows if r.get("human_judgment_required", "").strip().lower() == "yes")
    yes_docs = sum(1 for r in rows if r.get("document_heavy", "").strip().lower() == "yes")
    yes_compliance = sum(1 for r in rows if r.get("compliance_or_audit_pressure", "").strip().lower() == "yes")
    industries = {r.get("industry", "Unknown").strip() or "Unknown" for r in rows}
    return {
        "total_postings": len(rows),
        "industries_count": len(industries),
        "avg_score": sum(scores) / len(scores) if scores else 0.0,
        "min_score": min(scores) if scores else 0.0,
        "max_score": max(scores) if scores else 0.0,
        "pct_human_judgment": (yes_judgment / len(rows) * 100) if rows else 0.0,
        "pct_document_heavy": (yes_docs / len(rows) * 100) if rows else 0.0,
        "pct_compliance": (yes_compliance / len(rows) * 100) if rows else 0.0,
    }


def divider(char: str = "=", width: int = 70) -> str:
    return char * width


def build_report(rows: list[dict]) -> str:
    lines: list[str] = []

    lines.append(divider())
    lines.append("OPERATIONAL FRICTION PATTERNS — SUMMARY REPORT")
    lines.append(divider())
    lines.append("")

    # --- Overall stats ---
    stats = overall_stats(rows)
    lines.append("DATASET OVERVIEW")
    lines.append(divider("-"))
    lines.append(f"  Total postings analyzed : {stats['total_postings']}")
    lines.append(f"  Unique industries        : {stats['industries_count']}")
    lines.append(f"  Avg AI opportunity score : {stats['avg_score']:.1f} / 10")
    lines.append(f"  Score range              : {stats['min_score']:.0f} – {stats['max_score']:.0f}")
    lines.append(f"  Require human judgment   : {stats['pct_human_judgment']:.0f}% of postings")
    lines.append(f"  Document-heavy roles     : {stats['pct_document_heavy']:.0f}% of postings")
    lines.append(f"  Compliance / audit load  : {stats['pct_compliance']:.0f}% of postings")
    lines.append("")

    # --- 1. Top industries by avg AI opportunity score ---
    lines.append(divider())
    lines.append("1. TOP INDUSTRIES BY AVERAGE AI OPPORTUNITY SCORE")
    lines.append(divider("-"))
    lines.append(f"  {'Rank':<5} {'Industry':<35} {'Avg Score':>9}  {'Postings':>8}")
    lines.append(f"  {'-'*4}  {'-'*34}  {'-'*9}  {'-'*8}")
    industry_scores = industry_ai_scores(rows)
    for rank, (industry, avg, count) in enumerate(industry_scores[:TOP_N], start=1):
        lines.append(f"  {rank:<5} {industry:<35} {avg:>8.1f}   {count:>7}")
    if not industry_scores:
        lines.append("  (no data)")
    lines.append("")

    # --- 2. Most frequently mentioned manual tasks ---
    lines.append(divider())
    lines.append("2. MOST FREQUENTLY MENTIONED MANUAL TASKS")
    lines.append(divider("-"))
    manual_tasks = top_terms(rows, "manual_tasks")
    if manual_tasks:
        max_count = manual_tasks[0][1]
        for rank, (task, count) in enumerate(manual_tasks, start=1):
            bar = "#" * int((count / max_count) * 30)
            lines.append(f"  {rank:>2}. {task:<40}  {count:>3}x  {bar}")
    else:
        lines.append("  (no data)")
    lines.append("")

    # --- 3. Most common systems / tools ---
    lines.append(divider())
    lines.append("3. MOST COMMON SYSTEMS / TOOLS")
    lines.append(divider("-"))
    tools = top_terms(rows, "systems_or_tools")
    if tools:
        max_count = tools[0][1]
        for rank, (tool, count) in enumerate(tools, start=1):
            bar = "#" * int((count / max_count) * 30)
            lines.append(f"  {rank:>2}. {tool:<40}  {count:>3}x  {bar}")
    else:
        lines.append("  (no data)")
    lines.append("")

    # --- 4. Industries with highest compliance pressure ---
    lines.append(divider())
    lines.append("4. INDUSTRIES WITH HIGHEST COMPLIANCE / AUDIT PRESSURE")
    lines.append(divider("-"))
    lines.append("  Note: industries with fewer than 2 postings are excluded — a single")
    lines.append("  data point would produce a misleading 0% or 100% figure.")
    lines.append("")
    lines.append(f"  {'Rank':<5} {'Industry':<35} {'% Compliance':>12}  {'(n/total)':>10}")
    lines.append(f"  {'-'*4}  {'-'*34}  {'-'*12}  {'-'*10}")
    compliance = compliance_by_industry(rows)
    if compliance:
        for rank, (industry, count, total, pct) in enumerate(compliance[:TOP_N], start=1):
            lines.append(f"  {rank:<5} {industry:<35} {pct:>11.0f}%   {count:>3}/{total:<3}")
    else:
        lines.append("  (no qualifying industries — need ≥2 postings per industry)")
    lines.append("")

    # --- 5. Most common pain points (frequency ranking) ---
    lines.append(divider())
    lines.append("5. MOST FREQUENTLY MENTIONED PAIN POINTS (FREQUENCY RANKING)")
    lines.append(divider("-"))
    pain_points = top_terms(rows, "pain_points")
    if pain_points:
        max_count = pain_points[0][1]
        for rank, (point, count) in enumerate(pain_points, start=1):
            bar = "#" * int((count / max_count) * 30)
            lines.append(f"  {rank:>2}. {point:<40}  {count:>3}x  {bar}")
    else:
        lines.append("  (no data)")
    lines.append("")

    lines.append(divider())
    lines.append("END OF REPORT")
    lines.append(divider())

    return "\n".join(lines)


def main():
    if not INPUT_CSV.exists():
        print(f"ERROR: Input file not found: {INPUT_CSV}")
        print("Run extract_operational_signals.py first to generate the CSV.")
        sys.exit(1)

    print(f"Reading signals from: {INPUT_CSV}")
    rows = load_rows(INPUT_CSV)

    if not rows:
        print("ERROR: No successfully extracted rows found in the CSV.")
        print("Check that extraction_status == 'ok' for at least one row.")
        sys.exit(1)

    print(f"Found {len(rows)} successfully extracted row(s).")

    report = build_report(rows)

    OUTPUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_TXT.write_text(report, encoding="utf-8")

    print(f"Summary report written to: {OUTPUT_TXT}")
    print()
    print(report)


if __name__ == "__main__":
    main()
