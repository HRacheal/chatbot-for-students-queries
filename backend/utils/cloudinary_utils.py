import tempfile
import requests
import os
from urllib.parse import urlparse

def download_pdf(url, temp_dir):
    """Download a PDF from a URL to a temporary file"""
    print(f"Attempting to download PDF from URL: {url}")
    
    try:
        # Simple direct download - the PDFs are public now
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Get filename from URL
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename.endswith('.pdf'):
            filename = 'document.pdf'
            
        print(f"Downloading {filename}...")
        
        # Download with requests
        response = requests.get(url, stream=True, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf', dir=temp_dir)
        
        # Write the content to the file
        bytes_written = 0
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:  # filter out keep-alive new chunks
                temp_file.write(chunk)
                bytes_written += len(chunk)
        
        temp_file.close()
        print(f"PDF downloaded successfully to {temp_file.name} ({bytes_written} bytes)")
        
        # Verify file isn't empty
        if os.path.getsize(temp_file.name) == 0:
            raise Exception("Downloaded file is empty")
            
        return temp_file.name
        
    except Exception as e:
        print(f"Error downloading PDF: {str(e)}")
        raise

def clean_text(text):
    """Clean and normalize text to remove problematic characters"""
    import re
    import unicodedata
    
    # Handle common Unicode issues
    if text is None:
        return ""
    
    # Replace surrogate pairs and other problematic characters
    text = re.sub(r'[\uD800-\uDFFF]', '', text)  # Remove surrogate pairs
    
    # Normalize unicode (NFKD converts ligatures and special chars to ASCII where possible)
    text = unicodedata.normalize('NFKD', text)
    
    # Replace other potential problematic characters
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # Replace non-ASCII with space
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def get_pdf_text_from_urls(pdf_urls):
    """Extract text from PDF documents available at URLs"""
    from PyPDF2 import PdfReader
    
    text = ""
    success_count = 0
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        for i, url in enumerate(pdf_urls):
            try:
                print(f"\nProcessing PDF {i+1}/{len(pdf_urls)}: {url}")
                
                # Download the PDF
                pdf_path = download_pdf(url, temp_dir)
                
                # Check if file exists and has content
                if not os.path.exists(pdf_path):
                    print(f"ERROR: Downloaded file does not exist at {pdf_path}")
                    continue
                    
                file_size = os.path.getsize(pdf_path)
                print(f"Downloaded file size: {file_size} bytes")
                if file_size == 0:
                    print("ERROR: Downloaded PDF file is empty")
                    continue
                
                # Extract text
                with open(pdf_path, 'rb') as f:
                    print(f"Opening PDF file: {pdf_path}")
                    pdf_reader = PdfReader(f)
                    num_pages = len(pdf_reader.pages)
                    print(f"PDF has {num_pages} pages")
                    
                    for p, page in enumerate(pdf_reader.pages):
                        print(f"Extracting text from page {p+1}/{num_pages}")
                        try:
                            page_text = page.extract_text() or ""
                            # Clean the text to handle encoding issues
                            cleaned_text = clean_text(page_text)
                            text += cleaned_text + "\n"
                            print(f"Extracted {len(cleaned_text)} characters")
                        except Exception as page_error:
                            print(f"Error extracting text from page {p+1}: {str(page_error)}")
                
                success_count += 1
                print(f"Successfully processed PDF {i+1}/{len(pdf_urls)}")
                
            except Exception as e:
                print(f"ERROR processing PDF at {url}: {str(e)}")
    
    print(f"Successfully processed {success_count} out of {len(pdf_urls)} PDFs")
    print(f"Total text extracted: {len(text)} characters")
    
    # Final cleaning of the entire text
    clean_full_text = clean_text(text)
    print(f"Total text after cleaning: {len(clean_full_text)} characters")
    
    return clean_full_text
