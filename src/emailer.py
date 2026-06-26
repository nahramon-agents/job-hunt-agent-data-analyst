import smtplib
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


GRUPOS = {
    1: {"emoji": "🔬", "nombre": "AI Content & Story Researcher", "fit": "95%"},
    2: {"emoji": "⚙️",  "nombre": "AI Content & Operations Strategist", "fit": "90%"},
    3: {"emoji": "🤖", "nombre": "AI Workflow & Automation Specialist", "fit": "85%"},
    4: {"emoji": "📊", "nombre": "Data & Growth Analyst — Content & Creator", "fit": "80%"},
    5: {"emoji": "🚀", "nombre": "Digital Strategy & Growth Lead — Creator & Education", "fit": "80%"},
    0: {"emoji": "📁", "nombre": "Sin grupo definido", "fit": "—"},
}


def score_color(score: float) -> str:
    if score >= 8.0:
        return "#22c55e"
    elif score >= 6.5:
        return "#84cc16"
    else:
        return "#f59e0b"


def score_emoji(score: float) -> str:
    if score >= 8.0:
        return "🟢"
    elif score >= 6.5:
        return "🟡"
    else:
        return "⚪"


def posibilidad_color(posibilidad: str) -> tuple:
    p = posibilidad.lower() if posibilidad else ""
    if p.startswith("alta"):
        return "#166534", "#86efac"
    elif p.startswith("media"):
        return "#713f12", "#fde68a"
    else:
        return "#450a0a", "#fca5a5"


def build_job_card(job: dict) -> str:
    score = job.get("score", 0)
    color = score_color(score)
    emoji = score_emoji(score)

    resumen = job.get("resumen", "—")
    por_que = job.get("por_que_encaja", "—")
    brecha = job.get("brecha_stack", "—")
    posibilidad = job.get("posibilidad_real", "—")
    red_flags = job.get("red_flags", [])
    location = job.get("location_restriction", "Sin restricción detectada")
    modalidad = job.get("modalidad", "unclear")
    salario = job.get("salario", "No especificado")

    pos_bg, pos_text = posibilidad_color(posibilidad)

    red_flags_html = ""
    if red_flags:
        flags_str = " · ".join(red_flags)
        red_flags_html = f"""
        <p style="margin:6px 0 0 0; color:#fca5a5; font-size:12px;">
          🚩 <strong>Red flags:</strong> {flags_str}
        </p>"""

    return f"""
    <div style="background:#1e293b; border-radius:12px; padding:20px; margin-bottom:14px;
                border-left: 4px solid {color};">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
        <div style="flex:1;">
          <p style="margin:0 0 3px 0; font-size:17px; font-weight:700; color:#f1f5f9;">
            {emoji} {job['title']}
          </p>
          <p style="margin:0; font-size:13px; color:#94a3b8;">
            {job['company']} · {job['source']}
          </p>
        </div>
        <div style="background:{color}; color:#0f172a; border-radius:8px;
                    padding:5px 12px; font-weight:800; font-size:20px; white-space:nowrap; flex-shrink:0;">
          {score}/10
        </div>
      </div>

      <div style="margin-top:10px;">
        <span style="background:{pos_bg}; color:{pos_text}; border-radius:6px;
                     padding:3px 10px; font-size:12px; font-weight:700;">
          POSIBILIDAD: {posibilidad}
        </span>
      </div>

      <div style="margin-top:12px; padding:12px; background:#0f172a; border-radius:8px;">
        <p style="margin:0 0 4px 0; font-size:11px; color:#64748b; text-transform:uppercase; letter-spacing:0.5px;">QUÉ ES ESTE ROL</p>
        <p style="margin:0; font-size:13px; color:#cbd5e1; line-height:1.5;">{resumen}</p>
      </div>

      <p style="margin:10px 0 0 0; color:#86efac; font-size:13px;">
        ✅ <strong>Por qué encaja:</strong> {por_que}
      </p>
      <p style="margin:6px 0 0 0; color:#fcd34d; font-size:13px;">
        🔧 <strong>Brecha de stack:</strong> {brecha}
      </p>
      {red_flags_html}

      <div style="margin-top:12px; display:flex; flex-wrap:wrap; gap:8px; font-size:12px;">
        <span style="background:#1e3a5f; color:#93c5fd; padding:3px 10px; border-radius:6px;">📍 {location}</span>
        <span style="background:#1e3a5f; color:#93c5fd; padding:3px 10px; border-radius:6px;">🕐 {modalidad}</span>
        <span style="background:#1e3a5f; color:#93c5fd; padding:3px 10px; border-radius:6px;">💰 {salario}</span>
      </div>

      <a href="{job['url']}" style="display:inline-block; margin-top:14px; padding:8px 18px;
         background:#6366f1; color:#fff; border-radius:8px; text-decoration:none;
         font-size:13px; font-weight:600;">Ver oferta →</a>
    </div>
    """


