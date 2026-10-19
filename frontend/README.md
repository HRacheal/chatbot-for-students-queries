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
- PDF preview in the browser's built-in viewer (files are not sent to third-party viewers)
- Delete PDFs with confirmation
- Rebuild embeddings functionality

## 🛠️ Setup Instructions

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Configure environment**:
   Copy `.env.example` to `.env.local`. In development leave `VITE_API_BASE_URL`
   empty: Vite proxies `/api` to the backend on `http://127.0.0.1:5000`.
   In production set it to the backend URL, and add the frontend's origin to the
   backend's `CORS_ORIGINS`.

3. **Run development server**:
   ```bash
   npm run dev
   ```

4. **Build for production**:
   ```bash
   npm run build
   ```

5. **Run the tests and linter**:
   ```bash
   npm test        # Vitest: safe Markdown rendering / XSS tests
   npm run lint    # ESLint (pre-existing warnings are still being cleaned up)
   ```

## 📄 PDF Preview Features

The system includes a PDF preview component that:
- Uses the browser's built-in PDF viewer; documents are never sent to Google Docs or other third-party viewers
- Includes a loading indicator and an "open in new tab" option



## 🎨 UI Framework

Built with:
- **React 18.3.1**
- **Vite** for fast development and building
- **Tailwind CSS** for utility-first styling
- **React Router** for navigation
- **Axios** for API communication
