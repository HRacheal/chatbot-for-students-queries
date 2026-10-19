from flask import Blueprint
from controllers.pdf_controller import PDFController
from middleware.auth_middleware import admin_required

def create_pdf_routes():
    """Create PDF routes"""
    pdf_bp = Blueprint('pdf_bp', __name__, url_prefix='/api/pdfs')
    pdf_controller = PDFController()
    
    @pdf_bp.route('/', methods=['GET'])
    @admin_required
    def list_pdfs():
        """List all PDFs stored in Cloudinary"""
        return pdf_controller.list_pdfs()
    
    @pdf_bp.route('/upload', methods=['POST'])
    @admin_required
    def upload_pdf():
        """Upload a PDF file to Cloudinary"""
        return pdf_controller.upload_pdf()
    
    @pdf_bp.route('/<path:public_id>', methods=['DELETE'])
    @admin_required
    def delete_pdf(public_id):
        """Delete a PDF from Cloudinary"""
        return pdf_controller.delete_pdf(public_id)
    
    @pdf_bp.route('/rebuild-embeddings', methods=['POST'])
    @admin_required
    def rebuild_embeddings():
        """Rebuild embeddings from PDFs stored in Cloudinary"""
        return pdf_controller.rebuild_embeddings()
    
    return pdf_bp
