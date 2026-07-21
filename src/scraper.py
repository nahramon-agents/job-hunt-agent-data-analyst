import re
import requests
import json
import os
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup

# ── PERFIL — NAHUEL RAMON ─────────────────────────────────────────────────────
# Data Analyst / Data Scientist — roles core: análisis de datos, BI, decision
# science, consultoría de datos, planning financiero.
# Ing. Industrial + 4 años Data Analyst en Novix (Python, SQL, forecasting,
# BI, presentaciones a dirección/gerencia) + AI Content Researcher freelance
# + co-estratega LarisaMagica (automatización, IA aplicada a operaciones)
# Stack: Python, SQL, Pandas, Power BI/Tableau, forecasting, Claude, ChatGPT,
# Perplexity, n8n/Zapier/Make
# Inglés C1 | Córdoba, Argentina | remoto global / LATAM, híbrido Córdoba como última opción

# ── GRUPOS DE ROLES Y KEYWORDS POR GRUPO ──────────────────────────────────────

GRUPOS_CONFIG = {
    1: {
        "nombre": "Data Analyst / Data Scientist — BI & Analytics",
        "fit": "95%",
        "nivel_a": [
            "data analyst", "data scientist", "business intelligence",
            "bi analyst", "analytics engineer",
            "analista de datos", "científico de datos", "cientifico de datos",
            "inteligencia de negocios",
        ],
        "nivel_b": [
            "python", "sql", "pandas", "power bi", "tableau",
            "forecasting", "eda", "exploratory data analysis",
        ],
    },
    2: {
        "nombre": "Decision Science / Data Consulting",
        "fit": "90%",
        "nivel_a": [
            "decision science", "decision scientist", "data consulting",
            "data consultant", "analytics consultant",
            "strategy & analytics", "strategy and analytics",
            "consultor de datos", "consultoría de datos", "consultoria de datos",
        ],
        "nivel_b": [
            "python", "sql", "pandas", "power bi", "tableau", "forecasting",
        ],
    },
    3: {
        "nombre": "Business/Process Analyst con IA aplicada",
        "fit": "80%",
        "nivel_a": [],
        # Condición conjunta: título de rol + señal de IA/automatización
        "nivel_a_conjunta": [
            (
                ["business analyst", "process analyst", "operations analyst",
                 "analista de negocios", "analista de procesos"],
                ["ai", "artificial intelligence", "automation", "genai",
                 "generative ai", "gen ai", "inteligencia artificial",
                 "automatización", "automatizacion"],
            ),
        ],
        "nivel_b": [],
    },
    4: {
        "nombre": "Forward Deployed / AI Solutions (moonshot)",
        "fit": "60%",
        "nivel_a": [
            "forward deployed", "forward-deployed",
            "ai solutions consultant", "ai solutions architect",
        ],
        "nivel_a_conjunta": [
            (
                ["implementation consultant"],
                ["ai", "artificial intelligence", "automation", "genai",
                 "generative ai"],
            ),
        ],
        "nivel_b": ["genai", "generative ai"],
    },
    5: {
        "nombre": "Financial/Business Planning — FP&A",
        "fit": "75%",
        "nivel_a": [
            "financial analyst", "business planning", "fp&a", "fpa",
            "forecasting analyst",
            "analista financiero", "planificación financiera",
            "planificacion financiera",
        ],
        "nivel_b": ["energy", "utilities", "forecasting"],
    },
}

