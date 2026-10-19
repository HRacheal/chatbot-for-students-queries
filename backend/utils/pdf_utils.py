import os
import tempfile
import requests
from PyPDF2 import PdfReader
from langchain_text_splitters import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import cloudinary
import cloudinary.uploader
import cloudinary.utils
import cloudinary.api
from config.config import Config
from services.cloudinary_service import CloudinaryService

def get_embeddings_model():
    """Get embeddings model based on configured provider"""
    provider = Config.AI_PROVIDER.lower()
    
    # Only use HuggingFace embeddings for all providers
    print("Using HuggingFace embeddings (free) for vector storage")
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

def get_pdf_text(pdf_docs):
    """Extract text from PDF documents"""
    text = ""
    for pdf in pdf_docs:
        try:
            pdf_reader = PdfReader(pdf)
            # Skip if PDF has no pages
            if len(pdf_reader.pages) == 0:
                print(f"Skipping empty PDF: {pdf}")
                continue
            for page in pdf_reader.pages:
                text += page.extract_text()
        except Exception as e:
            print(f"Error reading PDF {pdf}: {str(e)}")
            continue
    return text

def get_text_chunks(text, source=None):
    """Split text into chunks for processing with metadata"""
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    
    # Add metadata if source is provided
    if source:
        # Create minimal metadata to stay under Pinecone's 40KB limit
        metadatas = []
        for i, _ in enumerate(chunks):
            metadatas.append({
                "source": source,
                "chunk_id": str(i)
            })
        return chunks, metadatas
    return chunks

def sanitize_chunks(chunks):
    """Make sure all chunks are valid for embedding"""
    import re
    
    sanitized_chunks = []
    for chunk in chunks:
        # Ensure the chunk is a string
        if not isinstance(chunk, str):
            chunk = str(chunk)
            
        # Remove characters that might cause encoding issues
        chunk = re.sub(r'[\uD800-\uDFFF]', '', chunk)  # Remove surrogate pairs
        chunk = re.sub(r'[^\x00-\x7F]+', ' ', chunk)   # Replace non-ASCII with space
        chunk = re.sub(r'\s+', ' ', chunk).strip()      # Clean up whitespace
        
        # Ensure the chunk isn't empty after cleaning
        if chunk:
            sanitized_chunks.append(chunk)
    
    return sanitized_chunks

def get_vector_store(text_chunks, metadatas=None):
    """Create Pinecone vector store from text chunks"""
    # Initialize Pinecone with v3 API
    pc = Pinecone(api_key=Config.PINECONE_API_KEY)
    
    # Sanitize chunks to prevent encoding issues
    try:
        clean_chunks = sanitize_chunks(text_chunks)
        print(f"Original chunks: {len(text_chunks)}, Clean chunks: {len(clean_chunks)}")
        
        # Check if we have any valid chunks after cleaning
        if not clean_chunks:
            print("WARNING: No valid chunks after sanitization, using default text")
            clean_chunks = ["This is a student query chatbot for academic assistance."]
            metadatas = [{"source": "default"}]
        else:
            # Always create fresh minimal metadata to avoid any size issues
            metadatas = []
            for i in range(len(clean_chunks)):
                metadatas.append({
                    "source": "cloudinary_pdf", 
                    "chunk_id": str(i)
                })
        
        # Check if index exists, if not create it
        index_name = Config.PINECONE_INDEX_NAME
        # Only HuggingFace embedding dimension is supported
        dimension = 384
        
        # Check if the index already exists
        indexes = [idx.name for idx in pc.list_indexes()]
        if index_name not in indexes:
            print(f"Creating Pinecone index: {index_name}")
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine"
            )
        
        # Create embeddings with retry logic
        embeddings = get_embeddings_model()
        
        # Create and return the vector store
        print(f"Creating vector store from {len(clean_chunks)} chunks")
        vectorstore = PineconeVectorStore.from_texts(
            texts=clean_chunks,
            embedding=embeddings,
            metadatas=metadatas if metadatas and len(metadatas) == len(clean_chunks) else None,
            index_name=index_name,
            namespace="course_materials"
        )
        
        return vectorstore
        
    except Exception as e:
        print(f"Error creating vector store: {str(e)}")
        # Create a minimal vector store with default content
        default_text = ["This is a student query chatbot for academic assistance."]
        embeddings = get_embeddings_model()
        
        vectorstore = PineconeVectorStore.from_texts(
            texts=default_text,
            embedding=embeddings,
            metadatas=[{"source": "default"}],
            index_name=Config.PINECONE_INDEX_NAME,
            namespace="course_materials"
        )
        
        return vectorstore

