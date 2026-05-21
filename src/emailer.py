import smtplib
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


def score_color(score: float) -> str:
    if score >= 7.5:
        return "#22c55e"   # verde
    elif score >= 5.5:
        return "#f59e0b"   # amarillo
    else:
        return "#64748b"   # gris


def score_emoji(score: float) -> str:
    if score >= 7.5:
        return "🟢"
    elif score >= 5.5:
        return "🟡"
    else:
        return "⚪"


def build_job_card(job: dict) -> str:
    score = job["score"]
    positivos = ", ".join(job.get("positivos", [])) or "—"
    negativos = ", ".join(job.get("negativos", [])) or "ninguno"
    red_flags = ", ".join(job.get("red_flags", [])) or "ninguno"
    color = score_color(score)
    emoji = score_emoji(score)

    return f"""
    <div style="background:#1e293b; border-radius:12px; padding:20px; margin-bottom:16px;
                border-left: 4px solid {color};">
      <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
          <p style="margin:0 0 4px 0; font-size:18px; font-weight:700; color:#f1f5f9;">
            {emoji} {job['title']}
          </p>
          <p style="margin:0; font-size:14px; color:#94a3b8;">{job['company']} · {job['source']}</p>
        </div>
        <div style="background:{color}; color:#0f172a; border-radius:8px;
                    padding:6px 14px; font-weight:800; font-size:20px; white-space:nowrap;">
          {score}/10
        </div>
      </div>

      <div style="margin-top:14px; display:grid; gap:6px; font-size:13px;">
        <p style="margin:0; color:#86efac;">✅ <strong>Positivos:</strong> {positivos}</p>
        <p style="margin:0; color:#fca5a5;">🚩 <strong>Red flags:</strong> {red_flags}</p>
        <p style="margin:0; color:#fcd34d;">⚠️ <strong>Negativos:</strong> {negativos}</p>
      </div>

      <a href="{job['url']}" style="display:inline-block; margin-top:14px; padding:8px 18px;
         background:#6366f1; color:#fff; border-radius:8px; text-decoration:none;
         font-size:13px; font-weight:600;">Ver oferta →</a>
    </div>
    """


def build_email_html(jobs: list) -> str:
    today = datetime.now().strftime("%d %b %Y")
    top   = [j for j in jobs if j["score"] >= 7.5]
    mid   = [j for j in jobs if 5.5 <= j["score"] < 7.5]
    extra = [j for j in jobs if 3.5 <= j["score"] < 5.5]

    top_section = "".join(build_job_card(j) for j in top) if top else \
        "<p style='color:#64748b;'>No hubo ofertas top hoy. Mañana puede cambiar.</p>"
    mid_section = "".join(build_job_card(j) for j in mid) if mid else \
        "<p style='color:#64748b;'>Ninguna en este rango hoy.</p>"
    extra_section = "".join(build_job_card(j) for j in extra) if extra else \
        "<p style='color:#64748b;'>Ninguna hoy.</p>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin:0; padding:0; background:#0f172a; font-family: 'Segoe UI', sans-serif;">
      <div style="max-width:680px; margin:0 auto; padding:32px 16px;">

        <!-- Header -->
        <div style="text-align:center; margin-bottom:32px;">
          <h1 style="color:#f1f5f9; margin:0; font-size:24px;">🎯 Job Hunt — Nahuel Ramon</h1>
          <p style="color:#64748b; margin:6px 0 0 0;">{today} · Reporte diario automático</p>
        </div>

        <!-- Stats -->
        <div style="display:flex; gap:12px; margin-bottom:28px; justify-content:center; flex-wrap:wrap;">
          <div style="background:#1e293b; border-radius:10px; padding:14px 24px; text-align:center;">
            <p style="margin:0; font-size:28px; font-weight:800; color:#22c55e;">{len(top)}</p>
            <p style="margin:4px 0 0 0; font-size:12px; color:#94a3b8;">Aplicar ahora (≥7.5)</p>
          </div>
          <div style="background:#1e293b; border-radius:10px; padding:14px 24px; text-align:center;">
            <p style="margin:0; font-size:28px; font-weight:800; color:#f59e0b;">{len(mid)}</p>
            <p style="margin:4px 0 0 0; font-size:12px; color:#94a3b8;">Vale la pena (5.5–7.5)</p>
          </div>
          <div style="background:#1e293b; border-radius:10px; padding:14px 24px; text-align:center;">
            <p style="margin:0; font-size:28px; font-weight:800; color:#64748b;">{len(extra)}</p>
            <p style="margin:4px 0 0 0; font-size:12px; color:#94a3b8;">Ingreso extra (3.5–5.5)</p>
          </div>
          <div style="background:#1e293b; border-radius:10px; padding:14px 24px; text-align:center;">
            <p style="margin:0; font-size:28px; font-weight:800; color:#6366f1;">{len(jobs)}</p>
            <p style="margin:4px 0 0 0; font-size:12px; color:#94a3b8;">Total del día</p>
          </div>
        </div>

        <!-- Top ofertas -->
        <h2 style="color:#22c55e; font-size:16px; margin:0 0 12px 0;">🟢 APLICAR AHORA</h2>
        {top_section}

        <!-- Ofertas mid -->
        <h2 style="color:#f59e0b; font-size:16px; margin:24px 0 12px 0;">🟡 VALE LA PENA MIRAR</h2>
        {mid_section}

        <!-- Ofertas extra -->
        <h2 style="color:#64748b; font-size:16px; margin:24px 0 8px 0;">⚪ POSIBLE INGRESO EXTRA — EVALUÁ VOS</h2>
        <p style="color:#475569; font-size:12px; margin:0 0 12px 0;">
          El agente los muestra pero no los recomienda activamente. Mirá los positivos y negativos y decidís vos.
        </p>
        {extra_section}

        <!-- Footer -->
        <div style="margin-top:32px; text-align:center; color:#334155; font-size:12px;">
          <p>Agente automático de búsqueda laboral · Nahuel Ramon · Córdoba, Argentina</p>
          <p>Fuentes: Remote OK · We Work Remotely · Remotive · Working Nomads · Jobspresso</p>
        </div>

      </div>
    </body>
    </html>
    """


def send_email(jobs: list):
    gmail_user = os.environ["GMAIL_USER"]
    gmail_pass = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("RECIPIENT_EMAIL", gmail_user)

    today = datetime.now().strftime("%d %b %Y")
    top_count = len([j for j in jobs if j["score"] >= 7.5])
    total = len(jobs)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎯 {top_count} top · {total} total · Job Hunt {today}"
    msg["From"] = gmail_user
    msg["To"] = recipient

    html_body = build_email_html(jobs)
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, recipient, msg.as_string())
        print(f"Email enviado a {recipient}")


if __name__ == "__main__":
    with open("jobs_output.json") as f:
        jobs = json.load(f)
    send_email(jobs)
