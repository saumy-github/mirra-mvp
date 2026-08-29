"""Persist early-access applications and acknowledge them by email."""

import asyncio
import logging
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage

from ..config import get_settings
from ..core.security import new_id
from ..db import join_applications_col
from .models import JoinApplicationDocument

logger = logging.getLogger("mirra.backend.join")


def _confirmation_message(application: JoinApplicationDocument) -> EmailMessage:
    settings = get_settings()
    message = EmailMessage()
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = application.email
    message["Subject"] = "We received your Mirra early-access request"
    message.set_content(
        f"Hi {application.name},\n\n"
        "Thanks for your interest in testing Mirra. Your early-access request "
        f"for {application.company} is now with our team.\n\n"
        "We will review the details and follow up at this email address with the "
        "next steps.\n\n"
        "— Mirra"
    )
    return message


def _team_message(application: JoinApplicationDocument) -> EmailMessage:
    settings = get_settings()
    message = EmailMessage()
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = settings.join_notification_email
    message["Reply-To"] = application.email
    message["Subject"] = f"New Mirra early-access request — {application.company}"
    message.set_content(
        f"Application: {application.id}\n"
        f"Name: {application.name}\n"
        f"Email: {application.email}\n"
        f"Company: {application.company}\n"
        f"Website: {application.website or 'Not provided'}\n"
        f"Role: {application.role}\n"
        f"Monthly orders: {application.monthly_orders or 'Not provided'}\n\n"
        f"Goals:\n{application.goals}\n"
    )
    return message


def _deliver_confirmation(application: JoinApplicationDocument) -> bool:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_from_email:
        return False

    if settings.smtp_security == "ssl":
        smtp = smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=8,
            context=ssl.create_default_context(),
        )
    else:
        smtp = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=8)

    with smtp:
        if settings.smtp_security == "starttls":
            smtp.starttls(context=ssl.create_default_context())
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(_confirmation_message(application))

        if settings.join_notification_email:
            try:
                smtp.send_message(_team_message(application))
            except Exception:
                logger.exception("Could not deliver team notification for %s", application.id)

    return True


async def create_application(data: dict) -> tuple[str, bool]:
    application = JoinApplicationDocument(
        id=new_id("join"),
        name=data["name"],
        email=str(data["email"]).lower(),
        company=data["company"],
        website=data.get("website") or None,
        role=data["role"],
        monthly_orders=data.get("monthly_orders"),
        goals=data["goals"],
        created_at=datetime.now(timezone.utc),
    )
    await join_applications_col().insert_one(application.to_mongo())

    confirmation_sent = False
    try:
        confirmation_sent = await asyncio.wait_for(
            asyncio.to_thread(_deliver_confirmation, application),
            timeout=10,
        )
    except Exception:
        logger.exception("Could not deliver confirmation for %s", application.id)

    if confirmation_sent:
        try:
            await join_applications_col().update_one(
                {"_id": application.id},
                {"$set": {"confirmation_email_sent": True}},
            )
        except Exception:
            logger.exception("Could not record confirmation delivery for %s", application.id)

    return application.id, confirmation_sent
