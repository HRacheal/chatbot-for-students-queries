"""Logging setup with redaction of personal data.

Policy: never log the content of user questions, answers, passwords or tokens.
Log identifiers, sizes and outcomes instead. As a safety net, every log record
is passed through ``redact`` to mask email addresses and long numbers (phone
numbers, ID numbers) that might slip into a message.
"""

import logging
import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Sequences of 7+ digits, optionally separated by spaces, dots, dashes or brackets.
NUMBER_RE = re.compile(r"(?<![\w])\+?\d[\d\s().-]{5,}\d(?![\w])")
BEARER_RE = re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]+")


def redact(text):
    """Mask emails, long numbers and bearer tokens in ``text``."""
    if text is None:
        return ""
    text = str(text)
    text = BEARER_RE.sub("Bearer [token]", text)
    text = EMAIL_RE.sub("[email]", text)
    text = NUMBER_RE.sub("[number]", text)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record):
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - malformed log call
            message = str(record.msg)
        record.msg = redact(message)
        record.args = ()
        return True


def configure_logging(level="INFO"):
    """Configure root logging once, with redaction on every handler."""
    root = logging.getLogger()
    if not any(getattr(h, "_usiubot", False) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        handler.addFilter(RedactingFilter())
        handler._usiubot = True
        root.addHandler(handler)
    root.setLevel(level)
