from flask import Blueprint

from controllers.pdf_controller import PDFController
from utils.auth import admin_required


def create_pdf_routes(storage, knowledge_base):
    """Create PDF routes. Every route requires an admin token."""
    pdf_bp = Blueprint('pdf_bp', __name__, url_prefix='/api/pdfs')
    pdf_controller = PDFController(storage, knowledge_base)

    @pdf_bp.route('/', methods=['GET'])
    @admin_required
    def list_pdfs():
        """List all knowledge-base PDFs"""
        return pdf_controller.list_pdfs()

    @pdf_bp.route('/upload', methods=['POST'])
    @admin_required
    def upload_pdf():
        """Upload a PDF file"""
        return pdf_controller.upload_pdf()

    @pdf_bp.route('/rebuild-embeddings', methods=['POST'])
    @admin_required
    def rebuild_embeddings():
        """Rebuild the knowledge-base index from stored PDFs"""
        return pdf_controller.rebuild_embeddings()

    @pdf_bp.route('/<path:public_id>', methods=['DELETE'])
    @admin_required
    def delete_pdf(public_id):
        """Delete a PDF and its search entries"""
        return pdf_controller.delete_pdf(public_id)

    return pdf_bp
