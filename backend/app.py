"""
Student Chatbot Application
A professional Flask application for student query resolution using RAG and AI.
"""

import os
import sys
import time
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_mail import Mail
from werkzeug.middleware.proxy_fix import ProxyFix
import cloudinary

# Import configurations
from config.config import config
from config.database import db_instance

# Import services
from services.email_service import EmailService

# Import routes
from routes.admin_routes import create_admin_routes
from routes.auth_routes import create_auth_routes
from routes.chat_routes import create_chat_routes
from routes.admin_routes import create_legacy_admin_routes
from routes.pdf_routes import create_pdf_routes

# Import middleware
from middleware.middleware import (
    CORSMiddleware, 
    EnvironmentMiddleware, 
    ErrorHandlingMiddleware
)

# Import utilities
from utils.pdf_utils import create_embeddings, embeddings_exist

from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore

def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    # Get CORS origins from environment variable - supports multiple comma-separated origins
    cors_origins_env = os.environ.get('CORS_ORIGINS', '')
    
    if cors_origins_env:
        cors_origins = [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]
    else:
        # Fallback origins for development and common deployment platforms
        cors_origins = [
            'http://localhost:3000',
            'http://localhost:5173', 
            'http://127.0.0.1:3000',
            'http://127.0.0.1:5173',
            'https://*.vercel.app',
            'https://*.netlify.app'
        ]
    
    print(f"CORS Origins configured: {cors_origins}")
    
    cors = CORS(
        app, 
        resources={
            r"/api/*": {
                "origins": cors_origins,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
                "supports_credentials": True
            }
        },
        supports_credentials=True
    )
    mail = Mail(app)
    
    # Initialize Cloudinary
    cloudinary.config(
        cloud_name=app.config["CLOUDINARY_CLOUD_NAME"],
        api_key=app.config["CLOUDINARY_API_KEY"],
        api_secret=app.config["CLOUDINARY_API_SECRET"]
    )
    
    # Initialize middleware
    EnvironmentMiddleware(app)
    CORSMiddleware(app)
    ErrorHandlingMiddleware(app)
    
    # Initialize database
    if not db_instance.connect():
        raise Exception("Failed to connect to database")
    
    # Initialize email service
    email_service = EmailService()
    email_service.init_app(app)
    
    # Store email service in app config for global access
    app.config['EMAIL_SERVICE'] = email_service

     # Initialize Pinecone
    print("Initializing Pinecone...")
    try:
        # Using Pinecone v3 client API
        pc = Pinecone(api_key=app.config.get('PINECONE_API_KEY'))
        print("Pinecone initialized successfully!")
    except Exception as e:
        print(f"Error initializing Pinecone: {str(e)}")
        raise
    
    # Initialize Cloudinary
    print("Initializing Cloudinary...")
    try:
        from services.cloudinary_service import CloudinaryService
        cloudinary_service = CloudinaryService()
        print("Cloudinary initialized successfully!")
    except Exception as e:
        print(f"Error initializing Cloudinary: {str(e)}")
        raise
    
    # Create embeddings and vectorstore
    print("Initializing embeddings...")
    try:
        # Check if embeddings already exist in Pinecone
        if embeddings_exist():
            print("Embeddings already exist in Pinecone, skipping creation")
            from langchain_huggingface import HuggingFaceEmbeddings
            from langchain_pinecone import PineconeVectorStore
            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            vectorstore_global = PineconeVectorStore(
                index_name=app.config.get('PINECONE_INDEX_NAME'),
                embedding=embeddings,
                namespace="course_materials"
            )
        else:
            print("No embeddings found in Pinecone, creating new embeddings")
            vectorstore_global = create_embeddings()
        
        print("Embeddings initialized successfully!")
    except Exception as e:
        print(f"Error initializing embeddings: {str(e)}")
        # Create a fallback vectorstore with minimal default content
        print("Creating fallback vectorstore with default content")
        # Use a simple default text for embedding
        default_text = ["This is a student query chatbot for academic assistance."]
        try:
            # Try to create a minimal vectorstore
            from utils.pdf_utils import get_vector_store
            vectorstore_global = get_vector_store(default_text)
            print("Fallback vectorstore created successfully")
        except Exception as fallback_error:
            print(f"Error creating fallback vectorstore: {str(fallback_error)}")
            # If all else fails, set to None and handle in routes
            vectorstore_global = None
            print("WARNING: No vectorstore available, chat functionality will be limited")
    
    # Register blueprints (routes)
    app.register_blueprint(create_auth_routes(app))
    app.register_blueprint(create_chat_routes(vectorstore_global))
    app.register_blueprint(create_admin_routes(email_service))
    app.register_blueprint(create_legacy_admin_routes(email_service))  # For backward compatibility
    app.register_blueprint(create_pdf_routes())
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    @app.route('/api/health', methods=['GET'])  # Adding API prefix for Render health checks
    def health_check():
        return jsonify({
            "status": "healthy",
            "message": "Student Chatbot API is running", 
            "timestamp": datetime.now().isoformat(),
            "environment": os.environ.get("FLASK_ENV", "development")
        }), 200
    
    # Debug endpoint to list all routes
    @app.route('/debug/routes', methods=['GET'])
    def list_routes():
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                "endpoint": rule.endpoint,
                "methods": list(rule.methods),
                "url": str(rule)
            })
        return {"routes": routes}, 200
    
    # Debug endpoint to test CORS and environment
    @app.route('/debug/cors', methods=['GET', 'OPTIONS'])
    def test_cors():
        return jsonify({
            "status": "CORS test successful",
            "cors_origins": cors_origins,
            "request_origin": request.headers.get('Origin'),
            "method": request.method,
            "environment": os.environ.get("FLASK_ENV", "development")
        }), 200
    
    # Debug endpoint to test query endpoint without AI processing
    @app.route('/debug/query', methods=['POST', 'OPTIONS'])
    def test_query():
        if request.method == 'OPTIONS':
            return '', 200
        
        try:
            data = request.json
            question = data.get("question", "test question")
            
            return jsonify({
                "status": "Query endpoint test successful",
                "received_question": question,
                "mock_answer": f"This is a mock response to: {question}",
                "vectorstore_available": vectorstore_global is not None,
                "timestamp": datetime.now().isoformat()
            }), 200
        except Exception as e:
            return jsonify({
                "error": f"Query test failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }), 500
    

    
    # Debug endpoint to test email service
    @app.route('/debug/email', methods=['GET'])
    def test_email():
        email_service = app.config.get('EMAIL_SERVICE')
        if not email_service:
            return {"error": "Email service not found"}, 500
        
        if not email_service.mail:
            return {"error": "Mail instance not initialized"}, 500
        
        return {
            "status": "Email service is working",
            "mail_server": app.config.get('MAIL_SERVER'),
            "mail_username": app.config.get('MAIL_USERNAME'),
            "mail_configured": email_service.mail is not None
        }, 200
    
    # Test endpoint to send a test email
    @app.route('/debug/send-test-email', methods=['POST'])
    def send_test_email():
        email_service = app.config.get('EMAIL_SERVICE')
        if not email_service or not email_service.mail:
            return {"error": "Email service not available"}, 500
        
        try:
            # Send test email to the configured email address
            from flask_mail import Message
            msg = Message(
                subject="Test Email from Chatbot",
                sender=app.config.get('MAIL_USERNAME'),
                recipients=[app.config.get('MAIL_USERNAME')],  # Send to self
                body="This is a test email to verify email service is working."
            )
            email_service.mail.send(msg)
            return {"status": "Test email sent successfully"}, 200
        except Exception as e:
            return {"error": f"Failed to send test email: {str(e)}"}, 500
    
    # Root endpoint
    @app.route('/', methods=['GET'])
    def root():
        return {
            "message": "Welcome to Student Chatbot API",
            "version": "2.0.0",
            "endpoints": {
                "auth": "/api/signup, /api/login, /api/admin/login",
                "chat": "/api/query, /api/chat-history, /api/add-response",
                "admin": "/api/admin/stats, /api/admin/chat-history, /api/admin/query-analytics"
            }
        }, 200
    
    return app

def main():
    """Main function to run the application"""
    # Get environment
    env = os.getenv('FLASK_ENV', 'development')
    
    # Create app
    app = create_app(env)
    
    # Run app
    debug_mode = env == 'development'
    port = int(os.getenv('PORT', 5000))
    
    print(f"Starting Student Chatbot API in {env} mode...")
    print(f"Server running on http://localhost:{port}")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

# Create a global app object for Gunicorn to use
app = create_app(os.getenv('FLASK_ENV', 'production'))

if __name__ == "__main__":
    main()
