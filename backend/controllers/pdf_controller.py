from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename
from models.models import PDF
from services.cloudinary_service import CloudinaryService
import os

class PDFController:
    """Controller for PDF management"""
    
    def __init__(self):
        self.cloudinary_service = CloudinaryService()
    
    def allowed_file(self, filename):
        """Check if the file is a PDF"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'
    
    def upload_pdf(self):
        """Upload a PDF file to Cloudinary"""
        try:
            # Check if request contains a file
            if 'file' not in request.files:
                return jsonify({'error': 'No file part'}), 400
            
            file = request.files['file']
            
            # Check if file is selected
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            # Check if file is a PDF
            if not self.allowed_file(file.filename):
                return jsonify({'error': 'Only PDF files are allowed'}), 400
            
            # Upload file to Cloudinary
            upload_result = self.cloudinary_service.upload_pdf(file)
            
            # Create PDF object
            pdf = PDF(
                public_id=upload_result['public_id'],
                original_filename=upload_result['original_filename'],
                url=upload_result['url'],
                created_at=upload_result.get('created_at'),
                resource_type=upload_result.get('resource_type'),
                bytes=upload_result.get('bytes')
            )
            
            # Return success response
            return jsonify({
                'message': 'PDF uploaded successfully',
                'pdf': pdf.to_dict()
            }), 201
            
        except Exception as e:
            current_app.logger.error(f"Error uploading PDF: {str(e)}")
            return jsonify({'error': f'Error uploading PDF: {str(e)}'}), 500
    
    def list_pdfs(self):
        """List all PDFs stored in Cloudinary"""
        try:
            # Get all PDFs from Cloudinary
            pdf_resources = self.cloudinary_service.list_pdfs()
            
            # Print for debugging
            print(f"Found {len(pdf_resources)} PDF resources")
            for res in pdf_resources:
                print(f"PDF: {res.get('public_id')}, URL: {res.get('url')}")
            
            # Convert to PDF objects
            pdfs = [PDF.from_cloudinary_resource(resource).to_dict() for resource in pdf_resources]
            
            return jsonify({
                'pdfs': pdfs,
                'count': len(pdfs)
            }), 200
            
        except Exception as e:
            current_app.logger.error(f"Error listing PDFs: {str(e)}")
            return jsonify({'error': f'Error listing PDFs: {str(e)}'}), 500
    
    def delete_pdf(self, public_id):
        """Delete a PDF from Cloudinary"""
        try:
            # Delete PDF from Cloudinary
            result = self.cloudinary_service.delete_pdf(public_id)
            
            if result.get('result') == 'ok':
                return jsonify({'message': 'PDF deleted successfully'}), 200
            else:
                return jsonify({'error': 'Failed to delete PDF'}), 400
            
        except Exception as e:
            current_app.logger.error(f"Error deleting PDF: {str(e)}")
            return jsonify({'error': f'Error deleting PDF: {str(e)}'}), 500
    
    def rebuild_embeddings(self):
        """Rebuild embeddings from PDFs stored in Cloudinary"""
        try:
            # Import here to avoid circular imports
            from utils.pdf_utils import create_embeddings
            
            # Rebuild embeddings
            vectorstore = create_embeddings()
            
            return jsonify({'message': 'Embeddings rebuilt successfully'}), 200
            
        except Exception as e:
            current_app.logger.error(f"Error rebuilding embeddings: {str(e)}")
            return jsonify({'error': f'Error rebuilding embeddings: {str(e)}'}), 500
