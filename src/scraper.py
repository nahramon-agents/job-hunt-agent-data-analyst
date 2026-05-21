import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

# ── PERFIL DE NAHUEL ──────────────────────────────────────────────────────────

KEYWORDS_POSITIVAS = [
    # Roles
    "ai content", "content strategy", "content strategist", "content operations",
    "ai workflow", "workflow automation", "marketing automation", "digital strategy",
    "research analyst", "content researcher", "ai tools", "prompt engineer",
    "seo strategist", "growth content", "operations strategist", "ai specialist",
    "automation specialist", "marketing strategist", "content manager",
    "email marketing", "funnel", "async", "asynchronous", "flexible hours",
    # Valores SÍ
    "personal development", "personal growth", "conscious", "consciousness",
    "mental health", "mindfulness", "meditation", "wellbeing", "well-being",
    "transformational", "education", "e-learning", "edtech", "self-directed",
    "creator economy", "creative economy", "empowerment", "impact",
    "sustainability", "social impact", "purpose-driven", "mission-driven",
    "democratize", "open access", "knowledge sharing", "human potential",
    "spiritual", "holistic", "community-driven", "ethical ai", "ai for good",

    # Modalidad ideal
    "part-time", "part time", "contract", "freelance", "project-based",
    "project based", "flexible hours", "flexible schedule", "async",
    "asynchronous", "outcomes-based", "results-based", "no fixed hours",
    "work when you want", "hourly", "retainer",
]

KEYWORDS_NEGATIVAS = [
    "data engineer", "machine learning engineer", "ml engineer", "devops",
    "on-site", "onsite", "in-office", "hybrid", "in person", "presencial",
    "sales", "cold calling", "account executive", "business development rep",
    "full stack", "backend engineer", "frontend engineer", "software engineer",
    "fixed schedule", "9-5", "9 to 5", "monday to friday required",
    "per word", "per-word", "pay to access", "membership required",
    # Restricciones geográficas
    "work anywhere in the us",
    "must be based in the us",
    "us only",
    "us residents only",
    "authorized to work in the us",
    "us citizens only",
    "north america only",
    "canada only",
    "uk only",
    "eu only",
    "usa only",
    "united states only",
    "resident in the united states",
    "us resident",
    "must be a us resident",
    "must reside in the us",
    "must reside in the united states",
    "location: usa",
    "📍location: usa",
    "remote location: usa",
    "🇺🇸 usa only",

    # Full-time / horario fijo
    "full-time only",
    "full time only",
    "40 hours per week",
    "40hrs per week",
    "monday through friday",
    "monday to friday",
    "full-time position",
    "this is a full-time role",
    "full time commitment",
    "dedicated full time",
    "must be available 40",
]

RED_FLAGS_MODALIDAD = [
    "must be available", "business hours required", "overlap required",
    "est hours", "pst hours", "fixed shift", "weekend availability",
    "on call", "on-call",
]

INDUSTRIAS_BLOQUEADAS = [
    # Extractivistas
    "mining", "oil", "petroleum", "gas company", "fossil fuel", "agroindustry",
    # Pharma corporativa
    "pharmaceutical", "big pharma", "clinical trial recruitment",
    # Consumo masivo sin propósito
    "tobacco", "cigarette", "alcohol brand", "beer brand", "fast fashion",
    "coca-cola", "pepsi", "unilever", "nestle",
    # Vigilancia / manipulación
    "surveillance", "data broker", "tracking software", "spyware",
    "predictive policing", "ad targeting platform",
    # Gambling / addiction
    "gambling", "casino", "betting", "crypto pump",
]


# ── SCORING ───────────────────────────────────────────────────────────────────

def score_job(title: str, description: str) -> dict:
    texto = (title + " " + description).lower()
    score = 5.0
    positivos_encontrados = []
    negativos_encontrados = []
    red_flags = []

    # Filtro duro: industrias bloqueadas → score 0, no llega al email
    for industria in INDUSTRIAS_BLOQUEADAS:
        if industria in texto:
            return {
                "score": 0,
                "positivos": [],
                "negativos": [f"industria bloqueada: {industria}"],
                "red_flags": ["FILTRADO POR VALORES"],
                "bloqueada": True,
            }

    for kw in KEYWORDS_POSITIVAS:
        if kw in texto:
            score += 0.4
            positivos_encontrados.append(kw)

    for kw in KEYWORDS_NEGATIVAS:
        if kw in texto:
            score -= 1.5
            negativos_encontrados.append(kw)

    for kw in RED_FLAGS_MODALIDAD:
        if kw in texto:
            score -= 1.0
            red_flags.append(kw)

    # Bonus stack de Nahuel
    stack = ["claude", "chatgpt", "notion", "python", "sql", "mailerlite",
             "canva", "perplexity", "openai"]
    for tool in stack:
        if tool in texto:
            score += 0.3

    score = round(min(max(score, 0), 10), 1)

    return {
        "score": score,
        "positivos": positivos_encontrados[:5],
        "negativos": negativos_encontrados[:3],
        "red_flags": red_flags[:3],
        "bloqueada": False,
    }


