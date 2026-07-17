# 🎯 Job Hunt Agent — Nahuel Ramon

Agente automático que scrapea ofertas laborales remotas, las filtra y puntúa contra el perfil de **Data Analyst / Data Scientist** de Nahuel, y manda un email cada corrida con las mejores ofertas organizadas por grupo de rol.

Corre solo, dos veces por semana, vía GitHub Actions — no requiere que nadie lo dispare a mano.

---

## Cómo funciona

**1. Scraping** — junta candidatos de 12 fuentes (ver abajo).

**2. Pre-filtro por keywords** — cada oferta se puntúa independientemente contra cada uno de los 5 grupos de rol (ver abajo). Se seleccionan los mejores candidatos de cada grupo (10/6/6/4/4 = 30 en total) para no gastar evaluaciones de Claude en ruido, y para que ningún grupo quede opacado por otro.

**3. Claude como juez final** — cada uno de esos ~30 candidatos se manda a la API de Claude, que evalúa el fit real, clasifica en uno de los 5 grupos, y devuelve resumen, brecha de stack, posibilidad real, restricciones geográficas, modalidad y salario.

**4. Modificadores transversales** — geografía (LATAM/remoto explícito, o híbrido en Córdoba como última opción) y seniority (penaliza Junior/Entry/Intern, boostea Mid/Senior) ajustan el score final, tanto en el pre-filtro como sobre el score que devuelve Claude.

**5. Email + memoria** — las ofertas que superan el umbral de su grupo van al email, organizadas por sección. Las que quedan cerca del umbral van a `borderline_jobs.json` para revisión manual. Todo lo evaluado se guarda en `seen_jobs.json` para no repetir ofertas entre corridas.

---

## Los 5 grupos de rol

| # | Grupo | Fit estimado |
|---|---|---|
| 1 | Data Analyst / Data Scientist — BI & Analytics | 95% |
| 2 | Decision Science / Data Consulting | 90% |
| 3 | Business/Process Analyst con IA aplicada | 80% |
| 4 | Forward Deployed / AI Solutions (moonshot) | 60% |
| 5 | Financial/Business Planning — FP&A | 75% |

El Grupo 4 (moonshot) tiene un umbral de email más bajo a propósito (5.0 en vez de 6.0) — si no, casi nunca llegaría a Claude con score alto y el bucket quedaría invisible.

---

## Fuentes (12)

Remote OK · We Work Remotely · Remotive · Working Nomads · Jobspresso · Himalayas · Jobicy · Wellfound · Dynamite Jobs · **GetOnBoard** (LATAM) · **JobSpy** (LinkedIn + Indeed + ZipRecruiter + Glassdoor + Google Jobs)

**Nota:** Wellfound y Dynamite Jobs tienen sus feeds RSS rotos del lado del sitio (403 / devuelven HTML en vez de XML) — quedan en el pipeline por si se arreglan solos, pero hoy no aportan volumen. Jobspresso y Jobicy también fallan intermitentemente cuando sus APIs están caídas o rate-limitean; el agente lo tolera (loggea el error y sigue con las demás fuentes).

---

## Setup (una sola vez)

### 1. Configurar Gmail para envío automático

Gmail no acepta tu contraseña normal para apps externas. Necesitás una **App Password**:

1. Andá a tu cuenta Google → [myaccount.google.com/security](https://myaccount.google.com/security)
2. Activá **Verificación en dos pasos** (si no está activa)
3. Buscá **App passwords** → creá una nueva para "Mail" + "Other" → nombrala "job-agent"
4. Copiá la contraseña de 16 caracteres que te genera (tipo: `abcd efgh ijkl mnop`)

### 2. Conseguir una API key de Anthropic

El juez de cada oferta es Claude, vía la API de Anthropic — necesitás una key de [console.anthropic.com](https://console.anthropic.com/) (tiene costo por uso, pero corriendo 2 veces por semana con ~30 evaluaciones por corrida es bajo).

### 3. Agregar los Secrets a GitHub

En el repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Nombre | Valor |
|---|---|
| `GMAIL_USER` | tu email completo (ej: `nahuel@gmail.com`) |
| `GMAIL_APP_PASSWORD` | la app password de 16 caracteres |
| `RECIPIENT_EMAIL` | donde querés recibir el email (puede ser el mismo) |
| `ANTHROPIC_API_KEY` | tu API key de Anthropic |

### 4. Activar GitHub Actions

En el repo → pestaña **Actions** → si pide confirmar, click en "I understand my workflows, go ahead and enable them".

---

## Cuándo corre

Automático: **lunes y jueves a las 8 AM Argentina** (definido en `.github/workflows/main.yml`).

Manual, desde GitHub → **Actions** → **Job Hunt Estratégico** → **Run workflow**.

O localmente:
```bash
pip install -r requirements.txt
pip install python-jobspy  # opcional, para LinkedIn/Indeed/ZipRecruiter/Glassdoor/Google
export GMAIL_USER="tu@gmail.com"
export GMAIL_APP_PASSWORD="abcd efgh ijkl mnop"
export RECIPIENT_EMAIL="tu@gmail.com"
export ANTHROPIC_API_KEY="sk-ant-..."
python main.py
```

Cada corrida en Actions hace auto-commit de `seen_jobs.json` y `borderline_jobs.json` actualizados al repo.

---

## Modificar el perfil o los grupos

Todo vive en `src/scraper.py`:

- `GRUPOS_CONFIG` — los 5 grupos, con sus keywords de Nivel A (peso alto) y Nivel B (peso menor). Si cambia el perfil o se quiere afinar un grupo, es acá.
- `KEYWORDS_C` — bonus compartido por mencionar herramientas de IA/automatización (solo suma si el grupo ya tiene un match de rol real).
- `KEYWORDS_ASYNC` — bonus por señales de modalidad flexible.
- `KEYWORDS_PENALIZACION_MEDIA` / `KEYWORDS_PENALIZACION_FUERTE` — roles que bajan el score (paid media, ingeniería de software, QA, etc).
- `calc_geo_modifier` / `calc_seniority_modifier` — los modificadores transversales de geografía y seniority.
- `CLAUDE_SYSTEM_PROMPT` — el prompt que define cómo Claude evalúa y clasifica cada oferta.
- `CUPO_POR_GRUPO`, `UMBRAL_EMAIL`, `UMBRAL_BORDERLINE_MIN` — cuántos candidatos por grupo llegan a Claude, y los umbrales de score para email/borderline.

## Agregar más fuentes

`src/scraper.py` tiene una función `scrape_*()` por fuente, todas con la misma forma: piden la API/RSS, arman `title`/`company`/`description`/`url`, corren `pre_score()`, y agregan el resultado si pasa el umbral. Agregar una fuente nueva es copiar el patrón de la más parecida (API JSON vs RSS) y sumarla a la lista `sources` dentro de `get_all_jobs()`.