def build_grupo_section(grupo_num: int, jobs: list) -> str:
    if not jobs:
        return ""
    g = GRUPOS[grupo_num]
    jobs_sorted = sorted(jobs, key=lambda x: x.get("score", 0), reverse=True)
    cards = "".join(build_job_card(j) for j in jobs_sorted)
    return f"""
    <div style="margin-bottom:32px;">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:14px;
                  border-bottom:1px solid #1e293b; padding-bottom:10px;">
        <span style="font-size:20px;">{g['emoji']}</span>
        <div>
          <h2 style="margin:0; color:#f1f5f9; font-size:15px; font-weight:700;">
            GRUPO {grupo_num} — {g['nombre']}
          </h2>
          <p style="margin:2px 0 0 0; font-size:12px; color:#64748b;">Fit estimado: {g['fit']} · {len(jobs)} oferta{'s' if len(jobs) != 1 else ''}</p>
        </div>
      </div>
      {cards}
    </div>
    """


def build_email_html(jobs: list, borderline_count: int = 0) -> str:
    today = datetime.now().strftime("%d %b %Y")

    # Agrupar por grupo
    by_grupo = {1: [], 2: [], 3: [], 4: [], 5: []}
    for job in jobs:
        g = job.get("grupo", 0)
        if g in by_grupo:
            by_grupo[g].append(job)

    total_email = len(jobs)
    grupos_con_ofertas = sum(1 for v in by_grupo.values() if v)

    # Construir secciones solo para grupos con ofertas
    secciones = ""
    for g_num in (1, 2, 3, 4, 5):
        secciones += build_grupo_section(g_num, by_grupo[g_num])

    if not secciones.strip():
        secciones = """
        <div style="text-align:center; padding:40px 20px; color:#64748b;">
          <p style="font-size:16px;">No hubo ofertas que pasen el filtro hoy.</p>
          <p style="font-size:13px;">Los borderline están en el repo para revisión manual.</p>
        </div>"""

    borderline_note = ""
    if borderline_count > 0:
        borderline_note = f"""
        <div style="background:#1e293b; border-radius:10px; padding:14px 20px; margin-bottom:24px;
                    border-left:4px solid #64748b;">
          <p style="margin:0; color:#94a3b8; font-size:13px;">
            📁 <strong>{borderline_count} ofertas borderline</strong> (score 5.0–5.9 o grupo 0) guardadas en
            <code style="color:#fcd34d;">borderline_jobs.json</code> en el repo para revisión manual.
          </p>
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin:0; padding:0; background:#0f172a; font-family: 'Segoe UI', Arial, sans-serif;">
      <div style="max-width:680px; margin:0 auto; padding:32px 16px;">

        <div style="text-align:center; margin-bottom:28px;">
          <h1 style="color:#f1f5f9; margin:0; font-size:22px;">🎯 Job Hunt — Nahuel Ramon</h1>
          <p style="color:#64748b; margin:6px 0 0 0; font-size:13px;">
            {today} · Evaluado por Claude · {grupos_con_ofertas} grupo{'s' if grupos_con_ofertas != 1 else ''} con ofertas
          </p>
        </div>

        <div style="display:flex; gap:10px; margin-bottom:24px; justify-content:center; flex-wrap:wrap;">
          <div style="background:#1e293b; border-radius:10px; padding:14px 20px; text-align:center; min-width:90px;">
            <p style="margin:0; font-size:26px; font-weight:800; color:#22c55e;">{total_email}</p>
            <p style="margin:4px 0 0 0; font-size:11px; color:#94a3b8;">En el email</p>
          </div>
          <div style="background:#1e293b; border-radius:10px; padding:14px 20px; text-align:center; min-width:90px;">
            <p style="margin:0; font-size:26px; font-weight:800; color:#64748b;">{borderline_count}</p>
            <p style="margin:4px 0 0 0; font-size:11px; color:#94a3b8;">Borderline</p>
          </div>
          <div style="background:#1e293b; border-radius:10px; padding:14px 20px; text-align:center; min-width:90px;">
            <p style="margin:0; font-size:26px; font-weight:800; color:#6366f1;">{grupos_con_ofertas}</p>
            <p style="margin:4px 0 0 0; font-size:11px; color:#94a3b8;">Grupos activos</p>
          </div>
        </div>

        {borderline_note}
        {secciones}

        <div style="margin-top:32px; text-align:center; color:#334155; font-size:11px; line-height:1.8;">
          <p style="margin:0;">Agente automático · Claude Sonnet · Nahuel Ramon · Córdoba, Argentina</p>
          <p style="margin:0;">Remote OK · WWR · Remotive · Working Nomads · Jobspresso · Himalayas · Jobicy · Wellfound · Dynamite Jobs · LinkedIn</p>
        </div>

      </div>
    </body>
    </html>
    """


def send_email(jobs: list, borderline_count: int = 0):
    gmail_user = os.environ["GMAIL_USER"]
    gmail_pass = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("RECIPIENT_EMAIL", gmail_user)

    today = datetime.now().strftime("%d %b %Y")
    grupos_activos = len(set(j.get("grupo", 0) for j in jobs if j.get("grupo", 0) > 0))

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎯 {len(jobs)} ofertas · {grupos_activos} grupos · {borderline_count} borderline · {today}"
    msg["From"] = gmail_user
    msg["To"] = recipient

    html_body = build_email_html(jobs, borderline_count)
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, recipient, msg.as_string())
        print(f"Email enviado a {recipient}")


if __name__ == "__main__":
    with open("jobs_output.json") as f:
        jobs = json.load(f)
    borderline = 0
    try:
        with open("borderline_jobs.json") as f:
            borderline = len(json.load(f))
    except Exception:
        pass
    send_email(jobs, borderline)
