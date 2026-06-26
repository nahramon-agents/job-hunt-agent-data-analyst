import requests
import json
import os
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup

# ── PERFIL — NAHUEL RAMON ─────────────────────────────────────────────────────
# AI Content & Operations Strategist — roles estratégicos 1-2-3
# Ing. Industrial + 4 años Data Analyst + AI Content Researcher (YouTuber USA)
# + co-estratega LarisaMagica (funnels, email, contenido, IA)
# Stack: Claude, ChatGPT, Perplexity, Python, SQL, MailerLite, Notion, Canva
# Inglés C1 | Córdoba, Argentina | 100% remoto global

# ── KEYWORDS PONDERADAS ───────────────────────────────────────────────────────

# Nivel A (+1.5) — "Este es exactamente mi rol"
KEYWORDS_A = [
    "ai content researcher", "story researcher", "youtube researcher",
    "content researcher", "ai workflow", "workflow automation",
    "content operations", "ai content strategist", "marketing automation",
    "fractional", "prompt engineer", "prompt engineering",
    "ai operations", "content strategy director", "research specialist",
    "ai researcher", "content automation",
]

# Nivel B (+0.7) — "Buen indicador, no definitorio"
KEYWORDS_B = [
    "content strategy", "content strategist", "digital strategy",
    "research analyst", "growth analyst", "seo strategist",
    "email marketing", "ai tools", "ai specialist",
    "automation specialist", "edtech", "creator economy",
    "content manager", "growth marketing", "lifecycle marketing",
    "narrative research", "knowledge management", "ai-powered",
    "generative ai", "llm", "content lead",
]

# Nivel C (+0.3) — "Contexto positivo, no determinante"
KEYWORDS_C = [
    "newsletter", "copywriter", "content writer", "ghostwriter",
    "community manager", "virtual assistant", "market research",
    "personal development", "personal growth", "mindfulness",
    "sustainability", "impact", "mission-driven", "purpose-driven",
    "funnel", "content creation", "content manager",
    # Stack de Nahuel
    "claude", "chatgpt", "notion", "canva", "mailerlite",
    "perplexity", "openai", "python", "sql", "zapier", "make.com",
]

# Bonus modalidad (+1.2) — señal fuerte de diseño de vida compatible
KEYWORDS_ASYNC = [
    "async", "asynchronous", "flexible hours", "flexible schedule",
    "work from anywhere", "your own schedule", "set your own hours",
    "flexible work", "own hours", "results-based", "outcome-based",
    "no fixed hours",
]

# Penalización media (-1.0) — paid media: relevante pero no el foco
KEYWORDS_PENALIZACION_MEDIA = [
    "paid media", "ppc", "media buyer", "media buying",
    "google ads", "facebook ads", "meta ads", "ad campaigns",
    "performance marketing specialist", "sem specialist",
]

# Penalización fuerte (-2.5) — roles que no encajan
KEYWORDS_PENALIZACION_FUERTE = [
    "data engineer", "machine learning engineer", "ml engineer",
    "software engineer", "backend engineer", "frontend engineer",
    "full stack", "devops", "data scientist",
    "on-site", "onsite", "in-office", "hybrid", "in person",
    "cold calling", "account executive", "sales development",
    "fixed schedule", "9-5", "9 to 5",
]

# Restricciones geográficas — penalización fuerte
GEO_RESTRICTIONS = [
    "usa only", "us only", "united states only",
    "us resident", "must be a us resident", "must reside in the us",
    "must reside in the united states", "based in the us",
    "must be located in the us", "us-based only", "us based only",
    "hiring in the us", "us citizens", "authorized to work in the us",
    "work anywhere in the us", "anywhere in the us",
    "remote (us)", "remote (united states)", "remote, united states",
    "remote, us", "location: united states", "location: usa",
    "uk only", "united kingdom only", "australia only",
    "canada only", "eu only", "europe only",
    "eligible to work in the united states",
    "within the continental us", "within the continental u.s.",
    "sponsorship is not available", "no sponsorship available",
    "work authorization required",
]

