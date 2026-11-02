import logging

from flask import current_app, jsonify, request

from services.guidance_service import (DISCLAIMER, GRADES, SUBJECTS, GuidanceError, extract_grades, read_upload,
                                       serialize_requirement)
from utils.validation import ValidationError, get_json_object, validate_object_id

logger = logging.getLogger(__name__)


class GuidanceController:
    """Degree guidance: results-slip extraction and recommendations (users); requirements (admins)."""

    def __init__(self, guidance_service):
        self.service = guidance_service

    def options(self):
        return jsonify({
            "subjects": list(SUBJECTS),
            "grades": list(GRADES),
            "disclaimer": DISCLAIMER,
            "accepted_files": [".pdf", ".txt"],
            "max_upload_mb": current_app.config["GUIDANCE_MAX_UPLOAD_MB"],
            "verified_programmes": len(self.service.list_requirements(verified_only=True)),
        }), 200

    def extract(self):
        """Read grades from an uploaded file. The file is processed in memory and discarded."""
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return jsonify({"error": "Choose a file to upload"}), 400
        max_bytes = current_app.config["GUIDANCE_MAX_UPLOAD_MB"] * 1024 * 1024
        data = upload.stream.read(max_bytes + 1)
        try:
            text = read_upload(upload.filename, data, max_bytes)
        except GuidanceError as e:
            return jsonify({"error": str(e)}), 400
        finally:
            del data
        result = extract_grades(text)
        del text
        logger.info("Results slip processed in memory (%d subjects recognised)", len(result["subjects"]))
        result["needs_confirmation"] = True
        result["message"] = ("Please check these subjects and grades against your results slip and correct "
                             "anything that is wrong before continuing. The file was not stored.")
        return jsonify(result), 200

    def recommend(self):
        try:
            data = get_json_object()
            result = self.service.recommend(data)
        except (ValidationError, GuidanceError) as e:
            return jsonify({"error": str(e)}), 400
        return jsonify(result), 200

    # --- administrators -------------------------------------------------------------------
    def admin_list(self):
        return jsonify({"requirements": [serialize_requirement(r) for r in self.service.list_requirements()]}), 200

    def admin_create(self):
        try:
            doc = self.service.create_requirement(get_json_object())
        except (ValidationError, GuidanceError) as e:
            return jsonify({"error": str(e)}), 400
        return jsonify({"requirement": serialize_requirement(doc)}), 201

    def admin_update(self, requirement_id):
        try:
            validate_object_id(requirement_id, "requirement id")
            doc = self.service.update_requirement(requirement_id, get_json_object())
        except (ValidationError, GuidanceError) as e:
            return jsonify({"error": str(e)}), 400
        if not doc:
            return jsonify({"error": "Requirement not found"}), 404
        return jsonify({"requirement": serialize_requirement(doc)}), 200

    def admin_delete(self, requirement_id):
        try:
            validate_object_id(requirement_id, "requirement id")
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        if not self.service.delete_requirement(requirement_id):
            return jsonify({"error": "Requirement not found"}), 404
        return jsonify({"message": "Requirement deleted"}), 200
