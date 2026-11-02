"""Outgoing email over SMTP.

Every send returns True/False instead of raising, so callers can report a
clear notification status. Messages never include passwords, tokens or
uploaded documents.
"""

import logging
import smtplib
from email.message import EmailMessage

from models.models import User

logger = logging.getLogger(__name__)


class EmailService:
    """Service for handling email operations"""

    def __init__(self, settings):
        self.settings = settings
        self.user_model = User()

    def is_configured(self):
        s = self.settings
        return bool(s.get("MAIL_SERVER") and s.get("MAIL_USERNAME") and s.get("MAIL_PASSWORD"))

    def send(self, recipient, subject, body):
        """Send a plain-text email. Returns True on success."""
        if not self.is_configured():
            logger.warning("Email not sent: SMTP is not configured")
            return False
        s = self.settings
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = s.get("MAIL_DEFAULT_SENDER") or s["MAIL_USERNAME"]
        message["To"] = recipient
        message.set_content(body)
        try:
            smtp_class = smtplib.SMTP_SSL if s.get("MAIL_USE_SSL") else smtplib.SMTP
            with smtp_class(s["MAIL_SERVER"], s["MAIL_PORT"], timeout=s.get("MAIL_TIMEOUT", 15)) as server:
                if s.get("MAIL_USE_TLS") and not s.get("MAIL_USE_SSL"):
                    server.starttls()
                server.login(s["MAIL_USERNAME"], s["MAIL_PASSWORD"])
                server.send_message(message)
            logger.info("Email sent: %s", subject)
            return True
        except (smtplib.SMTPException, OSError) as e:
            logger.error("Email sending failed (%s)", type(e).__name__)
            return False

    def send_query_response_notification(self, user_id, question, response):
        """Tell a registered user that their question has been answered."""
        user = self.user_model.find_by_id(user_id)
        if not user or not user.get("email"):
            logger.info("Answer notification skipped: no email address on file")
            return False
        body = (
            "Hello,\n\n"
            f"Your question: \"{question}\"\n\n"
            f"Has been answered: \"{response}\"\n\n"
            "Thank you for your patience!\n\n"
            "- The Support Team\n"
        )
        return self.send(user["email"], "Your query has been answered", body)

    def send_welcome_email(self, user_email, username):
        """Send welcome email to new users"""
        body = (
            f"Hello {username},\n\n"
            "Welcome! Your USIUBOT account has been created.\n\n"
            "You can now:\n"
            "- Ask questions at any time\n"
            "- Access your chat history\n"
            "- Receive email notifications when staff answer your questions\n\n"
            "- The Support Team\n"
        )
        return self.send(user_email, "Welcome to USIUBOT", body)
