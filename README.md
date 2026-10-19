# Student Query Resolution Chatbot

An intelligent AI-powered chatbot system designed to help resolve student queries efficiently using **Retrieval-Augmented Generation (RAG)** technology. The system features both user and admin interfaces, allowing for dynamic query handling, AI-powered responses, and comprehensive query management with cloud storage integration.

## 🚀 Key Features

### 🤖 AI-Powered Query Resolution
- **RAG (Retrieval-Augmented Generation)** for intelligent responses
- **Google AI (Gemini)** integration for natural language processing
- **LangChain** framework for advanced language processing
- **Pinecone** vector database for semantic search and embedding storage
- **PDF document processing** for knowledge base creation with Cloudinary integration

### 🔐 User Authentication System
- Secure user signup and login
- JWT-based authentication with session management
- Password encryption using Bcrypt
- Admin authentication with role-based access

### 💬 Advanced Query Management
- Real-time AI-powered query responses
- Automatic query storage and categorization
- Historical query search and analytics
- Unanswered query tracking for admin review

### 🎛️ Comprehensive Admin Dashboard
- Dedicated admin login system
- Query analytics and statistics
- Manage unanswered queries with bulk operations
- Add and update responses manually
- PDF management with Cloudinary integration
- One-click embedding rebuilding for knowledge base updates
- Email notification system for critical queries
- Chat history management

### 📧 Email Integration
- Automated email notifications
- Admin alerts for unanswered queries
- Test email functionality for system verification

### ☁️ Cloud Storage Integration
- Cloudinary PDF storage for document management
- PDF preview with Google Docs viewer
- Original filename preservation
- Public/private access management

## 🛠️ Technology Stack

### Backend (Flask)
- **Flask 2.3.3** - Modern Python web framework
- **Flask-CORS** - Cross-Origin Resource Sharing support
- **Gunicorn** - WSGI HTTP Server for production deployment
- **MongoDB with PyMongo** - NoSQL database for scalable data storage
- **Google AI (Gemini)** - Advanced language model integration
- **LangChain** - AI application framework
- **Pinecone** - Vector database for production-ready RAG systems
- **Cloudinary** - Cloud-based PDF storage and management
- **Flask-Mail** - Email service integration
- **JWT** - Secure token-based authentication
- **Flask-CORS** - Cross-origin resource sharing

### Frontend (React + Vite)
- **React 18.3.1** - Modern UI library
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **ShadCN/UI** - Modern component library
- **React Router** - Client-side routing
- **Axios** - HTTP client for API communication
- **Lucide React** - Beautiful icons

### AI & ML Stack
- **Google AI API** - Generative AI responses
- **LangChain Community** - Extended AI capabilities
- **Pinecone** - Managed vector database for production RAG deployments
- **TextBlob** - Text processing and analysis
- **PyPDF2** - PDF document processing
- **ReportLab** - PDF generation for Q&A documents
- **Cloudinary SDK** - Cloud storage API integration

## 📡 API Endpoints

### 🔐 Authentication
```http
POST /api/signup              # Register new user
POST /api/login               # User login  
POST /api/admin/login         # Admin authentication
```

### 💬 Chat & Query Management
```http
POST /api/query               # Submit query (AI-powered response)
GET  /api/chat-history        # Retrieve user chat history
POST /api/add-response        # Add manual response to query
```

### 🎛️ Admin Management
```http
GET  /api/admin/stats         # Get system statistics
GET  /api/admin/chat-history  # Get all chat history (admin)
GET  /api/admin/query-analytics # Get query analytics
GET  /api/unanswered-queries  # Get pending queries
DELETE /api/delete-query/<id> # Delete specific query
```

### 📄 PDF Management
```http
GET  /api/pdfs/               # List all PDFs
POST /api/pdfs/upload         # Upload a PDF file
DELETE /api/pdfs/<public_id>  # Delete a PDF
POST /api/pdfs/rebuild-embeddings # Rebuild embeddings from PDFs
```