# Industrias bloqueadas — filtro duro (score = 0)
INDUSTRIAS_BLOQUEADAS = [
    "mining", "oil company", "petroleum", "fossil fuel",
    "pharmaceutical", "big pharma",
    "tobacco", "cigarette", "alcohol brand", "fast fashion",
    "surveillance", "data broker", "spyware", "predictive policing",
    "gambling", "casino", "betting", "crypto pump",
    "coca-cola", "pepsi", "nestle", "unilever",
]

# Ubicaciones permitidas — Remote OK trae location en la API
GEO_PERMITIDAS = [
    "worldwide", "anywhere", "global", "latam", "latin america",
    "south america", "europe", "argentina", "spain", "remote",
    "", None,
]

GEO_BLOQUEADAS_LOCATION_FIELD = [
    "usa", "us", "united states", "united states only",
    "australia", "australia only", "uk", "united kingdom",
    "canada only", "new zealand",
]


# ── PRE-SCORING (keywords) ────────────────────────────────────────────────────

def pre_score(title: str, description: str) -> dict:
    """
    Scoring por keywords ponderadas. Actúa como pre-filtro antes de Claude.
    Devuelve score y listas para contexto.
    """
    texto = (title + " " + description).lower()
    score = 2.0
    encontrados = {"A": [], "B": [], "C": [], "async": [], "neg_media": [], "neg_fuerte": []}

    # Filtro duro: industrias bloqueadas
    for ind in INDUSTRIAS_BLOQUEADAS:
        if ind in texto:
            return {
                "pre_score": 0,
                "bloqueada": True,
                "razon_bloqueo": f"industria bloqueada: {ind}",
                "encontrados": encontrados,
            }

    # Filtro duro: restricciones geo en texto
    for geo in GEO_RESTRICTIONS:
        if geo in texto:
            return {
                "pre_score": 0,
                "bloqueada": True,
                "razon_bloqueo": f"restricción geográfica: {geo}",
                "encontrados": encontrados,
            }

    # Keywords positivas
    for kw in KEYWORDS_A:
        if kw in texto:
            score += 1.5
            encontrados["A"].append(kw)

    for kw in KEYWORDS_B:
        if kw in texto:
            score += 0.7
            encontrados["B"].append(kw)

    for kw in KEYWORDS_C:
        if kw in texto:
            score += 0.3
            encontrados["C"].append(kw)

    for kw in KEYWORDS_ASYNC:
        if kw in texto:
            score += 1.2
            encontrados["async"].append(kw)

    # Penalizaciones
    for kw in KEYWORDS_PENALIZACION_MEDIA:
        if kw in texto:
            score -= 1.0
            encontrados["neg_media"].append(kw)

    for kw in KEYWORDS_PENALIZACION_FUERTE:
        if kw in texto:
            score -= 2.5
            encontrados["neg_fuerte"].append(kw)

    score = round(min(max(score, 0), 10), 1)

    return {
        "pre_score": score,
        "bloqueada": False,
        "razon_bloqueo": None,
        "encontrados": encontrados,
    }


# ── CLAUDE COMO JUEZ ──────────────────────────────────────────────────────────

