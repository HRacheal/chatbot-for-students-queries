# Student Query Chatbot - Frontend

This directory contains the React frontend for the Student Query Chatbot system. The frontend provides user and admin interfaces for interacting with the AI chatbot and managing the system.

## 🚀 Key Features

- **User Chat Interface**: Intuitive interface for submitting queries and viewing responses
- **Admin Dashboard**: Comprehensive dashboard for system management
- **PDF Management**: Upload, list, preview, and delete PDFs with Cloudinary integration
- **Embedding Management**: One-click rebuilding of embeddings
- **Responsive Design**: Mobile-friendly interface using Tailwind CSS

## 📂 Directory Structure

```
frontend/
├── public/               # Public assets
│   └── logo.svg          # Application logo
├── src/
│   ├── assets/           # Static assets (images, etc.)
│   ├── components/       # React components
│   │   ├── Admin.jsx     # Admin dashboard
│   │   ├── Chat.jsx      # Chat interface
│   │   ├── Login.jsx     # Login page
│   │   ├── PDFManagement.jsx # PDF management component
│   │   ├── PDFPreview.jsx    # PDF preview component
│   │   └── ...
│   ├── lib/              # Utility libraries
│   │   └── api.js        # API communication functions
│   ├── styles/           # Additional styles
│   ├── App.css           # Global CSS
│   ├── App.jsx           # Main application component
│   └── main.jsx          # Application entry point
├── index.html            # HTML template
├── vite.config.js        # Vite configuration
└── tailwind.config.js    # Tailwind CSS configuration
```

## 🌟 Key Components

### Chat Interface
- Real-time query submission and response
- Chat history display
- User authentication integration

### Admin Dashboard
- Statistics overview (users, chats, unanswered queries)
- Unanswered query management
- Chat history browsing
- Analytics visualization
- PDF management
- Embedding management

### PDF Management
- PDF upload with Cloudinary integration
- List and manage uploaded PDFs
- PDF preview with Google Docs viewer
- Delete PDFs with confirmation
- Rebuild embeddings functionality

## 🛠️ Setup Instructions

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Configure environment**:
   Create a `.env.local` file with:
   ```
   # Development
   VITE_API_BASE_URL=http://localhost:5000
   
   # Production (uncomment when deploying)
   # VITE_API_BASE_URL=https://your-backend-url.onrender.com
   ```

3. **Run development server**:
   ```bash
   npm run dev
   ```

4. **Build for production**:
   ```bash
   npm run build
   ```

## 📄 PDF Preview Features

The system includes a PDF preview component that:
- Uses Google Docs Viewer for reliable PDF rendering
- Provides fallback to direct iframe embedding
- Includes loading indicators and error handling
- Supports switching between viewer types



## 🎨 UI Framework

Built with:
- **React 18.3.1**
- **Vite** for fast development and building
- **Tailwind CSS** for utility-first styling
- **React Router** for navigation
- **Axios** for API communication