### 🔍 System Endpoints
```http
GET  /health                  # Health check
GET  /debug/routes            # List all available routes
GET  /debug/email             # Test email service
POST /debug/send-test-email   # Send test email
```

## 🚀 Getting Started

### Prerequisites
- **Python 3.8+** (recommended 3.10+)
- **Node.js 16+** and npm
- **MongoDB Atlas** account or local MongoDB
- **Google AI API** key
- **Gmail account** for email services (with app password)
- **LangSmith account** (optional, for AI tracing)

### 🔧 Backend Setup

1. **Clone the repository:**
```bash
git clone https://github.com/Arnavkesari/chatbot-for-students-queries.git
cd chatbot-for-students-queries
```

2. **Navigate to backend directory:**
```bash
cd backend
```

3. **Create and activate virtual environment:**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux  
python3 -m venv venv
source venv/bin/activate
```

4. **Install dependencies:**
```bash
pip install -r requirements.txt
```

5. **Set up environment variables:**
Create `.env` file in the backend directory:

```env
# Database Configuration
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/chatbot?retryWrites=true&w=majority

# Google AI Configuration  
GOOGLE_API_KEY=your_google_ai_api_key

# LangChain Configuration (Optional - for AI tracing)
LANGSMITH_API_KEY=your_langsmith_api_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=Faculty Chatbot
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# Email Configuration (Gmail SMTP)
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_gmail_app_password

# Security
SECRET_KEY=your_secure_random_secret_key

# Flask Configuration
FLASK_ENV=development
PORT=5000

# Admin Credentials
ADMIN_EMAIL=
ADMIN_PASSWORD=
```

6. **Add PDF documents to resources folder:**
```bash
# Place your PDF documents in:
backend/resources/
```

7. **Start the backend server:**
```bash
python app.py
```

### 🎨 Frontend Setup

1. **Navigate to frontend directory:**
```bash
cd frontend
```

2. **Install dependencies:**
```bash
npm install
```

3. **Configure environment variables:**
```bash
# Create .env.local file
cp .env.local.example .env.local

# Edit .env.local to set the API base URL
# For development:
VITE_API_BASE_URL=http://localhost:5000

# For production (when deploying):
# VITE_API_BASE_URL=https://your-backend-url.onrender.com
```

4. **Start the development server:**
```bash
npm run dev
```

The frontend will run on `http://localhost:5173`

## 🏗️ Project Structure

```
chatbot-for-students-queries/
├── backend/
│   ├── app.py                    # Main Flask application
│   ├── requirements.txt          # Python dependencies
│   ├── config/
│   │   ├── config.py            # Configuration settings
│   │   └── database.py          # Database connection
│   ├── controllers/             # Business logic controllers
│   ├── middleware/              # Custom middleware
│   ├── models/                  # Database models
│   ├── routes/                  # API route definitions
│   ├── services/                # Business services
│   ├── utils/                   # Utility functions
│   └── resources/               # PDF documents for RAG
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── assets/              # Static assets
│   │   └── lib/                 # Utility libraries
│   ├── package.json             # Frontend dependencies
│   └── vite.config.js           # Vite configuration
└── RAG/                         # RAG implementation notes
```

## 🗃️ Database Schema

### Users Collection
```json
{
  "_id": "ObjectId",
  "username": "string",
  "email": "string", 
  "password": "bcrypt_hashed_string",
  "created_at": "datetime",
  "last_login": "datetime"
}
```

### Queries Collection
```json
{
  "_id": "ObjectId",
  "question": "string",
  "answer": "string", 
  "answered": "boolean",
  "user_id": "ObjectId",
  "timestamp": "datetime",
  "ai_generated": "boolean",
  "similarity_score": "float",
  "category": "string"
}
```

## 🔧 Configuration Details

