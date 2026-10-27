"""Envío del resumen por Gmail (SMTP, gratuito) con el PDF adjunto."""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path


class FaltanCredenciales(Exception):
    pass


def enviar(usuario: str, clave: str, destinatarios: list[str], asunto: str,
           texto: str, html: str, pdf: Path) -> None:
    if not (usuario and clave and destinatarios):
        raise FaltanCredenciales(
            "Faltan GMAIL_USUARIO, GMAIL_CLAVE_APLICACION o MAIL_DESTINATARIOS en el archivo .env"
        )
    msg = EmailMessage()
    msg["From"] = usuario
    msg["To"] = ", ".join(destinatarios)
    msg["Subject"] = asunto
    msg.set_content(texto)
    msg.add_alternative(html, subtype="html")
    msg.add_attachment(pdf.read_bytes(), maintype="application", subtype="pdf", filename=pdf.name)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=60) as smtp:
        smtp.login(usuario, clave.replace(" ", ""))
        smtp.send_message(msg)
