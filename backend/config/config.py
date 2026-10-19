import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class"""
    SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
    MONGODB_URI = os.getenv("MONGO_URI")
    
    # AI Provider Selection: 'groq', 'google', or 'huggingface'
    AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")  # Default to Groq (free)
    
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    
    # Groq configuration (FREE - recommended)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")  # Fast and free
    GROQ_TIMEOUT = int(os.getenv("GROQ_TIMEOUT", "30"))
    
    # HuggingFace configuration (alternative free option)
    HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
    HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "mistralai/Mixtral-8x7B-Instruct-v0.1")

    # Pinecone configuration
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "student-chatbot")
    
    # Cloudinary configuration
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
    PDF_FOLDER = os.getenv("CLOUDINARY_PDF_FOLDER", "student_chatbot/pdfs")
    
    # Mail configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv("EMAIL_USER")
    # Clean the password to remove any non-breaking spaces or other Unicode issues
    _raw_password = os.getenv("EMAIL_PASS")
    MAIL_PASSWORD = _raw_password.replace('\xa0', ' ').replace('\u00a0', ' ') if _raw_password else None
    MAIL_DEFAULT_SENDER = os.getenv("EMAIL_USER")
    MAIL_MAX_EMAILS = None
    MAIL_SUPPRESS_SEND = False
    MAIL_ASCII_ATTACHMENTS = False
    
    # Ensure UTF-8 encoding for emails
    MAIL_USE_SSL = False
    MAIL_DEBUG = False
    
    # LangChain configuration
    LANGCHAIN_TRACING_V2 = "true"
    LANGCHAIN_PROJECT = "Faculty Chatbot"
    LANGCHAIN_ENDPOINT = "https://api.smith.langchain.com"
    
    # Session management
    SESSION_CLEANUP_INTERVAL = 3600  # Cleanup every hour
    SESSION_TIMEOUT = 7200  # Session timeout after 2 hours
    
    # Admin credentials
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
    
    # CORS Settings
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True

# Dictionary to easily access configurations
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
