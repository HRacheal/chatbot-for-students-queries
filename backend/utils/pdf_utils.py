"""PDF helpers: content validation, text extraction and the admin Q&A document.

Embedding and vector-index logic lives in ``services/knowledge_base.py``.
"""

import io
import logging
import os
import re
import shutil
import tempfile
import unicodedata
import uuid

import cloudinary.uploader
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF-"
QA_DOCUMENT_PREFIX = "extra"


def is_pdf_bytes(data):
    """True if the data starts with the PDF file signature."""
    return isinstance(data, (bytes, bytearray)) and data[:1024].lstrip().startswith(PDF_MAGIC)


def normalize_text(text):
    """Normalise extracted text while keeping non-English characters.

    Removes control characters and lone surrogates, collapses runs of spaces
    and keeps paragraph breaks, which help the text splitter.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\ud800-\udfff]", "", text)
    text = "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch)[0] != "C")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def extract_pdf_text(data, max_pages=500):
    """Extract text from PDF bytes. Pages that fail to parse are skipped."""
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs are not supported")
    texts = []
    for page_number, page in enumerate(reader.pages):
        if page_number >= max_pages:
            logger.warning("PDF has more than %d pages; remaining pages skipped", max_pages)
            break
        try:
            texts.append(page.extract_text() or "")
        except Exception as e:  # pypdf raises many exception types for damaged pages
            logger.warning("Could not extract text from page %d (%s)", page_number + 1, type(e).__name__)
    return normalize_text("\n\n".join(texts))


def count_pdf_pages(data):
    """Parse the PDF structure and return its page count (raises if invalid)."""
    reader = PdfReader(io.BytesIO(data))
    return len(reader.pages)


# --- Admin Q&A document ------------------------------------------------------
# Answers written by administrators are collected in a generated "extra" PDF in
# the knowledge-base folder, and become searchable after the next rebuild.
# This will be replaced by a reviewed FAQ workflow in a later phase.

def _is_qa_document(resource):
    base = resource.get("public_id", "").split("/")[-1].lower()
    return base == QA_DOCUMENT_PREFIX or base.startswith(QA_DOCUMENT_PREFIX + "_")


def parse_qa_text(full_text):
    """Recover (question, answer) pairs from the text of the Q&A document."""
    qas = []
    pattern = r"Q&A #\d+\s*Question:\s*(.*?)\s*Answer:\s*(.*?)(?=Q&A #\d+|$)"
    for question, answer in re.findall(pattern, full_text or "", re.DOTALL | re.IGNORECASE):
        question = re.sub(r"\s+", " ", question).strip()
        answer = re.sub(r"\s+", " ", answer).strip()
        if question and answer:
            qas.append((question, answer))
    return qas


def _wrap_text(text, max_width=70):
    words = text.split()
    lines, current = [], ""
    for word in words:
        if len(current + " " + word) <= max_width:
            current = f"{current} {word}" if current else word
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_qa_pdf(qas, path):
    """Write the list of (question, answer) pairs to a PDF at ``path``."""
    line_height, page_height = 15, 792
    margin_top, margin_bottom, margin_left = 50, 50, 50

    c = canvas.Canvas(path, pagesize=letter)
    current_y = page_height - margin_top
    for i, (question, answer) in enumerate(qas):
        q_lines, a_lines = _wrap_text(question), _wrap_text(answer)
        space_needed = (len(q_lines) + len(a_lines) + 4) * line_height
        if current_y - space_needed < margin_bottom:
            c.showPage()
            current_y = page_height - margin_top

        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin_left, current_y, f"Q&A #{i + 1}")
        current_y -= line_height + 5
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin_left, current_y, "Question:")
        current_y -= line_height
        c.setFont("Helvetica", 10)
        for line in q_lines:
            c.drawString(margin_left + 10, current_y, line)
            current_y -= line_height
        current_y -= 5
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin_left, current_y, "Answer:")
        current_y -= line_height
        c.setFont("Helvetica", 10)
        for line in a_lines:
            c.drawString(margin_left + 10, current_y, line)
            current_y -= line_height
        current_y -= 20
    c.save()


def append_to_pdf(question, answer, storage):
    """Append an admin Q&A pair to the Q&A document in storage.

    Unlike the previous implementation, existing pairs are never discarded.
    Returns True on success, False otherwise (the caller decides how to report it).
    """
    if not storage.is_configured():
        logger.warning("Document storage not configured; Q&A not added to knowledge base")
        return False

    temp_dir = tempfile.mkdtemp()
    try:
        existing = next((r for r in storage.list_pdfs() if _is_qa_document(r)), None)
        qas = []
        if existing:
            qas = parse_qa_text(extract_pdf_text(storage.download_pdf_bytes(existing)))

        if any(q.strip().lower() == question.strip().lower() for q, _ in qas):
            logger.info("Q&A already present in knowledge-base document; skipping duplicate")
        else:
            qas.append((question, answer))

        pdf_path = os.path.join(temp_dir, "extra.pdf")
        render_qa_pdf(qas, pdf_path)

        if existing:
            options = {
                "public_id": existing["public_id"],
                "type": existing.get("type", storage.delivery_type),
            }
        else:
            options = {
                "public_id": f"{QA_DOCUMENT_PREFIX}_{uuid.uuid4().hex[:8]}",
                "folder": storage.folder,
                "type": storage.delivery_type,
            }
        if options["type"] == "upload":
            options["access_mode"] = "public"
        cloudinary.uploader.upload(pdf_path, resource_type="raw", overwrite=True, **options)
        logger.info("Q&A document updated (%d pairs); rebuild the knowledge base to index it", len(qas))
        return True
    except Exception as e:
        logger.error("Failed to update Q&A document (%s)", type(e).__name__)
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