CLAUDE_SYSTEM_PROMPT = """Sos el evaluador de ofertas laborales de Nahuel Ramon. Tu trabajo es ser DIRECTO, HONESTO y REALISTA — no inflar el ego, no ser optimista de más.

PERFIL REAL DE NAHUEL:
- Título: AI Content & Operations Strategist
- Background: Ingeniero Industrial + 4 años Data Analyst en Novix (empresa argentina) + AI Content Researcher freelance para canal documental de YouTube en USA (cliente: Ethan) + co-estratega en LarisaMagica (marca personal de desarrollo personal: funnels, email marketing, contenido, IA)
- Stack técnico: Claude, ChatGPT, Perplexity, Python (nivel intermedio/autodidacta), SQL, MailerLite, Notion, Canva
- Idiomas: Español nativo, Inglés C1 (TOEFL IBT), italiano/portugués intermedios
- Ubicación: Córdoba, Argentina — solo 100% remoto
- Situación actual: Sus roles son freelance/colaboración, NO tiene experiencia como empleado en empresa corporativa en estos roles. Es autodidacta en IA, no tiene certificaciones formales de empresas tech.

NO-NEGOCIABLES:
- 100% remoto (no híbrido)
- Sin micromanagement ni estructura rígida
- Sin trabajar fines de semana

EMPRESAS QUE SÍ (aunque no sea explícito en la oferta, si el contexto lo sugiere):
- Desarrollo personal, bienestar, educación transformacional
- IA con propósito: herramientas que empoderan personas
- Creator economy con valores, startups que democratizan oportunidades
- Salud mental, mindfulness, sostenibilidad real

EMPRESAS QUE NO:
- Extractivistas, farmacéuticas corporativas, consumo masivo sin propósito
- Tecnología de vigilancia o manipulación
- Gambling, tabaco, alcohol, fast fashion

Tu tarea: evaluar la oferta y devolver ÚNICAMENTE un JSON válido, sin texto antes ni después, sin backticks, sin markdown.

El JSON debe tener exactamente estas claves:
{
  "score": (float 0.0-10.0),
  "resumen": "(2 líneas en español: qué es el rol realmente y qué tipo de empresa es)",
  "por_que_encaja": "(1-2 líneas honestas sobre el fit real)",
  "brecha_stack": "(honesto y directo: qué pide el puesto que Nahuel no tiene o tiene débil. Si no hay brecha significativa, decí 'Stack suficiente para este rol')",
  "posibilidad_real": "(una de estas tres: 'Alta', 'Media', 'Baja') + 1 línea explicando por qué",
  "red_flags": ["lista de red flags detectadas, puede ser lista vacía []"],
  "location_restriction": "(si detectás que es USA/UK/AU/CA only aunque esté implícito o escondido, describilo. Si no hay restricción clara: 'Sin restricción detectada')",
  "modalidad": "(una de: full-time / part-time / contract / freelance / unclear)",
  "salario": "(lo que diga la oferta textualmente, o 'No especificado')",
  "pasa_filtro": (true si score >= 6.0, false si no)
}"""


def claude_evaluate(title: str, company: str, description: str, source: str) -> dict | None:
    """
    Manda la oferta a Claude para evaluación profunda.
    Retorna el JSON parseado o None si falla.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    prompt = f"""Evaluá esta oferta laboral para Nahuel Ramon:

TÍTULO: {title}
EMPRESA: {company}
FUENTE: {source}
DESCRIPCIÓN:
{description[:3000]}

