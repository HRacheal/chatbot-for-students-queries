import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
import tempfile
import uuid
import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
import tempfile
import uuid
from config.config import Config

class CloudinaryService:
    """Service for managing PDFs in Cloudinary"""
    
    def __init__(self):
        """Initialize Cloudinary configuration"""
        cloudinary.config(
            cloud_name=Config.CLOUDINARY_CLOUD_NAME,
            api_key=Config.CLOUDINARY_API_KEY,
            api_secret=Config.CLOUDINARY_API_SECRET
        )
        print(f"Cloudinary initialized with cloud name: {Config.CLOUDINARY_CLOUD_NAME}")
        
    def upload_pdf(self, pdf_file):
        """Upload a PDF file to Cloudinary
        
        Args:
            pdf_file: The file object from request.files
            
        Returns:
            dict: The response from Cloudinary with file details
        """
        try:
            # Create a temporary file to handle the upload
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            pdf_file.save(temp_file.name)
            temp_file.close()
            
            # Get the original filename and sanitize it
            filename = pdf_file.filename
            
            # Make sure the filename ends with .pdf
            if not filename.lower().endswith('.pdf'):
                filename = filename + '.pdf'
                
            # Sanitize filename for use in public_id (remove spaces and special chars)
            import re
            sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '_', os.path.splitext(filename)[0])
            
            # Generate a unique ID that includes the original filename
            unique_id = f"{sanitized_name}_{str(uuid.uuid4())[:8]}"
            
            print(f"Uploading PDF to Cloudinary: {filename} with ID: {unique_id}")
            
            # Upload to Cloudinary - similar to the test script that worked
            # Adding access_mode=public to make the file publicly accessible
            result = cloudinary.uploader.upload(
                temp_file.name,
                resource_type="raw",
                public_id=unique_id,
                folder=Config.PDF_FOLDER,
                overwrite=True,
                access_mode="public"
            )
            
            # Add original filename to the result
            result['original_filename'] = filename
            
            # Clean up the temporary file
            os.unlink(temp_file.name)
            
            return result
        except Exception as e:
            if 'temp_file' in locals() and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            raise e
    
    def delete_pdf(self, public_id):
        """Delete a PDF from Cloudinary
        
        Args:
            public_id: The public_id of the PDF to delete
            
        Returns:
            dict: The response from Cloudinary
        """
        try:
            result = cloudinary.uploader.destroy(public_id, resource_type="raw")
            return result
        except Exception as e:
            raise e
    
    def list_pdfs(self):
        """List all PDFs stored in Cloudinary
        
        Returns:
            list: List of PDF files with their details
        """
        try:
            # Using the same approach as the test script
            folder = Config.PDF_FOLDER
            result = cloudinary.api.resources(
                resource_type="raw",
                type="upload",
                prefix=folder,
                max_results=500
            )
            
            # Return the resources directly
            return result.get("resources", [])
            
        except Exception as e:
            print(f"Error listing PDFs: {str(e)}")
            raise e
    
    def get_pdf_url(self, public_id):
        """Get the URL for a PDF
        
        Args:
            public_id: The public_id of the PDF
            
        Returns:
            str: The URL of the PDF
        """
        # Return the secure URL when possible
        url, options = cloudinary.utils.cloudinary_url(
            public_id,
            resource_type="raw"
        )
        return url
