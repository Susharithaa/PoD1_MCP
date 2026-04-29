"""
Email sender using Gmail SMTP (TLS port 587).
Requires SMTP_USER and SMTP_PASSWORD (Gmail App Password) in .env
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings


def send_otp_email(to_email: str, otp_code: str, full_name: str = "") -> None:
    """Raises on failure so the caller can handle it."""
    placeholder_values = {
        "",
        "you@gmail.com",
        "your-16-char-app-password",
        "your-16-char-gmail-app-password",
    }
    if settings.smtp_user in placeholder_values or settings.smtp_password in placeholder_values:
        print(f"[DEV OTP] Verification code for {to_email}: {otp_code}")
        return

    subject = "Your MCP Hub verification code"
    name_part = f"Hi {full_name}," if full_name else "Hi,"

    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:480px;margin:0 auto;padding:32px 24px">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:28px">
        <div style="width:32px;height:32px;background:#2563eb;border-radius:8px;
                    display:flex;align-items:center;justify-content:center">
          <span style="color:white;font-size:18px;font-weight:700;line-height:1">+</span>
        </div>
        <span style="font-weight:600;font-size:16px;color:#111827">MCP Hub</span>
      </div>

      <h2 style="font-size:20px;font-weight:600;color:#111827;margin:0 0 8px">
        Verification code
      </h2>
      <p style="color:#6b7280;font-size:14px;margin:0 0 24px">{name_part}</p>
      <p style="color:#374151;font-size:14px;margin:0 0 24px">
        Use the code below to complete your sign-in. It expires in <strong>10 minutes</strong>.
      </p>

      <div style="background:#f3f4f6;border-radius:12px;padding:24px;text-align:center;
                  margin-bottom:24px">
        <span style="font-size:36px;font-weight:700;letter-spacing:10px;
                     color:#111827;font-family:monospace">{otp_code}</span>
      </div>

      <p style="color:#9ca3af;font-size:12px;margin:0">
        If you did not attempt to sign in, you can safely ignore this email.
      </p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"MCP Hub <{settings.smtp_user}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_user, to_email, msg.as_string())
