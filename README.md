# 🎯 Job Hunt Agent — Nahuel Ramon

Agente automático que scrapea ofertas laborales remotas, las filtra y puntúa contra tu perfil, y manda un email diario cada mañana de lunes a viernes.

**Fuentes:** Remote OK · We Work Remotely · Remotive

---

## Setup (una sola vez)

### 1. Crear el repositorio en GitHub

1. Andá a [github.com/new](https://github.com/new)
2. Nombre: `job-hunt-agent` (privado recomendado)
3. No inicialices con README
4. Subí todos estos archivos al repo

### 2. Configurar Gmail para envío automático

Gmail no acepta tu contraseña normal para apps externas. Necesitás una **App Password**:

1. Andá a tu cuenta Google → [myaccount.google.com/security](https://myaccount.google.com/security)
2. Activá **Verificación en dos pasos** (si no está activa)
3. Buscá **App passwords** → creá una nueva para "Mail" + "Other" → nombrala "job-agent"
4. Copiá la contraseña de 16 caracteres que te genera (tipo: `abcd efgh ijkl mnop`)

### 3. Agregar los Secrets a GitHub

1. En tu repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
2. Crear estos 3 secrets:

| Nombre | Valor |
|---|---|
| `GMAIL_USER` | tu email completo (ej: `nahuel@gmail.com`) |
| `GMAIL_APP_PASSWORD` | la app password de 16 caracteres |
| `RECIPIENT_EMAIL` | donde querés recibir el email (puede ser el mismo) |

### 4. Activar GitHub Actions

1. En tu repo → pestaña **Actions**
2. Si te pide confirmar, hacé click en "I understand my workflows, go ahead and enable them"
3. Listo — va a correr automáticamente cada mañana (lunes a viernes, 8 AM Argentina)

---

## Correr manualmente

En GitHub → **Actions** → **Job Hunt Diario** → **Run workflow**

O localmente:
```bash
pip install -r requirements.txt
export GMAIL_USER="tu@gmail.com"
export GMAIL_APP_PASSWORD="abcd efgh ijkl mnop"
export RECIPIENT_EMAIL="tu@gmail.com"
python main.py
```

---

## Cómo funciona el scoring

Cada oferta recibe un puntaje de 0 a 10:

- **≥ 7.5** 🟢 → Aplicar ahora
- **6.0 – 7.5** 🟡 → Vale la pena mirar
- **< 6.0** → Filtrada, no llega al email

El score sube con keywords como: `ai content`, `workflow automation`, `content strategy`, `async`, `flexible`...

El score baja con: `data engineer`, `on-site`, `hybrid`, `per word`, `sales`, `fixed schedule`...

---

## Modificar el perfil

Editá `src/scraper.py`:
- `KEYWORDS_POSITIVAS` — lo que querés que suba el score
- `KEYWORDS_NEGATIVAS` — lo que querés que baje el score
- `RED_FLAGS_MODALIDAD` — red flags de modalidad de trabajo

---

## Agregar más fuentes

El archivo `src/scraper.py` tiene funciones separadas por fuente (`scrape_remoteok`, `scrape_weworkremotely`, `scrape_remotive`). Podés agregar nuevas siguiendo el mismo patrón.