def create_embeddings():
    """Create embeddings from PDFs stored in Cloudinary"""
    # Get all PDFs from Cloudinary
    cloudinary_service = CloudinaryService()
    pdf_resources = cloudinary_service.list_pdfs()
    
    if not pdf_resources:
        print("No PDF resources found in Cloudinary")
        # Create a default embedding if no PDFs are available
        default_text = "This is a student query chatbot for academic assistance."
        chunks = get_text_chunks(default_text)
        
        return get_vector_store(chunks)
    
    # Get URLs directly from resources
    pdf_urls = []
    for resource in pdf_resources:
        # Use secure_url when available, otherwise use url
        url = resource.get('secure_url', resource.get('url'))
        if url:
            pdf_urls.append(url)
            print(f"Using URL for {resource.get('public_id')}: {url}")
    
    print(f"Processing {len(pdf_urls)} PDFs from Cloudinary")
    
    # Extract text from all PDFs
    from utils.cloudinary_utils import get_pdf_text_from_urls
    all_text = get_pdf_text_from_urls(pdf_urls)
    
    if not all_text.strip():
        print("No text extracted from PDFs, creating default vectorstore")
        default_text = "This is a student query chatbot for academic assistance."
        chunks = get_text_chunks(default_text)
        return get_vector_store(chunks)
    
    # Create text chunks without including text in metadata
    # Debug the text content first
    print(f"Total text length: {len(all_text)} characters")
    print(f"First 100 characters: {all_text[:100]}")
    print(f"Number of newlines: {all_text.count('\n')}")
    
    # Force chunking by length if needed
    chunks = []
    if len(all_text) > 5000:  # If text is very long
        # Manual chunking by fixed size
        chunk_size = 800  # Smaller chunks to be safe
        for i in range(0, len(all_text), chunk_size):
            chunk = all_text[i:i+chunk_size]
            if chunk.strip():  # Only add non-empty chunks
                chunks.append(chunk)
        print(f"Manually created {len(chunks)} chunks")
    else:
        # Try standard chunking for shorter texts
        text_splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=800,  # Smaller chunk size
            chunk_overlap=100,  # Less overlap
            length_function=len
        )
        chunks = text_splitter.split_text(all_text)
        print(f"Text splitter created {len(chunks)} chunks")
    
    # Ensure we have chunks
    if len(chunks) == 0:
        print("WARNING: No chunks created, falling back to default")
        chunks = [all_text[i:i+800] for i in range(0, len(all_text), 800)]
        print(f"Force created {len(chunks)} chunks")
    
    # Create minimal metadata with only essential information
    metadatas = []
    for i in range(len(chunks)):
        metadatas.append({
            "source": "cloudinary_pdf", 
            "chunk_id": str(i)
        })
    
    print(f"Created {len(chunks)} chunks with minimal metadata")

    # Use the unified get_vector_store logic, which already selects the correct embedding model
    return get_vector_store(chunks, metadatas)