# ── SCRAPERS ──────────────────────────────────────────────────────────────────

def scrape_remoteok() -> list:
    jobs = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (job-search-agent/1.0)"}
        r = requests.get("https://remoteok.com/api", headers=headers, timeout=15)
        data = r.json()
        for item in data[1:]:  # primer elemento es metadata
            if not isinstance(item, dict):
                continue
            title = item.get("position", "")
            company = item.get("company", "")
            description = item.get("description", "")
            url = item.get("url", "")
            tags = " ".join(item.get("tags", []))
            full_text = f"{title} {tags} {description}"
            scored = score_job(title, full_text)
            if scored["score"] >= 5.5:
                jobs.append({
                    "title": title,
                    "company": company,
                    "url": url,
                    "source": "Remote OK",
                    **scored,
                })
    except Exception as e:
        print(f"[RemoteOK] Error: {e}")
    return jobs


def scrape_weworkremotely() -> list:
    jobs = []
    feeds = [
        ("https://weworkremotely.com/categories/remote-marketing-jobs.rss", "Marketing"),
        ("https://weworkremotely.com/categories/remote-copywriting-jobs.rss", "Copywriting"),
        ("https://weworkremotely.com/categories/remote-management-and-finance-jobs.rss", "Operations"),
    ]
    headers = {"User-Agent": "Mozilla/5.0 (job-search-agent/1.0)"}
    for feed_url, category in feeds:
        try:
            r = requests.get(feed_url, headers=headers, timeout=15)
            soup = BeautifulSoup(r.content, "xml")
            for item in soup.find_all("item"):
                title = item.find("title").text if item.find("title") else ""
                company_region = title.split(":")
                title_clean = company_region[-1].strip() if len(company_region) > 1 else title
                company = company_region[0].strip() if len(company_region) > 1 else ""
                description = item.find("description").text if item.find("description") else ""
                url = item.find("link").text if item.find("link") else ""
                scored = score_job(title_clean, description)
                if scored["score"] >= 5.5:
                    jobs.append({
                        "title": title_clean,
                        "company": company,
                        "url": url,
                        "source": f"We Work Remotely ({category})",
                        **scored,
                    })
        except Exception as e:
            print(f"[WWR {category}] Error: {e}")
    return jobs


def scrape_remotive() -> list:
    jobs = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (job-search-agent/1.0)"}
        categories = ["marketing", "all"]
        for cat in categories:
            r = requests.get(f"https://remotive.com/api/remote-jobs?category={cat}&limit=50",
                             headers=headers, timeout=15)
            data = r.json()
            for item in data.get("jobs", []):
                title = item.get("title", "")
                company = item.get("company_name", "")
                description = item.get("description", "")
                url = item.get("url", "")
                tags = " ".join(item.get("tags", []))
                full_text = f"{title} {tags} {description}"
                scored = score_job(title, full_text)
                if scored["score"] >= 5.5:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "url": url,
                        "source": "Remotive",
                        **scored,
                    })
    except Exception as e:
        print(f"[Remotive] Error: {e}")
    return jobs


# ── DEDUP ─────────────────────────────────────────────────────────────────────

def dedup(jobs: list) -> list:
    seen = set()
    unique = []
    for job in jobs:
        key = (job["title"].lower()[:40], job["company"].lower()[:30])
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


# ── MAIN ──────────────────────────────────────────────────────────────────────

def get_all_jobs() -> list:
    print("Scrapeando Remote OK...")
    jobs = scrape_remoteok()
    print(f"  → {len(jobs)} ofertas relevantes")

    print("Scrapeando We Work Remotely...")
    wwr = scrape_weworkremotely()
    print(f"  → {len(wwr)} ofertas relevantes")
    jobs += wwr

    print("Scrapeando Remotive...")
    rem = scrape_remotive()
    print(f"  → {len(rem)} ofertas relevantes")
    jobs += rem

    jobs = dedup(jobs)
    jobs.sort(key=lambda x: x["score"], reverse=True)
    print(f"\nTotal ofertas únicas con score ≥ 5.5: {len(jobs)}")
    return jobs


if __name__ == "__main__":
    jobs = get_all_jobs()
    with open("jobs_output.json", "w") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print("Guardado en jobs_output.json")
