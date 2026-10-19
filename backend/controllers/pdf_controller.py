import logging

from flask import current_app, jsonify, request

from models.models import PDF
from services.cloudinary_service import StorageNotConfiguredError
from services.knowledge_base import (
    KnowledgeBaseError,
    KnowledgeBaseUnavailable,
    RebuildInProgress,
    rebuild_from_storage,
)
from utils.pdf_utils import count_pdf_pages, is_pdf_bytes

logger = logging.getLogger(__name__)

STORAGE_UNAVAILABLE = {"error": "Document storage is not configured or unavailable"}


class PDFController:
    """Controller for knowledge-base PDF management (all routes are admin-only)."""

    def __init__(self, storage, knowledge_base):
        self.storage = storage
        self.knowledge_base = knowledge_base

    @staticmethod
    def allowed_file(filename):
        return bool(filename) and '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

    def upload_pdf(self):
        """Validate and upload a PDF to private storage."""
        file = request.files.get('file')
        if file is None:
            return jsonify({'error': 'No file part'}), 400
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400
        if not self.allowed_file(file.filename):
            return jsonify({'error': 'Only PDF files are allowed'}), 400

        data = file.stream.read()
        if not is_pdf_bytes(data):
            return jsonify({'error': 'The file content is not a valid PDF'}), 400
        try:
            if count_pdf_pages(data) == 0:
                return jsonify({'error': 'The PDF has no pages'}), 400
        except Exception:
            return jsonify({'error': 'The PDF could not be read; it may be damaged'}), 400
        file.stream.seek(0)

        try:
            upload_result = self.storage.upload_pdf(file)
        except StorageNotConfiguredError:
            return jsonify(STORAGE_UNAVAILABLE), 503
        except Exception as e:
            logger.error("PDF upload failed (%s)", type(e).__name__)
            return jsonify({'error': 'The PDF could not be uploaded. Please try again.'}), 502

        pdf = PDF.from_cloudinary_resource(upload_result, url=self.storage.file_url(upload_result))
        return jsonify({
            'message': 'PDF uploaded. Rebuild the knowledge base to make it searchable.',
            'pdf': pdf.to_dict(),
        }), 201

    def list_pdfs(self):
        """List knowledge-base PDFs with short-lived access URLs."""
        try:
            resources = self.storage.list_pdfs()
        except StorageNotConfiguredError:
            return jsonify(STORAGE_UNAVAILABLE), 503
        except Exception as e:
            logger.error("Listing PDFs failed (%s)", type(e).__name__)
            return jsonify({'error': 'Could not list documents. Please try again.'}), 502

        pdfs = [
            PDF.from_cloudinary_resource(r, url=self.storage.file_url(r)).to_dict() for r in resources
        ]
        return jsonify({'pdfs': pdfs, 'count': len(pdfs)}), 200

    def delete_pdf(self, public_id):
        """Delete a PDF from storage and remove its vectors from the index."""
        if not self.storage.is_in_managed_folder(public_id):
            return jsonify({'error': 'Invalid document id'}), 400
        try:
            result = self.storage.delete_pdf(public_id)
        except StorageNotConfiguredError:
            return jsonify(STORAGE_UNAVAILABLE), 503
        except Exception as e:
            logger.error("Deleting PDF failed (%s)", type(e).__name__)
            return jsonify({'error': 'The document could not be deleted. Please try again.'}), 502
        if result.get('result') != 'ok':
            return jsonify({'error': 'Document not found'}), 404

        response = {'message': 'PDF deleted successfully'}
        try:
            response['vectors_removed'] = self.knowledge_base.delete_document(public_id)
        except KnowledgeBaseUnavailable:
            response['warning'] = 'Knowledge base not configured; no search entries were removed'
        except Exception as e:
            logger.error("Removing vectors for deleted PDF failed (%s)", type(e).__name__)
            response['warning'] = (
                'The file was deleted, but its search entries could not be removed. '
                'Run a knowledge-base rebuild to clean them up.'
            )
        return jsonify(response), 200

    def rebuild_embeddings(self):
        """Re-index every stored PDF and remove obsolete vectors."""
        try:
            summary = rebuild_from_storage(
                self.knowledge_base, self.storage, current_app.config["MAX_PDF_PAGES"]
            )
        except StorageNotConfiguredError:
            return jsonify(STORAGE_UNAVAILABLE), 503
        except RebuildInProgress as e:
            return jsonify({'error': str(e)}), 409
        except KnowledgeBaseUnavailable as e:
            return jsonify({'error': str(e)}), 503
        except KnowledgeBaseError as e:
            return jsonify({'error': str(e)}), 422
        return jsonify({'message': 'Knowledge base rebuilt successfully', 'summary': summary}), 200