Devolvé solo el JSON, sin texto adicional."""

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 1000,
                "system": CLAUDE_SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        data = r.json()
        raw = data["content"][0]["text"].strip()
        # Limpiar por si Claude agrega backticks igual
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"    [Claude] Error evaluando '{title}': {e}")
        return None


# ── SEEN JOBS (memoria) ───────────────────────────────────────────────────────

SEEN_JOBS_FILE = "seen_jobs.json"


def load_seen_jobs() -> set:
    try:
        with open(SEEN_JOBS_FILE) as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen_jobs(seen: set):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen), f, indent=2)


def job_id(title: str, company: str, url: str) -> str:
    key = f"{title.lower()[:50]}|{company.lower()[:30]}|{url[-40:]}"
    return hashlib.md5(key.encode()).hexdigest()


# ── SCRAPERS ──────────────────────────────────────────────────────────────────

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}


def location_bloqueada(location: str) -> bool:
    """Verifica si el campo location de la API indica restricción geográfica."""
    if not location:
        return False
    loc = location.lower().strip()
    for bloq in GEO_BLOQUEADAS_LOCATION_FIELD:
        if loc == bloq or loc.startswith(bloq + ",") or loc.startswith(bloq + " "):
            return True
    return False


def scrape_remoteok() -> list:
    jobs = []
    try:
        r = requests.get("https://remoteok.com/api", headers=HEADERS, timeout=15)
        data = r.json()
        for item in data[1:]:
            if not isinstance(item, dict):
                continue
            # Fix geo: usar el campo location de la API
            location = item.get("location", "") or ""
            if location_bloqueada(location):
                continue
            title = item.get("position", "")
            company = item.get("company", "")
            description = item.get("description", "")
            url = item.get("url", "")
            tags = " ".join(item.get("tags", []))
            full_text = f"{title} {tags} {description} {location}"
            pre = pre_score(title, full_text)
            if not pre["bloqueada"] and pre["pre_score"] >= 5.0:
                jobs.append({
                    "title": title, "company": company,
                    "url": url, "source": "Remote OK",
                    "description": description[:2000],
                    "pre_score": pre["pre_score"],
                    "encontrados": pre["encontrados"],
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
    for feed_url, category in feeds:
        try:
            r = requests.get(feed_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.content, "xml")
            for item in soup.find_all("item"):
                title_raw = item.find("title").text if item.find("title") else ""
                parts = title_raw.split(":")
                title_clean = parts[-1].strip() if len(parts) > 1 else title_raw
                company = parts[0].strip() if len(parts) > 1 else ""
                description = item.find("description").text if item.find("description") else ""
                url = item.find("link").text if item.find("link") else ""
                pre = pre_score(title_clean, description)
                if not pre["bloqueada"] and pre["pre_score"] >= 5.0:
                    jobs.append({
                        "title": title_clean, "company": company,
                        "url": url, "source": f"We Work Remotely ({category})",
                        "description": description[:2000],
                        "pre_score": pre["pre_score"],
                        "encontrados": pre["encontrados"],
                    })
        except Exception as e:
            print(f"[WWR {category}] Error: {e}")
    return jobs


def scrape_remotive() -> list:
    jobs = []
    try:
        categories = ["marketing", "all"]
        for cat in categories:
            r = requests.get(
                f"https://remotive.com/api/remote-jobs?category={cat}&limit=50",
                headers=HEADERS, timeout=15)
            data = r.json()
            for item in data.get("jobs", []):
                title = item.get("title", "")
                company = item.get("company_name", "")
                description = item.get("description", "")
                url = item.get("url", "")
                tags = " ".join(item.get("tags", []))
                location = item.get("candidate_required_location", "")
                if location_bloqueada(location):
                    continue
                full_text = f"{title} {tags} {description} {location}"
                pre = pre_score(title, full_text)
                if not pre["bloqueada"] and pre["pre_score"] >= 5.0:
                    jobs.append({
                        "title": title, "company": company,
                        "url": url, "source": "Remotive",
                        "description": description[:2000],
                        "pre_score": pre["pre_score"],
                        "encontrados": pre["encontrados"],
                    })
    except Exception as e:
        print(f"[Remotive] Error: {e}")
    return jobs


def scrape_workingnomads() -> list:
    jobs = []
    try:
        categories = ["marketing", "business", "writing"]
        for cat in categories:
            r = requests.get(
                f"https://www.workingnomads.com/api/exposed_jobs/?category={cat}",
                headers=HEADERS, timeout=15)
            data = r.json()
            for item in data:
                title = item.get("title", "")
                company = item.get("company_name", "")
                description = item.get("description", "")
                url = item.get("url", "")
                # Working Nomads: el campo location viene en la oferta
                location = item.get("location", "") or ""
                if location_bloqueada(location):
                    continue
                full_text = f"{title} {description} {location}"
                pre = pre_score(title, full_text)
                if not pre["bloqueada"] and pre["pre_score"] >= 5.0:
                    jobs.append({
                        "title": title, "company": company,
                        "url": url, "source": "Working Nomads",
                        "description": description[:2000],
                        "pre_score": pre["pre_score"],
                        "encontrados": pre["encontrados"],
                    })
    except Exception as e:
        print(f"[WorkingNomads] Error: {e}")
    return jobs


def scrape_jobspresso() -> list:
    jobs = []
    try:
        r = requests.get(
            "https://jobspresso.co/wp-json/wp/v2/job_listing?per_page=50&status=publish",
            headers=HEADERS, timeout=15)
        data = r.json()
        for item in data:
            if not isinstance(item, dict):
                continue
            title_field = item.get("title", "")
            title = title_field.get("rendered", "") if isinstance(title_field, dict) else str(title_field)
            content_field = item.get("content", "")
            description = content_field.get("rendered", "") if isinstance(content_field, dict) else str(content_field)
            url = item.get("link", "")
            meta = item.get("meta", {})
            company = meta.get("_company_name", "") if isinstance(meta, dict) else ""
            pre = pre_score(title, description)
            if not pre["bloqueada"] and pre["pre_score"] >= 5.0:
                jobs.append({
                    "title": title, "company": company,
                    "url": url, "source": "Jobspresso",
                    "description": description[:2000],
                    "pre_score": pre["pre_score"],
                    "encontrados": pre["encontrados"],
                })
    except Exception as e:
        print(f"[Jobspresso] Error: {e}")
    return jobs


def scrape_himalayas() -> list:
    jobs = []
    searches = [
        {"q": "ai content researcher", "limit": 20},
        {"q": "content strategist", "limit": 20},
        {"q": "marketing automation", "limit": 20},
        {"q": "ai workflow", "limit": 20},
        {"q": "content operations", "limit": 20},
        {"q": "prompt engineer", "limit": 20},
        {"employment_type": "contract", "limit": 20},
        {"employment_type": "part_time", "limit": 20},
    ]
    seen_ids = set()
    for params in searches:
        try:
            r = requests.get(
                "https://himalayas.app/jobs/api/search",
                params=params, headers=HEADERS, timeout=15)
            data = r.json()
            for item in data.get("jobs", []):
                job_id_val = item.get("id", "")
                if job_id_val in seen_ids:
                    continue
                seen_ids.add(job_id_val)
                title = item.get("title", "")
                company = item.get("company", {}).get("name", "")
                description = item.get("description", "") or item.get("descriptionHtml", "")
                url = item.get("applicationUrl", "") or f"https://himalayas.app/jobs/{item.get('slug','')}"
                employment_type = item.get("employmentType", "")
                location = item.get("location", "") or ""
                if location_bloqueada(location):
                    continue
                full_text = f"{title} {employment_type} {description}"
                pre = pre_score(title, full_text)
                if not pre["bloqueada"] and pre["pre_score"] >= 5.0:
                    jobs.append({
                        "title": title, "company": company,
                        "url": url, "source": "Himalayas",
                        "description": description[:2000],
                        "pre_score": pre["pre_score"],
                        "encontrados": pre["encontrados"],
                    })
        except Exception as e:
            print(f"[Himalayas] Error: {e}")
    return jobs


def scrape_jobicy() -> list:
    jobs = []
    queries = [
        {"count": 50, "industry": "marketing", "job_types": "freelance"},
        {"count": 50, "industry": "marketing", "job_types": "contract"},
        {"count": 50, "industry": "marketing", "job_types": "part-time"},
        {"count": 50, "industry": "copywriting", "job_types": "freelance"},
        {"count": 50, "industry": "business", "job_types": "freelance"},
        {"count": 50, "industry": "seo", "job_types": "freelance"},
        {"count": 50, "geo": "latam"},
        {"count": 50, "geo": "argentina"},
    ]
    seen_ids = set()
    for params in queries:
        try:
            r = requests.get(
                "https://jobicy.com/api/v2/remote-jobs",
                params=params, headers=HEADERS, timeout=15)
            data = r.json()
            for item in data.get("jobs", []):
                jid = item.get("id", "")
                if jid in seen_ids:
                    continue
                seen_ids.add(jid)
                title = item.get("jobTitle", "")
                company = item.get("companyName", "")
                description = item.get("jobDescription", "") or item.get("jobExcerpt", "")
                url = item.get("url", "")
                job_type = item.get("jobType", "")
                location = item.get("jobGeo", "") or ""
                if location_bloqueada(location):
                    continue
                full_text = f"{title} {job_type} {description}"
                pre = pre_score(title, full_text)
                if not pre["bloqueada"] and pre["pre_score"] >= 5.0:
                    jobs.append({
                        "title": title, "company": company,
                        "url": url, "source": "Jobicy",
                        "description": description[:2000],
                        "pre_score": pre["pre_score"],
                        "encontrados": pre["encontrados"],
                    })
        except Exception as e:
            print(f"[Jobicy] Error: {e}")
    return jobs


def scrape_wellfound() -> list:
    """
    Wellfound (ex AngelList) — via RSS público por categoría.
    """
    jobs = []
    feeds = [
        "https://wellfound.com/jobs.rss?role=marketing",
        "https://wellfound.com/jobs.rss?role=operations",
        "https://wellfound.com/jobs.rss?role=content",
    ]
    for feed_url in feeds:
        try:
            r = requests.get(feed_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.content, "xml")
            for item in soup.find_all("item"):
                title = item.find("title").text if item.find("title") else ""
                description = item.find("description").text if item.find("description") else ""
                url = item.find("link").text if item.find("link") else ""
                company_tag = item.find("company") or item.find("source")
                company = company_tag.text if company_tag else ""
                pre = pre_score(title, description)
                if not pre["bloqueada"] and pre["pre_score"] >= 5.0:
                    jobs.append({
                        "title": title, "company": company,
                        "url": url, "source": "Wellfound",
                        "description": description[:2000],
                        "pre_score": pre["pre_score"],
                        "encontrados": pre["encontrados"],
                    })
        except Exception as e:
            print(f"[Wellfound] Error con {feed_url}: {e}")
    return jobs


def scrape_dynamitejobs() -> list:
    """
    Dynamite Jobs — RSS por categoría.
    """
    jobs = []
    feeds = [
        "https://dynamitejobs.com/remote-jobs/rss?category=marketing",
        "https://dynamitejobs.com/remote-jobs/rss?category=operations",
        "https://dynamitejobs.com/remote-jobs/rss?category=writing-editing",
    ]
    for feed_url in feeds:
        try:
            r = requests.get(feed_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.content, "xml")
            for item in soup.find_all("item"):
                title = item.find("title").text if item.find("title") else ""
                description = item.find("description").text if item.find("description") else ""
                url = item.find("link").text if item.find("link") else ""
                company_tag = item.find("company") or item.find("author")
                company = company_tag.text if company_tag else ""
                pre = pre_score(title, description)
                if not pre["bloqueada"] and pre["pre_score"] >= 5.0:
                    jobs.append({
                        "title": title, "company": company,
                        "url": url, "source": "Dynamite Jobs",
                        "description": description[:2000],
                        "pre_score": pre["pre_score"],
                        "encontrados": pre["encontrados"],
                    })
        except Exception as e:
            print(f"[DynamiteJobs] Error con {feed_url}: {e}")
    return jobs


def scrape_linkedin_jobspy() -> list:
    """
    LinkedIn via JobSpy — requiere: pip install python-jobspy
    Si no está instalado, falla silenciosamente.
    """
    jobs = []
    try:
        from jobspy import scrape_jobs
        searches = [
            "AI content researcher",
            "content operations strategist",
            "marketing automation specialist",
            "AI workflow specialist",
            "prompt engineer content",
        ]
        for search_term in searches:
            try:
                df = scrape_jobs(
                    site_name=["linkedin"],
                    search_term=search_term,
                    location="Worldwide",
                    results_wanted=10,
                    job_type="contract",
                )
                for _, row in df.iterrows():
                    title = str(row.get("title", ""))
                    company = str(row.get("company", ""))
                    description = str(row.get("description", ""))
                    url = str(row.get("job_url", ""))
                    location = str(row.get("location", ""))
                    if location_bloqueada(location):
                        continue
                    full_text = f"{title} {description} {location}"
                    pre = pre_score(title, full_text)
                    if not pre["bloqueada"] and pre["pre_score"] >= 5.0:
                        jobs.append({
                            "title": title, "company": company,
                            "url": url, "source": "LinkedIn (JobSpy)",
                            "description": description[:2000],
                            "pre_score": pre["pre_score"],
                            "encontrados": pre["encontrados"],
                        })
            except Exception as e:
                print(f"[LinkedIn JobSpy] Error búsqueda '{search_term}': {e}")
    except ImportError:
        print("[LinkedIn JobSpy] jobspy no instalado — saltando fuente.")
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


# ── PIPELINE PRINCIPAL ────────────────────────────────────────────────────────

def get_all_jobs() -> tuple[list, list]:
    """
    Retorna (jobs_para_email, jobs_borderline).
    - jobs_para_email: score Claude >= 6.0
    - jobs_borderline: score Claude 5.0-5.9 (para revisión manual)
    """
    # Cargar memoria de puestos ya vistos
    seen = load_seen_jobs()
    print(f"Puestos ya vistos en runs anteriores: {len(seen)}")

    # ── Scraping de todas las fuentes
    all_candidates = []
    sources = [
        ("Remote OK", scrape_remoteok),
        ("We Work Remotely", scrape_weworkremotely),
        ("Remotive", scrape_remotive),
        ("Working Nomads", scrape_workingnomads),
        ("Jobspresso", scrape_jobspresso),
        ("Himalayas", scrape_himalayas),
        ("Jobicy", scrape_jobicy),
        ("Wellfound", scrape_wellfound),
        ("Dynamite Jobs", scrape_dynamitejobs),
        ("LinkedIn", scrape_linkedin_jobspy),
    ]
    for name, fn in sources:
        print(f"Scrapeando {name}...")
        result = fn()
        print(f"  → {len(result)} candidatos pre-filtrados")
        all_candidates += result

    # Dedup y filtro de ya-vistos
    all_candidates = dedup(all_candidates)
    nuevos = []
    for job in all_candidates:
        jid = job_id(job["title"], job["company"], job["url"])
        if jid not in seen:
            job["_id"] = jid
            nuevos.append(job)

    print(f"\nCandidatos únicos nuevos para evaluar: {len(nuevos)}")

    # Ordenar por pre_score y limitar a los 30 más prometedores para Claude
    nuevos.sort(key=lambda x: x["pre_score"], reverse=True)
    nuevos = nuevos[:30]
    print(f"Limitando a los 30 candidatos con mayor pre_score para evaluación Claude")

    # ── Evaluación con Claude
    jobs_email = []
    jobs_borderline = []
    nuevos_vistos = set()

    print("\nEvaluando con Claude...")
    for i, job in enumerate(nuevos):
        print(f"  [{i+1}/{len(nuevos)}] {job['title'][:50]} — pre: {job['pre_score']}")

        eval_result = claude_evaluate(
            job["title"], job["company"],
            job["description"], job["source"]
        )

        # Marcar como visto siempre, independientemente del resultado
        nuevos_vistos.add(job["_id"])

        if eval_result is None:
            # Si Claude falla, usar pre_score como fallback
            if job["pre_score"] >= 6.0:
                job["score"] = job["pre_score"]
                job["resumen"] = "Evaluación automática (Claude no disponible)"
                job["por_que_encaja"] = "—"
                job["brecha_stack"] = "—"
                job["posibilidad_real"] = "unclear"
                job["red_flags"] = []
                job["location_restriction"] = "—"
                job["modalidad"] = "unclear"
                job["salario"] = "No especificado"
                jobs_email.append(job)
            continue

        score = float(eval_result.get("score", 0))
        job.update({
            "score": score,
            "resumen": eval_result.get("resumen", ""),
            "por_que_encaja": eval_result.get("por_que_encaja", ""),
            "brecha_stack": eval_result.get("brecha_stack", ""),
            "posibilidad_real": eval_result.get("posibilidad_real", ""),
            "red_flags": eval_result.get("red_flags", []),
            "location_restriction": eval_result.get("location_restriction", ""),
            "modalidad": eval_result.get("modalidad", "unclear"),
            "salario": eval_result.get("salario", "No especificado"),
        })

        print(f"    → Claude score: {score} | {job['posibilidad_real']}")

        if score >= 6.0:
            jobs_email.append(job)
        elif score >= 5.0:
            jobs_borderline.append(job)
        # < 5.0 → descartado silenciosamente

    # Guardar memoria actualizada
    seen.update(nuevos_vistos)
    save_seen_jobs(seen)
    print(f"\nMemoria actualizada: {len(seen)} puestos vistos en total")

    # Guardar borderline para revisión manual (se sobreescribe)
    with open("borderline_jobs.json", "w") as f:
        json.dump(jobs_borderline, f, ensure_ascii=False, indent=2)
    print(f"Borderline (5.0-5.9): {len(jobs_borderline)} guardados en borderline_jobs.json")

    jobs_email.sort(key=lambda x: x["score"], reverse=True)
    print(f"Para el email (≥6.0): {len(jobs_email)}")

    return jobs_email, jobs_borderline


if __name__ == "__main__":
    jobs_email, jobs_borderline = get_all_jobs()
    with open("jobs_output.json", "w") as f:
        json.dump(jobs_email, f, ensure_ascii=False, indent=2)
    print("Guardado en jobs_output.json")
