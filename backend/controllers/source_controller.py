from flask import current_app, jsonify, request

from services.sources import SourceError, SourceNotFound, serialize_source
from utils.pdf_utils import extract_pdf_text, is_pdf_bytes
from utils.validation import ValidationError, get_json_object

FORM_FIELDS = ("url", "title", "department", "content_type", "source_date", "retrieved_at", "notes", "text")


class SourceController:
    """Admin management of approved USIU-Africa sources (routes require ``admin_required``)."""

    def __init__(self, registry):
        self.registry = registry

    def _serialize(self, source, include_text=False):
        return serialize_source(source, include_text, current_app.config.get("SOURCE_STALE_DAYS", 365))

    def _request_data(self):
        """JSON body, or a multipart form with an optional PDF whose text becomes the source text."""
        if request.mimetype == "multipart/form-data":
            data = {k: request.form[k] for k in FORM_FIELDS if k in request.form}
            upload = request.files.get("file")
            if upload is not None and upload.filename:
                if not upload.filename.lower().endswith(".pdf"):
                    raise SourceError("Only PDF files can be uploaded")
                raw = upload.read()
                if not is_pdf_bytes(raw):
                    raise SourceError("The uploaded file is not a valid PDF")
                try:
                    text = extract_pdf_text(raw, max_pages=current_app.config.get("MAX_PDF_PAGES", 500))
                except Exception:
                    raise SourceError("Text could not be extracted from this PDF") from None
                if not text.strip():
                    raise SourceError("The PDF contains no extractable text (scanned PDFs are not supported yet)")
                data["text"] = text
                data.setdefault("content_type", "pdf")
            return data
        try:
            return get_json_object()
        except ValidationError as e:
            raise SourceError(str(e)) from None

    def list_sources(self):
        try:
            args = request.args
            sources = self.registry.list(args.get("status") or None, args.get("department") or None,
                                         category=args.get("category") or None,
                                         data_origin=args.get("origin") or None,
                                         origin_kind=args.get("kind") or None,
                                         search=args.get("search") or None,
                                         flagged=args.get("flagged") or None)
        except SourceError as e:
            return jsonify({"error": str(e)}), 400
        return jsonify({"sources": [self._serialize(s) for s in sources]}), 200

    def get_source(self, source_id):
        try:
            return jsonify({"source": self._serialize(self.registry.get(source_id), include_text=True)}), 200
        except SourceNotFound as e:
            return jsonify({"error": str(e)}), 404

    def create_source(self):
        try:
            source = self.registry.create(self._request_data())
        except SourceError as e:
            return jsonify({"error": str(e)}), 400
        return jsonify({"source": self._serialize(source)}), 201

    def update_source(self, source_id):
        try:
            source = self.registry.update(source_id, self._request_data())
        except SourceNotFound as e:
            return jsonify({"error": str(e)}), 404
        except SourceError as e:
            return jsonify({"error": str(e)}), 400
        return jsonify({"source": self._serialize(source)}), 200

    def set_status(self, source_id):
        try:
            data = self._request_data()
            source = self.registry.set_status(source_id, data.get("status"), note=data.get("note") or "")
        except SourceNotFound as e:
            return jsonify({"error": str(e)}), 404
        except SourceError as e:
            return jsonify({"error": str(e)}), 400
        return jsonify({"source": self._serialize(source)}), 200

    def rebuild_index(self):
        """Re-create the search index from approved sources (source records are not changed)."""
        try:
            report = self.registry.rebuild_index()
        except Exception as e:
            current_app.logger.error("Index rebuild failed (%s)", type(e).__name__)
            return jsonify({"error": "The index could not be rebuilt; the database may be unavailable"}), 503
        return jsonify({"report": report, "counts": self.registry.counts()}), 200