# Bonus compartido (+0.3) — herramientas de IA/automatización (aplica a todos los grupos)
KEYWORDS_C = [
    "claude", "chatgpt", "notion", "canva", "mailerlite",
    "perplexity", "openai", "zapier", "make.com", "airtable", "n8n",
    "ai-assisted", "ai-powered", "ai tools", "ai-first", "generative ai", "llm",
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
# NOTA: "data scientist" NO está acá — es keyword core del Grupo 1/2.
# NOTA: modalidad (hybrid/on-site/in-office/in person) NO está acá — es un
# filtro pasa/no-pasa aparte (ver evaluar_geo_modalidad), no un puntaje.
KEYWORDS_PENALIZACION_FUERTE = [
    "data engineer", "machine learning engineer", "ml engineer",
    "software engineer", "backend engineer", "frontend engineer",
    "ai engineer", "full stack", "devops",
    "quality engineer", "qa engineer", "qa automation", "test engineer",
    "video editor",
    "cold calling", "account executive", "sales development",
    "fixed schedule", "9-5", "9 to 5",
]

# ── FILTRO DE MODALIDAD/GEOGRAFÍA (pasa o no pasa — nunca puntúa) ─────────────
# El texto del puesto es lo único que define el score y si Claude lo analiza.
# La geografía solo decide si el puesto entra en el pool y, si entra, en qué
# orden de prioridad se muestra — nunca suma ni resta puntos.

GEO_LATAM_EXPLICITO = [
    "latam", "latin america", "south america", "argentina",
    "remote (latam)", "remote, latam", "remote - latam", "latam only",
    "latam timezone", "latam time zone",
]

# Modalidad presencial — no pasa, salvo que sea explícitamente en Córdoba
MODALIDAD_PRESENCIAL = ["hybrid", "on-site", "onsite", "in-office", "in person"]


def evaluar_geo_modalidad(texto: str) -> dict:
    """
    Pasa/no pasa — no es un puntaje.
    - No pasa: modalidad híbrida/presencial explícita en cualquier lado que no
      sea Córdoba, o restricción geográfica explícita (ver GEO_RESTRICTIONS).
    - Pasa, con prioridad 1: LATAM/remoto explícito.
    - Pasa, con prioridad 2: sin señal geográfica explícita (no se penaliza
      la ausencia de dato) o remoto global explícito.
    - Pasa, con prioridad 3: híbrido/presencial explícito en Córdoba — última
      opción aceptada, pero al final del orden.
    La prioridad se usa SOLO para ordenar (ranking y email), nunca para sumar
    o restar del score.
    """
    t = texto.lower()
    es_cordoba = "cordoba" in t or "córdoba" in t

    for kw in MODALIDAD_PRESENCIAL:
        if kw in t:
            if es_cordoba:
                return {"pasa": True, "razon": None, "prioridad": 3}
            return {"pasa": False, "razon": f"modalidad presencial/híbrida sin Córdoba: {kw}", "prioridad": None}

    for kw in GEO_LATAM_EXPLICITO:
        if kw in t:
            return {"pasa": True, "razon": None, "prioridad": 1}

    return {"pasa": True, "razon": None, "prioridad": 2}

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


# ── PRE-SCORING (keywords, por grupo) ─────────────────────────────────────────

def _kw_en_texto(texto: str, kw: str) -> bool:
    """
    Keywords cortos y sin espacios (ai, eda, sql, llm, ppc, fpa, n8n...) son
    ambiguos como substring — "eda" matcheaba dentro de "seedance" (una
    herramienta de IA de video), "ai" dentro de "email"/"domain". Para esos
    se exige borde de palabra. Las frases largas/multi-palabra (sin ese
    riesgo) se buscan como substring normal, igual que antes.
    """
    if len(kw) <= 4 and " " not in kw:
        return re.search(r"\b" + re.escape(kw) + r"\b", texto) is not None
    return kw in texto


def calc_grupo_score(title: str, texto: str, grupo_num: int) -> tuple:
    """
    Score de keywords para UN grupo específico, basado únicamente en el texto
    del puesto. Nivel A se busca SOLO en el título — es lo que identifica QUÉ
    ES el rol, y buscarlo en descripciones de miles de caracteres (texto
    institucional, beneficios, etc.) da falsos positivos (ej. "process
    analyst" mencionado de pasada en la descripción de un puesto de
    "Director, Revenue Systems Strategy" que no tiene nada que ver). Nivel B
    (stack) sí se busca en todo el texto — son señales que naturalmente
    aparecen en el cuerpo del aviso, no en el título.
    Geografía y seniority NO entran acá — geografía es un filtro pasa/no-pasa
    aparte (ver evaluar_geo_modalidad) y seniority no se puntúa.
    """
    cfg = GRUPOS_CONFIG[grupo_num]
    score = 2.0
    encontrados = {"A": [], "B": []}
    titulo = title.lower()

    for kw in cfg.get("nivel_a", []):
        if _kw_en_texto(titulo, kw):
            score += 1.5
            encontrados["A"].append(kw)

    for roles, condiciones in cfg.get("nivel_a_conjunta", []):
        rol_match = next((r for r in roles if _kw_en_texto(titulo, r)), None)
        if rol_match and any(_kw_en_texto(texto, c) for c in condiciones):
            score += 1.5
            encontrados["A"].append(f"{rol_match} + IA/automation")

    for kw in cfg.get("nivel_b", []):
        if _kw_en_texto(texto, kw):
            score += 0.7
            encontrados["B"].append(kw)

    # Los bonus de cultura/herramientas (IA, async) solo suman si el grupo ya
    # tiene un match de Nivel A (título) — un solo keyword de Nivel B (ej.
    # "sql" o "energy" mencionado una vez en una descripción larga) no alcanza
    # para desbloquear todo el resto de la pila de bonus.
    if encontrados["A"]:
        for kw in KEYWORDS_C:
            if _kw_en_texto(texto, kw):
                score += 0.3

        for kw in KEYWORDS_ASYNC:
            if _kw_en_texto(texto, kw):
                score += 1.2

    for kw in KEYWORDS_PENALIZACION_MEDIA:
        if _kw_en_texto(texto, kw):
            score -= 1.0

    # Techo, no solo resta: en descripciones largas (texto institucional de
    # la empresa, secciones de beneficios, etc.) los bonus de cultura/
    # herramientas pueden acumular más que el -2.5 y "tapar" la señal de que
    # el rol es de otro tipo (ej. "Account Executive" con mucho texto de
    # marketing terminaba en 5.3 pese a la penalización). Si matchea, el
    # score de ESE grupo no puede superar 1.5 — no importa cuánto acumuló.
    penalizacion_fuerte = any(_kw_en_texto(texto, kw) for kw in KEYWORDS_PENALIZACION_FUERTE)
    if penalizacion_fuerte:
        score = min(score, 1.5)

    score = round(min(max(score, 0), 10), 1)
    return score, encontrados


def pre_score(title: str, description: str) -> dict:
    """
    Scoring por keywords ponderadas, calculado independientemente para cada
    uno de los 5 grupos, basado solo en el texto del puesto. Actúa como
    pre-filtro antes de Claude — cada grupo tiene su propio ranking (ver
    CUPO_POR_GRUPO en get_all_jobs). La modalidad/geografía se evalúa aparte
    como pasa/no-pasa (ver evaluar_geo_modalidad) y determina "prioridad_geo",
    que se usa solo para ordenar, nunca para puntuar.
    """
    texto = (title + " " + description).lower()

    def _bloqueada(razon: str) -> dict:
        return {
            "bloqueada": True, "razon_bloqueo": razon,
            "grupo_scores": {}, "max_score": 0,
            "prioridad_geo": None, "encontrados": {},
        }

    # Filtro duro: industrias bloqueadas
    for ind in INDUSTRIAS_BLOQUEADAS:
        if ind in texto:
            return _bloqueada(f"industria bloqueada: {ind}")

    # Filtro duro: restricciones geo explícitas en texto
    for geo in GEO_RESTRICTIONS:
        if geo in texto:
            return _bloqueada(f"restricción geográfica: {geo}")

    # Filtro duro: modalidad presencial/híbrida sin Córdoba
    geo_eval = evaluar_geo_modalidad(texto)
    if not geo_eval["pasa"]:
        return _bloqueada(geo_eval["razon"])

    grupo_scores = {}
    encontrados = {}
    for grupo_num in GRUPOS_CONFIG:
        score, matched = calc_grupo_score(title, texto, grupo_num)
        grupo_scores[grupo_num] = score
        encontrados[grupo_num] = matched

    return {
        "bloqueada": False,
        "razon_bloqueo": None,
        "grupo_scores": grupo_scores,
        "max_score": max(grupo_scores.values()),
        "prioridad_geo": geo_eval["prioridad"],
        "encontrados": encontrados,
    }


# ── CLAUDE COMO JUEZ ──────────────────────────────────────────────────────────

CLAUDE_SYSTEM_PROMPT = """Sos el evaluador de ofertas laborales de Nahuel Ramon. Tu trabajo es ser DIRECTO, HONESTO y REALISTA — no inflar el ego, no ser optimista de más.

PERFIL REAL DE NAHUEL:
- Título: Data Analyst / Data Scientist
- Background: Ingeniero Industrial + 4 años como Data Analyst en Novix (empresa argentina de energía) — análisis de datos, forecasting, reporting/BI, presentaciones a dirección y gerencia (incluso en portugués). Además: AI Content Researcher freelance para canal documental de YouTube en USA + co-estratega en LarisaMagica (automatización de operaciones con IA).
- Stack técnico: Python (nivel intermedio/autodidacta), SQL, Pandas, Power BI / Tableau (uso aplicado en Novix), forecasting, y herramientas de IA (Claude, ChatGPT, Perplexity) y automatización (n8n, Zapier, Make).
- Idiomas: Español nativo, Inglés C1 (TOEFL iBT), italiano/portugués intermedios
- Ubicación: Córdoba, Argentina.
- Situación actual: Nahuel necesita conseguir trabajo. Su experiencia de Data Analyst es como empleado real en Novix (no freelance); los roles de IA/contenido son freelance/colaboración adicional. No tiene certificaciones formales de empresas tech.

NO-NEGOCIABLES (estos sí son vetos duros):
- Modalidad: remoto (global o LATAM) es lo preferido. Un rol HÍBRIDO es aceptable ÚNICAMENTE si menciona explícitamente Córdoba, Argentina (o "Córdoba" a secas) como la sede — es una última opción válida, no la descartes. Un rol 100% presencial (on-site/in-office) SIN mención de Córdoba, o híbrido en cualquier otra ciudad/país, sí se descarta.
- Sin trabajar fines de semana — descartá solo si lo dice explícitamente
- Roles de ingeniería de software pura, diseño UX/UI, ventas puras sin componente analítico/estratégico

RESTRICCIONES GEOGRÁFICAS — REGLA CRÍTICA:
Solo marcá restricción geográfica si la oferta lo dice EXPLÍCITAMENTE con frases como "must be located in", "US only", "requires work authorization", "must reside in".
Si la empresa es de Australia, UK o USA pero NO dice que el candidato debe estar ahí — NO es restricción. Marcalo como "Verificar con la empresa" en red_flags, pero NO bajes el score por eso. Muchas empresas globales contratan remoto worldwide aunque tengan sede en otro país.

FILTRO DE VALORES — SOLO VETA LO EXPLÍCITAMENTE DAÑINO:
Descartá con score bajo ÚNICAMENTE si la empresa opera en: gambling, tabaco, alcohol, tecnología de vigilancia/manipulación masiva, industrias extractivistas (minería, petróleo), fast fashion sin propósito.
Una empresa B2B de software, finanzas, salud corporativa, hardware, o cualquier industria "neutral" NO es motivo de descarte. El tipo de empresa no es un veto — solo lo es si hay daño explícito. Nahuel necesita trabajar y puede hacerlo en empresas de distintos sectores.

TIPO DE EMPRESA — NO ES CRITERIO DE DESCARTE:
Que sea corporativa, grande, orientada a ventas B2B, o de cualquier industria — ninguna de esas cosas descarta una oferta. El agente evalúa el ROL, no la cultura de la empresa.

GRUPOS DE ROLES — clasificá la oferta en UNO de estos grupos:

GRUPO 1 — Data Analyst / Data Scientist — BI & Analytics (fit 95%)
Roles core: Data Analyst, Data Scientist, BI Analyst, Analytics Engineer. Es literalmente el título de Nahuel — el bucket de mayor volumen esperado. Empresas: cualquier industria.

GRUPO 2 — Decision Science / Data Consulting (fit 90%)
Roles: Decision Scientist, Data Consultant, Analytics Consultant, Strategy & Analytics. Se diferencia del Grupo 1 por el componente de consultoría a cliente/dirección — justo la experiencia real de Nahuel en Novix presentando a gerencia.

GRUPO 3 — Business/Process Analyst con IA aplicada (fit 80%)
Roles: Business Analyst, Process Analyst, Operations Analyst — CON mención de IA/automatización/GenAI en el título o la descripción. Si es un Business Analyst genérico sin ningún componente de IA/automatización, NO entra en este grupo (evaluar como Grupo 0 u otro si aplica).

GRUPO 4 — Forward Deployed / AI Solutions (moonshot, fit 60%)
Roles: Forward Deployed Engineer/Consultant, AI Solutions Consultant, Implementation Consultant con IA. Bucket ambicioso — el gap real suele ser ingeniería de software más pesada de la que tiene Nahuel, por eso el fit es más bajo, pero vale la pena que los vea.

GRUPO 5 — Financial/Business Planning Analyst — FP&A (fit 75%)
Roles: Financial Analyst, Business Planning Analyst, FP&A, forecasting — especialmente en energía/utilities (como Novix) o cualquier sector con forecasting. Es directamente el rol que tuvo en Novix.

GRUPO 0 — No encaja en ningún grupo
Usá este grupo SOLO si el rol es claramente incompatible con el perfil de Nahuel: ingeniería de software, diseño UX/UI, ventas puras, roles presenciales confirmados sin Córdoba, roles que requieren certificaciones técnicas específicas que Nahuel no tiene.

IMPORTANTE: Sé generoso con los grupos. Si un rol tiene elementos de análisis de datos, BI, consultoría analítica, automatización con IA aplicada a procesos, o planificación financiera — probablemente encaja en alguno. La duda se resuelve a favor de incluirlo.

BRECHA DE STACK: evaluá "brecha_stack" contra el perfil de Data Analyst/Data Scientist (Python, SQL, Pandas, Power BI/Tableau, forecasting, experiencia de consultoría/presentación a stakeholders) — NO contra un perfil de AI Content/Operations.

Tu tarea: evaluar la oferta y devolver ÚNICAMENTE un JSON válido, sin texto antes ni después, sin backticks, sin markdown.

El JSON debe tener exactamente estas claves:
{
  "score": (float 0.0-10.0),
  "grupo": (entero: 0, 1, 2, 3, 4 o 5),
  "resumen": "(2 líneas en español: qué es el rol realmente y qué tipo de empresa es)",
  "por_que_encaja": "(1-2 líneas honestas sobre el fit real)",
  "brecha_stack": "(honesto y directo: qué pide el puesto que Nahuel no tiene o tiene débil, contra el perfil de Data Analyst/Data Scientist. Si no hay brecha significativa, decí 'Stack suficiente para este rol')",
  "posibilidad_real": "(una de estas tres: 'Alta', 'Media', 'Baja') + 1 línea explicando por qué",
  "red_flags": ["lista de red flags — solo hechos explícitos de la oferta, no suposiciones. Máximo 3."],
  "location_restriction": "(SOLO si la oferta lo dice explícitamente. Si no, escribí: 'Sin restricción explícita — verificar si aplica remoto global')",
  "modalidad": "(una de: full-time / part-time / contract / freelance / unclear)",
  "salario": "(lo que diga la oferta textualmente, o 'No especificado')"
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
            description = item.get("description") or ""
            url = item.get("url", "")
            tags = " ".join(item.get("tags", []))
            full_text = f"{title} {tags} {description} {location}"
            pre = pre_score(title, full_text)
            if not pre["bloqueada"] and pre["max_score"] >= 3.0:
                jobs.append({
                    "title": title, "company": company,
                    "url": url, "source": "Remote OK",
                    "description": description[:2000],
                    "pre_score": pre["max_score"],
                    "grupo_scores": pre["grupo_scores"],
                    "prioridad_geo": pre["prioridad_geo"],
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
                if not pre["bloqueada"] and pre["max_score"] >= 3.0:
                    jobs.append({
                        "title": title_clean, "company": company,
                        "url": url, "source": f"We Work Remotely ({category})",
                        "description": description[:2000],
                        "pre_score": pre["max_score"],
                        "grupo_scores": pre["grupo_scores"],
                        "prioridad_geo": pre["prioridad_geo"],
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
                description = item.get("description") or ""
                url = item.get("url", "")
                tags = " ".join(item.get("tags", []))
                location = item.get("candidate_required_location", "")
                if location_bloqueada(location):
                    continue
                full_text = f"{title} {tags} {description} {location}"
                pre = pre_score(title, full_text)
                if not pre["bloqueada"] and pre["max_score"] >= 3.0:
                    jobs.append({
                        "title": title, "company": company,
                        "url": url, "source": "Remotive",
                        "description": description[:2000],
                        "pre_score": pre["max_score"],
                        "grupo_scores": pre["grupo_scores"],
                        "prioridad_geo": pre["prioridad_geo"],
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
                description = item.get("description") or ""
                url = item.get("url", "")
                # Working Nomads: el campo location viene en la oferta
                location = item.get("location", "") or ""
                if location_bloqueada(location):
                    continue
                full_text = f"{title} {description} {location}"
                pre = pre_score(title, full_text)
                if not pre["bloqueada"] and pre["max_score"] >= 3.0:
                    jobs.append({
                        "title": title, "company": company,
                        "url": url, "source": "Working Nomads",
                        "description": description[:2000],
                        "pre_score": pre["max_score"],
                        "grupo_scores": pre["grupo_scores"],
                        "prioridad_geo": pre["prioridad_geo"],
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
            title = item.get("title", {}).get("rendered", "")
            description = item.get("content", {}).get("rendered", "")
            url = item.get("link", "")
            company = item.get("meta", {}).get("_company_name", "")
            pre = pre_score(title, description)
            if not pre["bloqueada"] and pre["max_score"] >= 3.0:
                jobs.append({
                    "title": title, "company": company,
                    "url": url, "source": "Jobspresso",
                    "description": description[:2000],
                    "pre_score": pre["max_score"],
                    "grupo_scores": pre["grupo_scores"],
                    "prioridad_geo": pre["prioridad_geo"],
                    "encontrados": pre["encontrados"],
                })
    except Exception as e:
        print(f"[Jobspresso] Error: {e}")
    return jobs


def scrape_himalayas() -> list:
    jobs = []
    searches = [
        {"q": "data analyst", "limit": 20},
        {"q": "data scientist", "limit": 20},
        {"q": "business intelligence analyst", "limit": 20},
        {"q": "decision scientist", "limit": 20},
        {"q": "financial analyst", "limit": 20},
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
                description = item.get("description") or item.get("descriptionHtml") or ""
                url = item.get("applicationUrl", "") or f"https://himalayas.app/jobs/{item.get('slug','')}"
                employment_type = item.get("employmentType", "")
                location = item.get("location", "") or ""
                if location_bloqueada(location):
                    continue
                full_text = f"{title} {employment_type} {description}"
                pre = pre_score(title, full_text)
                if not pre["bloqueada"] and pre["max_score"] >= 3.0:
                    jobs.append({
                        "title": title, "company": company,
                        "url": url, "source": "Himalayas",
                        "description": description[:2000],
                        "pre_score": pre["max_score"],
                        "grupo_scores": pre["grupo_scores"],
                        "prioridad_geo": pre["prioridad_geo"],
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
                if not pre["bloqueada"] and pre["max_score"] >= 3.0:
                    jobs.append({
                        "title": title, "company": company,
                        "url": url, "source": "Jobicy",
                        "description": description[:2000],
                        "pre_score": pre["max_score"],
                        "grupo_scores": pre["grupo_scores"],
                        "prioridad_geo": pre["prioridad_geo"],
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
        "https://wellfound.com/jobs.rss?role=data",
        "https://wellfound.com/jobs.rss?role=finance",
        "https://wellfound.com/jobs.rss?role=operations",
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
                if not pre["bloqueada"] and pre["max_score"] >= 3.0:
                    jobs.append({
                        "title": title, "company": company,
                        "url": url, "source": "Wellfound",
                        "description": description[:2000],
                        "pre_score": pre["max_score"],
                        "grupo_scores": pre["grupo_scores"],
                        "prioridad_geo": pre["prioridad_geo"],
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
        "https://dynamitejobs.com/remote-jobs/rss?category=data-science",
        "https://dynamitejobs.com/remote-jobs/rss?category=finance-legal",
        "https://dynamitejobs.com/remote-jobs/rss?category=operations",
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
                if not pre["bloqueada"] and pre["max_score"] >= 3.0:
                    jobs.append({
                        "title": title, "company": company,
                        "url": url, "source": "Dynamite Jobs",
                        "description": description[:2000],
                        "pre_score": pre["max_score"],
                        "grupo_scores": pre["grupo_scores"],
                        "prioridad_geo": pre["prioridad_geo"],
                        "encontrados": pre["encontrados"],
                    })
        except Exception as e:
            print(f"[DynamiteJobs] Error con {feed_url}: {e}")
    return jobs


def scrape_jobspy_sites() -> list:
    """
    LinkedIn + Indeed + ZipRecruiter + Glassdoor + Google Jobs, todos vía
    JobSpy en una sola pasada por término de búsqueda — requiere:
    pip install python-jobspy. Si no está instalado, falla silenciosamente.
    """
    jobs = []
    try:
        from jobspy import scrape_jobs
        searches = [
            "data analyst",
            "data scientist",
            "business intelligence analyst",
            "decision scientist",
            "financial analyst FP&A",
        ]
        site_names = ["linkedin", "indeed", "zip_recruiter", "glassdoor", "google"]
        for search_term in searches:
            try:
                df = scrape_jobs(
                    site_name=site_names,
                    search_term=search_term,
                    google_search_term=f"{search_term} remote jobs",
                    location="Worldwide",
                    results_wanted=10,
                    job_type="contract",
                )
                for _, row in df.iterrows():
                    # row.get(key, default) solo usa el default si falta la
                    # clave — pandas trae la columna presente pero en None/NaN
                    # para muchas filas, y str(None) da el string "None". Por
                    # eso "or ''" en vez de confiar en el default de .get().
                    title = str(row.get("title") or "")
                    company = str(row.get("company") or "")
                    description = str(row.get("description") or "")
                    url = str(row.get("job_url") or "")
                    location = str(row.get("location") or "")
                    site = str(row.get("site") or "jobspy")
                    if location_bloqueada(location):
                        continue
                    full_text = f"{title} {description} {location}"
                    pre = pre_score(title, full_text)
                    if not pre["bloqueada"] and pre["max_score"] >= 3.0:
                        jobs.append({
                            "title": title, "company": company,
                            "url": url, "source": f"JobSpy ({site.title()})",
                            "description": description[:2000],
                            "pre_score": pre["max_score"],
                            "grupo_scores": pre["grupo_scores"],
                            "prioridad_geo": pre["prioridad_geo"],
                            "encontrados": pre["encontrados"],
                        })
            except Exception as e:
                print(f"[JobSpy] Error búsqueda '{search_term}': {e}")
    except ImportError:
        print("[JobSpy] jobspy no instalado — saltando fuente.")
    return jobs


def _getonboard_company_name(job_id: str) -> str:
    """
    La API de búsqueda de GetOnBoard no trae el nombre de la empresa (la
    relación viene null en remote=true, y el endpoint de detalle da 401).
    El <title> de la página pública sí lo trae siempre, con el patrón
    "{puesto} at {EMPRESA} - {ubicación} | Get on Board". Solo se llama
    para los jobs que ya pasaron el filtro de keywords, no para todos los
    resultados crudos.
    """
    try:
        r = requests.get(
            f"https://www.getonbrd.com/jobs/{job_id}",
            headers=HEADERS, timeout=10)
        m = re.search(r"<title>.*? at (.+?)(?: - |\s*\|\s*Get on Board)", r.text)
        return m.group(1).strip() if m else ""
    except Exception:
        return ""


def scrape_getonboard() -> list:
    """
    GetOnBoard (getonbrd.com) — job board fuerte en LATAM (Chile, México,
    Argentina, Colombia). API pública de búsqueda:
    https://www.getonbrd.com/api/v0/search/jobs?query=...&remote=true
    """
    jobs = []
    searches = [
        "data analyst", "data scientist", "business intelligence",
        "decision science", "financial analyst",
        "analista de datos", "científico de datos",
    ]
    seen_ids = set()
    for term in searches:
        try:
            r = requests.get(
                "https://www.getonbrd.com/api/v0/search/jobs",
                params={"query": term, "remote": "true"},
                headers=HEADERS, timeout=15)
            data = r.json()
            for item in data.get("data", []):
                jid = item.get("id", "")
                if not jid or jid in seen_ids:
                    continue
                seen_ids.add(jid)
                attrs = item.get("attributes", {})
                title = attrs.get("title", "")
                description = attrs.get("description", "") or ""
                url = f"https://www.getonbrd.com/jobs/{jid}"
                full_text = f"{title} {description}"
                pre = pre_score(title, full_text)
                if not pre["bloqueada"] and pre["max_score"] >= 3.0:
                    jobs.append({
                        "title": title, "company": _getonboard_company_name(jid),
                        "url": url, "source": "GetOnBoard",
                        "description": description[:2000],
                        "pre_score": pre["max_score"],
                        "grupo_scores": pre["grupo_scores"],
                        "prioridad_geo": pre["prioridad_geo"],
                        "encontrados": pre["encontrados"],
                    })
        except Exception as e:
            print(f"[GetOnBoard] Error búsqueda '{term}': {e}")
    return jobs


def scrape_computrabajo_ar() -> list:
    """
    Computrabajo Argentina — no tiene API/RSS pública, pero la página de
    resultados es HTML renderizado del lado del servidor (a diferencia de
    Bumeran/Zonajobs, que son SPA y no se pueden scrapear sin navegador).
    LIMITACIÓN CONOCIDA: el listado no trae descripción, solo título/empresa/
    ubicación — el score se calcula solo contra el título, señal más débil
    que otras fuentes.
    """
    jobs = []
    searches = [
        "analista-de-datos", "business-intelligence", "analista-financiero",
        "cientifico-de-datos", "planificacion-financiera",
    ]
    for slug in searches:
        try:
            r = requests.get(
                f"https://ar.computrabajo.com/trabajo-de-{slug}",
                headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.content, "html.parser")
            for article in soup.find_all("article", class_="box_offer"):
                link = article.find("a", class_="js-o-link")
                if not link:
                    continue
                title = link.get_text(strip=True)
                url = "https://ar.computrabajo.com" + (link.get("href", "") or "")
                company_tag = article.find(attrs={"offer-grid-article-company-url": True})
                company = company_tag.get_text(strip=True) if company_tag else ""
                pre = pre_score(title, "")
                if not pre["bloqueada"] and pre["max_score"] >= 3.0:
                    jobs.append({
                        "title": title, "company": company,
                        "url": url, "source": "Computrabajo Argentina",
                        "description": "",
                        "pre_score": pre["max_score"],
                        "grupo_scores": pre["grupo_scores"],
                        "prioridad_geo": pre["prioridad_geo"],
                        "encontrados": pre["encontrados"],
                    })
        except Exception as e:
            print(f"[Computrabajo AR] Error búsqueda '{slug}': {e}")
    return jobs


def scrape_hackernews() -> list:
    """
    Hacker News "Ask HN: Who is hiring?" — thread mensual público, vía la API
    oficial de Firebase (sin autenticación, sin límite de uso razonable).
    Los comentarios son ofertas posteadas directo por fundadores/CTOs, sin
    pasar por LinkedIn ni ATS — mucha menos competencia que las fuentes
    tradicionales.
    """
    jobs = []
    try:
        r = requests.get(
            "https://hacker-news.firebaseio.com/v0/user/whoishiring.json",
            headers=HEADERS, timeout=15)
        submitted = r.json().get("submitted", [])[:20]

        thread_id = None
        kids = []
        for item_id in submitted:
            item = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json",
                headers=HEADERS, timeout=15).json()
            titulo = ((item or {}).get("title") or "").lower()
            if titulo.startswith("ask hn: who is hiring?"):
                thread_id = item_id
                kids = item.get("kids", [])
                break

        if thread_id is None:
            print("[HackerNews] No se encontró el thread de este mes")
            return jobs

        for kid_id in kids[:400]:
            try:
                comment = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{kid_id}.json",
                    headers=HEADERS, timeout=10).json()
                if not comment or comment.get("deleted") or comment.get("dead"):
                    continue
                raw_text = comment.get("text", "") or ""
                if not raw_text:
                    continue
                texto_plano = BeautifulSoup(raw_text, "html.parser").get_text(separator=" ")
                # No hay un campo "título" real acá (es texto libre) — el
                # Nivel A busca solo en el "title", así que si le pasamos
                # nada más que los primeros 120 caracteres, se pierde
                # cualquier mención del rol más adelante en el posteo. Le
                # pasamos el texto completo como "título" también.
                title_display = texto_plano.strip()[:120]
                pre = pre_score(texto_plano, texto_plano)
                if not pre["bloqueada"] and pre["max_score"] >= 3.0:
                    jobs.append({
                        "title": title_display, "company": "",
                        "url": f"https://news.ycombinator.com/item?id={kid_id}",
                        "source": "Hacker News (Who is Hiring)",
                        "description": texto_plano[:2000],
                        "pre_score": pre["max_score"],
                        "grupo_scores": pre["grupo_scores"],
                        "prioridad_geo": pre["prioridad_geo"],
                        "encontrados": pre["encontrados"],
                    })
            except Exception:
                continue
    except Exception as e:
        print(f"[HackerNews] Error: {e}")
    return jobs


# Empresas remote-friendly/LATAM con board público confirmado (verificado en
# vivo). No existe forma de "buscar en todo Greenhouse/Lever" — cada empresa
# expone su propio board, así que esto escala agregando empresas a la lista,
# no con una query abierta.
EMPRESAS_GREENHOUSE = [
    "remotecom", "canonical", "nubank", "gitlab", "bitso", "vtex", "webflow",
]
EMPRESAS_LEVER = ["xepelin", "dlocal", "kavak"]


def scrape_greenhouse_lever() -> list:
    """
    Boards públicos de Greenhouse y Lever para la lista curada de arriba.
    """
    jobs = []

    for slug in EMPRESAS_GREENHOUSE:
        try:
            r = requests.get(
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
                params={"content": "true"}, headers=HEADERS, timeout=15)
            data = r.json()
            for item in data.get("jobs", []):
                title = item.get("title", "")
                location = (item.get("location") or {}).get("name", "") or ""
                if location_bloqueada(location):
                    continue
                content_html = item.get("content", "") or ""
                description = BeautifulSoup(content_html, "html.parser").get_text(separator=" ")
                full_text = f"{title} {description} {location}"
                pre = pre_score(title, full_text)
                if not pre["bloqueada"] and pre["max_score"] >= 3.0:
                    jobs.append({
                        "title": title, "company": item.get("company_name", slug),
                        "url": item.get("absolute_url", ""), "source": "Greenhouse",
                        "description": description[:2000],
                        "pre_score": pre["max_score"],
                        "grupo_scores": pre["grupo_scores"],
                        "prioridad_geo": pre["prioridad_geo"],
                        "encontrados": pre["encontrados"],
                    })
        except Exception as e:
            print(f"[Greenhouse] Error '{slug}': {e}")

    for slug in EMPRESAS_LEVER:
        try:
            r = requests.get(
                f"https://api.lever.co/v0/postings/{slug}",
                headers=HEADERS, timeout=15)
            data = r.json()
            for item in data:
                title = item.get("text", "")
                location = (item.get("categories") or {}).get("location", "") or ""
                if location_bloqueada(location):
                    continue
                description = item.get("descriptionPlain", "") or ""
                full_text = f"{title} {description} {location}"
                pre = pre_score(title, full_text)
                if not pre["bloqueada"] and pre["max_score"] >= 3.0:
                    jobs.append({
                        "title": title, "company": slug,
                        "url": item.get("hostedUrl", ""), "source": "Lever",
                        "description": description[:2000],
                        "pre_score": pre["max_score"],
                        "grupo_scores": pre["grupo_scores"],
                        "prioridad_geo": pre["prioridad_geo"],
                        "encontrados": pre["encontrados"],
                    })
        except Exception as e:
            print(f"[Lever] Error '{slug}': {e}")

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

# Cupo de candidatos que llegan a Claude, repartido por grupo (ponderado por
# volumen esperado). Total: 30 — mismo costo de API que antes.
CUPO_POR_GRUPO = {1: 10, 2: 6, 3: 6, 4: 4, 5: 4}

# Umbral de score final (Claude + modificadores) para entrar al email.
# Grupo 4 (moonshot, 60% fit) tiene un corte más bajo a propósito: si no,
# casi nunca llegaría a 6.0 y el bucket quedaría invisible.
UMBRAL_EMAIL = {1: 6.0, 2: 6.0, 3: 6.0, 4: 5.0, 5: 6.0}
UMBRAL_BORDERLINE_MIN = {1: 5.0, 2: 5.0, 3: 5.0, 4: 4.0, 5: 5.0}


def get_all_jobs() -> tuple[list, list]:
    """
    Retorna (jobs_para_email, jobs_borderline).
    - jobs_para_email: score final (Claude + modificadores geo/seniority) >= umbral del grupo
    - jobs_borderline: un escalón por debajo del umbral de email (revisión manual)
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
        ("GetOnBoard", scrape_getonboard),
        ("JobSpy (LinkedIn/Indeed/ZipRecruiter/Glassdoor/Google)", scrape_jobspy_sites),
        ("Computrabajo Argentina", scrape_computrabajo_ar),
        ("Hacker News (Who is Hiring)", scrape_hackernews),
        ("Greenhouse/Lever (empresas curadas)", scrape_greenhouse_lever),
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

    # Ranking independiente por grupo — así ningún grupo queda opacado por
    # otro al recortar el total de candidatos que se mandan a Claude.
    # Desempate por prioridad_geo (1=LATAM, 2=remoto global/sin dato,
    # 3=híbrido Córdoba) — nunca afecta el score, solo el orden entre iguales.
    seleccionados = []
    ids_seleccionados = set()
    for grupo_num, cupo in CUPO_POR_GRUPO.items():
        ranking = sorted(
            nuevos,
            key=lambda j: (-j["grupo_scores"][grupo_num], j["prioridad_geo"]),
        )
        elegidos_grupo = 0
        for job in ranking:
            if elegidos_grupo >= cupo:
                break
            if job["grupo_scores"][grupo_num] < 3.0:
                break  # ranking está ordenado desc, no hay más candidatos válidos
            if job["_id"] not in ids_seleccionados:
                ids_seleccionados.add(job["_id"])
                seleccionados.append(job)
            elegidos_grupo += 1
    nuevos = seleccionados
    print(f"Seleccionados para evaluación Claude (top por grupo, cupo {CUPO_POR_GRUPO}): {len(nuevos)}")

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
            # Si Claude falla, usar pre_score (ya incluye modificadores) como fallback
            if job["pre_score"] >= 6.0:
                job["score"] = job["pre_score"]
                job["grupo"] = 0
                job["resumen"] = "Evaluación automática (Claude no disponible)"
                job["por_que_encaja"] = "—"
                job["brecha_stack"] = "—"
                job["posibilidad_real"] = "unclear"
                job["red_flags"] = []
                job["location_restriction"] = "—"
                job["modalidad"] = "unclear"
                job["salario"] = "No especificado"
                jobs_borderline.append(job)
            continue

        score = float(eval_result.get("score", 0))
        grupo = int(eval_result.get("grupo", 0))

        job.update({
            "score": score,
            "grupo": grupo,
            "resumen": eval_result.get("resumen", ""),
            "por_que_encaja": eval_result.get("por_que_encaja", ""),
            "brecha_stack": eval_result.get("brecha_stack", ""),
            "posibilidad_real": eval_result.get("posibilidad_real", ""),
            "red_flags": eval_result.get("red_flags", []),
            "location_restriction": eval_result.get("location_restriction", ""),
            "modalidad": eval_result.get("modalidad", "unclear"),
            "salario": eval_result.get("salario", "No especificado"),
        })

        print(f"    → Claude score: {score} | Grupo {grupo} | prioridad_geo {job['prioridad_geo']} | {job['posibilidad_real']}")

        umbral_email = UMBRAL_EMAIL.get(grupo, 6.0)
        umbral_borderline = UMBRAL_BORDERLINE_MIN.get(grupo, 5.0)

        if score >= umbral_email and grupo in (1, 2, 3, 4, 5):
            jobs_email.append(job)
        elif score >= umbral_borderline:
            # Borderline: score OK pero grupo 0, o score justo debajo del umbral de email
            jobs_borderline.append(job)
        # debajo del umbral de borderline → descartado silenciosamente

    # Guardar memoria actualizada
    seen.update(nuevos_vistos)
    save_seen_jobs(seen)
    print(f"\nMemoria actualizada: {len(seen)} puestos vistos en total")

    # Guardar borderline para revisión manual (se sobreescribe)
    with open("borderline_jobs.json", "w") as f:
        json.dump(jobs_borderline, f, ensure_ascii=False, indent=2)
    print(f"Borderline: {len(jobs_borderline)} guardados en borderline_jobs.json")

    jobs_email.sort(key=lambda x: (-x["score"], x["prioridad_geo"]))
    print(f"Para el email: {len(jobs_email)}")

    return jobs_email, jobs_borderline


if __name__ == "__main__":
    jobs_email, jobs_borderline = get_all_jobs()
    with open("jobs_output.json", "w") as f:
        json.dump(jobs_email, f, ensure_ascii=False, indent=2)
    print("Guardado en jobs_output.json")
