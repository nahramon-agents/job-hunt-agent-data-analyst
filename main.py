#!/usr/bin/env python3
"""
Job Hunt Agent — Nahuel Ramon
Roles estratégicos: AI Content Researcher · Content Ops · Marketing Automation
Evaluación en dos etapas: keywords ponderadas → Claude como juez final
"""

import json
from src.scraper import get_all_jobs
from src.emailer import send_email


def main():
    print("=" * 55)
    print("JOB HUNT AGENT v2 — Nahuel Ramon")
    print("Roles estratégicos 1-2-3 · Claude como juez final")
    print("=" * 55)

    jobs_email, jobs_borderline = get_all_jobs()

    # Guardar para debug
    with open("jobs_output.json", "w") as f:
        json.dump(jobs_email, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*55}")
    print(f"Para email: {len(jobs_email)} | Borderline: {len(jobs_borderline)}")
    print(f"{'='*55}")

    print("\nEnviando email...")
    send_email(jobs_email, len(jobs_borderline))
    print("✅ Listo.")


if __name__ == "__main__":
    main()
