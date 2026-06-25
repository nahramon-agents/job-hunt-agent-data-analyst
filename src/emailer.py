import smtplib
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


def score_color(score: float) -> str:
    if score >= 8.0:
        return "#22c55e"   # verde fuerte
    elif score >= 6.5:
        return "#84cc16"   # verde claro
    else:
        return "#f59e0b"   # amarillo


def score_emoji(score: float) -> str:
    if score >= 8.0:
        return "🟢"
    elif score >= 6.5:
        return "🟡"
    else:
        return "⚪"


def posibilidad_color(posibilidad: str) -> tuple[str, str]:
    """Retorna (color_bg, color_text) según posibilidad real."""
    p = posibilidad.lower() if posibilidad else ""
    if p.startswith("alta"):
        return "#166534", "#86efac"   # verde oscuro, texto verde claro
    elif p.startswith("media"):
        return "#713f12", "#fde68a"   # marrón, texto amarillo
    else:
        return "#450a0a", "#fca5a5"   # rojo oscuro, texto rojo claro


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
    <div style="background:#1e293b; border-radius:12px; padding:20px; margin-bottom:16px;
                border-left: 4px solid {color};">

      <!-- Header: título + score -->
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

      <!-- Posibilidad real -->
      <div style="margin-top:12px;">
        <span style="background:{pos_bg}; color:{pos_text}; border-radius:6px;
                     padding:3px 10px; font-size:12px; font-weight:700;">
          POSIBILIDAD: {posibilidad}
        </span>
      </div>

      <!-- Resumen Claude -->
      <div style="margin-top:12px; padding:12px; background:#0f172a; border-radius:8px;">
        <p style="margin:0 0 4px 0; font-size:11px; color:#64748b; text-transform:uppercase; letter-spacing:0.5px;">
          QUÉ ES ESTE ROL
        </p>
        <p style="margin:0; font-size:13px; color:#cbd5e1; line-height:1.5;">{resumen}</p>
      </div>

      <!-- Por qué encaja -->
      <p style="margin:10px 0 0 0; color:#86efac; font-size:13px;">
        ✅ <strong>Por qué encaja:</strong> {por_que}
      </p>

      <!-- Brecha de stack — honesto -->
      <p style="margin:6px 0 0 0; color:#fcd34d; font-size:13px;">
        🔧 <strong>Brecha de stack:</strong> {brecha}
      </p>

      {red_flags_html}

      <!-- Metadata -->
      <div style="margin-top:12px; display:flex; flex-wrap:wrap; gap:8px; font-size:12px;">
        <span style="background:#1e3a5f; color:#93c5fd; padding:3px 10px; border-radius:6px;">
          📍 {location}
        </span>
        <span style="background:#1e3a5f; color:#93c5fd; padding:3px 10px; border-radius:6px;">
          🕐 {modalidad}
        </span>
        <span style="background:#1e3a5f; color:#93c5fd; padding:3px 10px; border-radius:6px;">
          💰 {salario}
        </span>
      </div>

      <a href="{job['url']}" style="display:inline-block; margin-top:14px; padding:8px 18px;
         background:#6366f1; color:#fff; border-radius:8px; text-decoration:none;
         font-size:13px; font-weight:600;">Ver oferta →</a>
    </div>
    """


def build_email_html(jobs: list, borderline_count: int = 0) -> str:
    today = datetime.now().strftime("%d %b %Y")
    top = [j for j in jobs if j.get("score", 0) >= 8.0]
    mid = [j for j in jobs if 6.0 <= j.get("score", 0) < 8.0]

    top_section = "".join(build_job_card(j) for j in top) if top else \
        "<p style='color:#64748b; font-size:14px;'>No hubo ofertas top hoy.</p>"
    mid_section = "".join(build_job_card(j) for j in mid) if mid else \
        "<p style='color:#64748b; font-size:14px;'>Ninguna en este rango hoy.</p>"

    borderline_note = ""
    if borderline_count > 0:
        borderline_note = f"""
        <div style="background:#1e293b; border-radius:10px; padding:14px 20px; margin-bottom:28px;
                    border-left:4px solid #64748b;">
          <p style="margin:0; color:#94a3b8; font-size:13px;">
            📁 <strong>{borderline_count} ofertas borderline</strong> (score 5.0–5.9) guardadas en
            <code style="color:#fcd34d;">borderline_jobs.json</code> en el repo para revisión manual.
          </p>
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin:0; padding:0; background:#0f172a; font-family: 'Segoe UI', Arial, sans-serif;">
      <div style="max-width:680px; margin:0 auto; padding:32px 16px;">

        <!-- Header -->
        <div style="text-align:center; margin-bottom:28px;">
          <h1 style="color:#f1f5f9; margin:0; font-size:22px;">🎯 Job Hunt — Nahuel Ramon</h1>
          <p style="color:#64748b; margin:6px 0 0 0; font-size:13px;">{today} · Evaluado por Claude · Roles estratégicos 1-2-3</p>
        </div>

        <!-- Stats -->
        <div style="display:flex; gap:10px; margin-bottom:24px; justify-content:center; flex-wrap:wrap;">
          <div style="background:#1e293b; border-radius:10px; padding:14px 20px; text-align:center; min-width:100px;">
            <p style="margin:0; font-size:26px; font-weight:800; color:#22c55e;">{len(top)}</p>
            <p style="margin:4px 0 0 0; font-size:11px; color:#94a3b8;">Aplicar ahora (≥8)</p>
          </div>
          <div style="background:#1e293b; border-radius:10px; padding:14px 20px; text-align:center; min-width:100px;">
            <p style="margin:0; font-size:26px; font-weight:800; color:#84cc16;">{len(mid)}</p>
            <p style="margin:4px 0 0 0; font-size:11px; color:#94a3b8;">Vale la pena (6-8)</p>
          </div>
          <div style="background:#1e293b; border-radius:10px; padding:14px 20px; text-align:center; min-width:100px;">
            <p style="margin:0; font-size:26px; font-weight:800; color:#64748b;">{borderline_count}</p>
            <p style="margin:4px 0 0 0; font-size:11px; color:#94a3b8;">Borderline (5-6)</p>
          </div>
          <div style="background:#1e293b; border-radius:10px; padding:14px 20px; text-align:center; min-width:100px;">
            <p style="margin:0; font-size:26px; font-weight:800; color:#6366f1;">{len(jobs)}</p>
            <p style="margin:4px 0 0 0; font-size:11px; color:#94a3b8;">Total email</p>
          </div>
        </div>

        {borderline_note}

        <!-- Top ofertas -->
        <h2 style="color:#22c55e; font-size:15px; margin:0 0 12px 0; text-transform:uppercase; letter-spacing:0.5px;">
          🟢 APLICAR AHORA — Score ≥ 8.0
        </h2>
        {top_section}

        <!-- Mid ofertas -->
        <h2 style="color:#84cc16; font-size:15px; margin:24px 0 12px 0; text-transform:uppercase; letter-spacing:0.5px;">
          🟡 VALE LA PENA EVALUAR — Score 6.0–7.9
        </h2>
        {mid_section}

        <!-- Footer -->
        <div style="margin-top:32px; text-align:center; color:#334155; font-size:11px; line-height:1.8;">
          <p style="margin:0;">Agente automático · Evaluado por Claude Sonnet · Nahuel Ramon · Córdoba, Argentina</p>
          <p style="margin:0;">Fuentes: Remote OK · WWR · Remotive · Working Nomads · Jobspresso · Himalayas · Jobicy · Wellfound · Dynamite Jobs · LinkedIn</p>
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
    top_count = len([j for j in jobs if j.get("score", 0) >= 8.0])
    total = len(jobs)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎯 {top_count} top · {total} en email · {borderline_count} borderline · {today}"
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
