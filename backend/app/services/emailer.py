"""Transactional delivery: Resend HTTPS API on Render Free; SMTP for local/non-free hosting."""
import base64
import smtplib
from email.message import EmailMessage
import httpx
from ..config import get_settings


def send_result_email(to_email: str, subject: str, body: str, certificate: bytes | None = None) -> str:
    settings = get_settings()
    if settings.resend_api_key:
        sender = settings.resend_from
        if not sender:
            raise ValueError("RESEND_FROM_REQUIRED")
        data = {"from": sender, "to": [to_email], "subject": subject, "text": body}
        if certificate:
            data["attachments"] = [{
                "filename": "constancia_matricula.pdf",
                "content": base64.b64encode(certificate).decode("ascii"),
            }]
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                "https://api.resend.com/emails",
                json=data,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            )
            response.raise_for_status()
        return "SENT"
    if not settings.smtp_host:
        return "SIMULATED"
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    if certificate:
        message.add_attachment(certificate, maintype="application", subtype="pdf", filename="constancia_matricula.pdf")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        if settings.smtp_user and settings.smtp_password:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)
    return "SENT"