def append_to_pdf(question, answer):
    """Append question and answer to extra.pdf in Cloudinary"""
    import tempfile
    import shutil
    import uuid
    import cloudinary
    import cloudinary.uploader
    from services.cloudinary_service import CloudinaryService
    from config.config import Config
    
    # Use Cloudinary service
    cloudinary_service = CloudinaryService()
    
    # Create a temporary directory for working with files
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, "extra.pdf")
    
    # Get existing extra PDF from Cloudinary if it exists
    extra_pdf_public_id = None
    try:
        # List all PDFs and find the one with 'extra' in the name
        pdfs = cloudinary_service.list_pdfs()
        for pdf in pdfs:
            if 'extra' in pdf.get('public_id', '').lower():
                extra_pdf_public_id = pdf.get('public_id')
                extra_pdf_url = pdf.get('url')
                break
        
        # Download the PDF if it exists
        if extra_pdf_public_id and extra_pdf_url:
            print(f"Found existing extra PDF in Cloudinary: {extra_pdf_public_id}")
            from utils.cloudinary_utils import download_pdf
            pdf_path = download_pdf(extra_pdf_url, temp_dir)
        else:
            print("No existing extra PDF found in Cloudinary. Creating a new one.")
    except Exception as e:
        print(f"Error fetching extra PDF from Cloudinary: {str(e)}")
    
    # Maximum Q&As per page and text wrapping settings
    MAX_QA_PER_PAGE = 5
    LINE_HEIGHT = 15
    PAGE_HEIGHT = 792  # Letter size height in points
    MARGIN_TOP = 50
    MARGIN_BOTTOM = 50
    MARGIN_LEFT = 50
    TEXT_WIDTH = 500
    
    def wrap_text(text, max_width=70):
        """Wrap text to fit within specified width"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            if len(current_line + " " + word) <= max_width:
                current_line += " " + word if current_line else word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        return lines
    
    try:
        # Read existing Q&As from PDF if it exists
        existing_qas = []
        if os.path.exists(pdf_path):
            try:
                existing_pdf = PdfReader(pdf_path)
                full_text = ""
                for page in existing_pdf.pages:
                    full_text += page.extract_text() + "\n"
                
                # Improved parsing logic
                if full_text.strip():
                    # Split by Q&A markers and clean up
                    import re
                    
                    # Find all Q&A sections using regex
                    qa_pattern = r'Q&A #\d+\s*Question:\s*(.*?)\s*Answer:\s*(.*?)(?=Q&A #\d+|$)'
                    matches = re.findall(qa_pattern, full_text, re.DOTALL | re.IGNORECASE)
                    
                    for match in matches:
                        question_text = match[0].strip()
                        answer_text = match[1].strip()
                        
                        # Clean up the extracted text
                        question_text = re.sub(r'\s+', ' ', question_text)
                        answer_text = re.sub(r'\s+', ' ', answer_text)
                        
                        # Remove any remaining Q&A markers from the text
                        question_text = re.sub(r'Q&A #\d+', '', question_text).strip()
                        answer_text = re.sub(r'Q&A #\d+', '', answer_text).strip()
                        
                        if question_text and answer_text:
                            existing_qas.append((question_text, answer_text))
                    
                    # If regex parsing fails, try manual parsing as fallback
                    if not existing_qas and "Question:" in full_text:
                        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                        
                        i = 0
                        while i < len(lines):
                            line = lines[i]
                            
                            # Look for Question: marker
                            if "Question:" in line:
                                # Extract question
                                question_text = line.replace("Question:", "").strip()
                                question_text = re.sub(r'Q&A #\d+', '', question_text).strip()
                                
                                # Continue reading question lines until we hit Answer:
                                i += 1
                                while i < len(lines) and "Answer:" not in lines[i]:
                                    if lines[i] and not lines[i].startswith("Q&A #"):
                                        question_text += " " + lines[i]
                                    i += 1
                                
                                # Extract answer
                                answer_text = ""
                                if i < len(lines) and "Answer:" in lines[i]:
                                    answer_text = lines[i].replace("Answer:", "").strip()
                                    answer_text = re.sub(r'Q&A #\d+', '', answer_text).strip()
                                    
                                    # Continue reading answer lines until next Q&A or end
                                    i += 1
                                    while i < len(lines) and not lines[i].startswith("Q&A #") and "Question:" not in lines[i]:
                                        if lines[i]:
                                            answer_text += " " + lines[i]
                                        i += 1
                                    i -= 1  # Step back one since we'll increment at end of loop
                                
                                # Clean up and add if both question and answer exist
                                question_text = re.sub(r'\s+', ' ', question_text).strip()
                                answer_text = re.sub(r'\s+', ' ', answer_text).strip()
                                
                                if question_text and answer_text:
                                    # Check for duplicates
                                    if not any(q == question_text for q, a in existing_qas):
                                        existing_qas.append((question_text, answer_text))
                            
                            i += 1
                            
            except Exception as e:
                print(f"Could not read existing PDF, starting fresh: {str(e)}")
                existing_qas = []
        
        # Check if the new Q&A already exists to avoid duplicates
        new_qa_exists = any(q.strip().lower() == question.strip().lower() for q, a in existing_qas)
        if not new_qa_exists:
            existing_qas.append((question, answer))
        else:
            print("Q&A already exists, skipping duplicate.")
        
        # Limit total Q&As to prevent PDF from becoming too large
        MAX_TOTAL_QAS = 50
        if len(existing_qas) > MAX_TOTAL_QAS:
            # Keep only the most recent Q&As
            existing_qas = existing_qas[-MAX_TOTAL_QAS:]
        
        # Create new PDF with all Q&As
        temp_path = pdf_path + ".tmp"
        c = canvas.Canvas(temp_path, pagesize=letter)
        
        current_y = PAGE_HEIGHT - MARGIN_TOP
        qa_count_on_page = 0
        
        for i, (q, a) in enumerate(existing_qas):
            # Check if we need a new page
            if qa_count_on_page >= MAX_QA_PER_PAGE:
                c.showPage()
                current_y = PAGE_HEIGHT - MARGIN_TOP
                qa_count_on_page = 0
            
            # Wrap question and answer text
            q_lines = wrap_text(q)
            a_lines = wrap_text(a)
            
            # Calculate space needed for this Q&A
            space_needed = (len(q_lines) + len(a_lines) + 4) * LINE_HEIGHT  # +4 for labels and spacing
            
            # Check if we have enough space on current page
            if current_y - space_needed < MARGIN_BOTTOM:
                c.showPage()
                current_y = PAGE_HEIGHT - MARGIN_TOP
                qa_count_on_page = 0
            
            # Draw Q&A number
            c.setFont("Helvetica-Bold", 12)
            c.drawString(MARGIN_LEFT, current_y, f"Q&A #{i + 1}")
            current_y -= LINE_HEIGHT + 5
            
            # Draw Question
            c.setFont("Helvetica-Bold", 11)
            c.drawString(MARGIN_LEFT, current_y, "Question:")
            current_y -= LINE_HEIGHT
            
            c.setFont("Helvetica", 10)
            for line in q_lines:
                c.drawString(MARGIN_LEFT + 10, current_y, line)
                current_y -= LINE_HEIGHT
            
            current_y -= 5  # Extra spacing
            
            # Draw Answer
            c.setFont("Helvetica-Bold", 11)
            c.drawString(MARGIN_LEFT, current_y, "Answer:")
            current_y -= LINE_HEIGHT
            
            c.setFont("Helvetica", 10)
            for line in a_lines:
                c.drawString(MARGIN_LEFT + 10, current_y, line)
                current_y -= LINE_HEIGHT
            
            current_y -= 20  # Space between Q&As
            qa_count_on_page += 1
        
        c.save()
        
        # Replace original file with new one
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        os.rename(temp_path, pdf_path)
        
        # Upload updated PDF to Cloudinary
        try:
            # If we already had an extra PDF, use the same public_id to replace it
            if extra_pdf_public_id:
                public_id = extra_pdf_public_id
            else:
                # Create a new public_id in the PDF folder
                public_id = f"{Config.PDF_FOLDER}/extra_{str(uuid.uuid4())[:8]}"
            
            print(f"Uploading updated PDF to Cloudinary with ID: {public_id}")
            result = cloudinary.uploader.upload(
                pdf_path,
                resource_type="raw",
                public_id=public_id,
                folder=Config.PDF_FOLDER,
                overwrite=True,
                access_mode="public"
            )
            
            print(f"Successfully uploaded updated PDF to Cloudinary: {result.get('public_id')}")
            
            # Skip automatic embedding creation as requested
            print("PDF uploaded to Cloudinary successfully. Embeddings will not be created automatically.")
            print("Use the 'Rebuild Embeddings' button in the admin dashboard to update embeddings.")
            
            # Clean up
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            
            print(f"this Successfully appended Q&A to PDF. Total Q&As: {len(existing_qas)}")
            return True
            
        except Exception as upload_error:
            print(f"Error uploading updated PDF to Cloudinary: {str(upload_error)}")
            return False
        
    except Exception as e:
        print(f"Error in append_to_pdf: {str(e)}")
        # Clean up temp files
        if 'temp_path' in locals():
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    print(f"Failed to remove temp file: {temp_path}")
        
        # Clean up temp directory
        if 'temp_dir' in locals():
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                print(f"Failed to remove temp directory: {temp_dir}")
        
        return False

# Update the update_vectorstore function
def update_vectorstore(pdf_path=None, question=None, answer=None):
    """Update the Pinecone vector store with new content
    
    This function is a wrapper to create or update embeddings in the vectorstore
    """
    try:
        # If pdf_path is provided, use it to create embeddings
        if pdf_path:
            print(f"Updating vectorstore with PDF: {pdf_path}")
            create_embeddings()
            return True
            
        # If question and answer are provided, create embeddings from the text
        elif question and answer:
            print("Updating vectorstore with new Q&A...")
            # Format the text as Q&A
            text = f"Question: {question}\nAnswer: {answer}"
            metadata = {"source": "admin_response", "question": question[:100]}
            
            # Use our function to create embeddings directly from text
            create_embeddings_from_text(text, metadata)
            return True
        else:
            print("Error: Either pdf_path or question and answer must be provided")
            return False
    except Exception as e:
        print(f"Error updating vectorstore: {str(e)}")
        return False
    
def embeddings_exist():
    """Check if embeddings already exist in Pinecone"""
    try:
        # Initialize Pinecone
        pc = Pinecone(api_key=Config.PINECONE_API_KEY)
        
        # Check if index exists
        index_name = Config.PINECONE_INDEX_NAME
        indexes = [idx.name for idx in pc.list_indexes()]
        
        if index_name not in indexes:
            print(f"Index {index_name} does not exist")
            return False
        
        # Get the index
        index = pc.Index(index_name)
        
        # Check if the index has vectors in the namespace
        stats = index.describe_index_stats()
        namespaces = stats.get("namespaces", {})
        course_materials = namespaces.get("course_materials", {})
        vector_count = course_materials.get("vector_count", 0)
        
        print(f"Found {vector_count} vectors in the course_materials namespace")
        
        # Return True if there are vectors in the namespace
        return vector_count > 0
        
    except Exception as e:
        print(f"Error checking if embeddings exist: {str(e)}")
        return False