### 🤖 AI Configuration
- **Google AI (Gemini)**: Powers intelligent response generation
- **LangChain**: Handles RAG pipeline and document processing
- **FAISS**: Vector database for semantic similarity search
- **LangSmith**: Optional AI tracing and monitoring

### 📧 Email Service
- **Gmail SMTP** integration for notifications
- **Flask-Mail** for email management
- Automated alerts for unanswered queries

### 🛡️ Security Features
- **Bcrypt password hashing** with salt rounds
- **JWT token authentication** with expiration
- **Admin role-based access control**
- **Environment variable protection**
- **CORS middleware** for secure API access
- **Session timeout management**

## 🎛️ Admin 

### Admin Capabilities:
- View system statistics and analytics
- Manage unanswered queries
- Add manual responses to queries  
- Delete inappropriate queries
- Monitor chat history across all users
- Receive email notifications for critical queries

## 🔍 Development

### Environment Modes
- **Development**: `FLASK_ENV=development` (Hot reloading enabled)
- **Production**: `FLASK_ENV=production` (Optimized for performance)
- **Testing**: `FLASK_ENV=testing` (Test configuration)

### Testing the System
1. **Health Check**: `GET http://localhost:5000/health`
2. **Email Service**: `GET http://localhost:5000/debug/email`  
3. **Send Test Email**: `POST http://localhost:5000/debug/send-test-email`
4. **List Routes**: `GET http://localhost:5000/debug/routes`

### API Testing with cURL
```bash
# Test user signup
curl -X POST http://localhost:5000/api/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"password123"}'

# Test query submission  
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"question":"What are the admission requirements?"}'
```

## 📚 RAG Implementation

The system uses **Retrieval-Augmented Generation** to provide accurate, context-aware responses:

1. **Document Processing**: PDF files in `resources/` are processed and chunked
2. **Vector Embeddings**: Text chunks are converted to vectors using Google AI
3. **Vector Storage**: FAISS stores embeddings for fast similarity search  
4. **Query Processing**: User questions are embedded and matched against knowledge base
5. **Response Generation**: Relevant context + user query sent to Google AI for response generation

### Adding New Documents
1. Upload PDF files through the admin dashboard
2. Rebuild embeddings using the dedicated button
3. System automatically processes and indexes new content

## 🚀 Deployment

### Backend Deployment (Render)

The backend is configured for deployment on Render.com:

1. **Render.yaml Configuration**: The project includes a `render.yaml` file with all the necessary configuration for deployment on Render.

2. **Environment Variables**: Make sure to set up all required environment variables in the Render Dashboard:
   - `MONGODB_URI`
   - `JWT_SECRET_KEY`
   - `GOOGLE_API_KEY`
   - All email configuration variables
   - Cloudinary credentials
   - Pinecone API key and environment

3. **CORS Configuration**: The backend is configured to accept requests from the frontend domain. Make sure to update the `CORS_ALLOW_ORIGIN` environment variable with your frontend URL.

### Frontend Deployment (Vercel/Netlify)

1. **Build the frontend**:
```bash
cd frontend
npm run build
```

2. **Environment Variables**: Set the `VITE_API_BASE_URL` to your deployed backend URL:
```
VITE_API_BASE_URL=https://your-backend-url.onrender.com
```

3. **Deploy**: Use Vercel, Netlify, or any static hosting service to deploy the `dist` folder.


## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality  
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Use ESLint configuration for JavaScript
- Add docstrings to all functions
- Write tests for new features
- Update README for significant changes

## 📄 License

This project is licensed under the **MIT License** - see the LICENSE file for details.

## 🆘 Support & Contact

- **Email**: sahayak.iiitdmj@gmail.com
- **GitHub Issues**: [Create an issue](https://github.com/Arnavkesari/chatbot-for-students-queries/issues)
- **Documentation**: See `/docs` folder for detailed documentation

---

**Built with ❤️ for educational institutions and student success**
