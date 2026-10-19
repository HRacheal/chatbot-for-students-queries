from flask import request, jsonify
import os

class CORSMiddleware:
    """Middleware for handling CORS"""
    
    def __init__(self, app):
        self.app = app
        self.init_app(app)
    
    def init_app(self, app):
        """Initialize CORS middleware"""
        app.after_request(self.after_request)
    
    def after_request(self, response):
        """Add CORS headers to response"""
        # Get origins from environment variable
        cors_origins_env = os.environ.get('CORS_ORIGINS', '')
        
        # Determine allowed origins
        if cors_origins_env:
            # If specific origins are configured, use them
            allowed_origins = [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]
        else:
            # Fallback to wildcard for development or if not configured
            allowed_origins = ['*']
        
        # Check if the request origin is allowed
        origin = request.headers.get('Origin')
        
        if '*' in allowed_origins or not origin:
            # Allow all origins or no origin header present
            cors_origin = '*' if not origin else origin
        else:
            # Check if origin matches any allowed pattern
            cors_origin = None
            for allowed in allowed_origins:
                if allowed.endswith('.vercel.app') and origin and origin.endswith('.vercel.app'):
                    cors_origin = origin
                    break
                elif allowed == origin:
                    cors_origin = origin
                    break
            
            # If no match found, don't add CORS headers (will be blocked)
            if not cors_origin:
                return response
        
        # Add CORS headers
        response.headers.add('Access-Control-Allow-Origin', cors_origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        
        # Handle preflight OPTIONS request
        if request.method == 'OPTIONS':
            response.headers.add('Access-Control-Max-Age', '3600')
            
        return response

class EnvironmentMiddleware:
    """Middleware for setting up environment variables"""
    
    def __init__(self, app):
        self.app = app
        self.setup_environment()
    
    def setup_environment(self):
        """Set up LangChain environment variables"""
        from config.config import Config
        
        # Set environment variables for LangChain
        os.environ["LANGCHAIN_TRACING_V2"] = Config.LANGCHAIN_TRACING_V2
        os.environ["LANGCHAIN_PROJECT"] = Config.LANGCHAIN_PROJECT
        os.environ["LANGCHAIN_ENDPOINT"] = Config.LANGCHAIN_ENDPOINT
        
        if Config.LANGSMITH_API_KEY:
            os.environ["LANGSMITH_API_KEY"] = Config.LANGSMITH_API_KEY

        # Set environment variables for Pinecone
        if Config.PINECONE_API_KEY:
            os.environ["PINECONE_API_KEY"] = Config.PINECONE_API_KEY

class SessionCleanupMiddleware:
    """Middleware for cleaning up expired sessions"""
    
    def __init__(self, app, chat_service):
        self.app = app
        self.chat_service = chat_service
        self.init_app(app)
    
    def init_app(self, app):
        """Initialize session cleanup middleware"""
        app.before_request(self.before_request)
    
    def before_request(self):
        """Run cleanup before each request"""
        if hasattr(self.chat_service, 'cleanup_expired_sessions'):
            self.chat_service.cleanup_expired_sessions()

class ErrorHandlingMiddleware:
    """Middleware for global error handling"""
    
    def __init__(self, app):
        self.app = app
        self.init_app(app)
    
    def init_app(self, app):
        """Initialize error handling middleware"""
        app.errorhandler(404)(self.handle_404)
        app.errorhandler(500)(self.handle_500)
        app.errorhandler(Exception)(self.handle_exception)
    
    def handle_404(self, error):
        """Handle 404 errors"""
        return jsonify({'error': 'Endpoint not found'}), 404
    
    def handle_500(self, error):
        """Handle 500 errors"""
        return jsonify({'error': 'Internal server error'}), 500
    
    def handle_exception(self, error):
        """Handle general exceptions"""
        print(f"Unhandled exception: {str(error)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500
