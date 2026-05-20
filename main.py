#!/usr/bin/env python3
"""
Job Hunt Agent — Nahuel Ramon
Scrapea Remote OK, We Work Remotely y Remotive,
filtra y puntúa ofertas contra el perfil de Nahuel,
y manda un email diario con los resultados.
"""

import json
import sys
from src.scraper import get_all_jobs
from src.emailer import send_email


def main():
    print("=" * 50)
    print("JOB HUNT AGENT — Nahuel Ramon")
    print("=" * 50)

    jobs = get_all_jobs()

    if not jobs:
        print("No se encontraron ofertas relevantes hoy.")
        # igual mandar email para saber que el agente corrió
        send_email([])
        return

    # Guardar para debug
    with open("jobs_output.json", "w") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print(f"\nOfertas guardadas en jobs_output.json")

    print("\nEnviando email...")
    send_email(jobs)
    print("✅ Listo.")


if __name__ == "__main__":
    main()
