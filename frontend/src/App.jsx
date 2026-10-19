import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import ChatButton from "./components/ChatButton";
import ChatBox from "./components/ChatBox";
import Squares from "./components/ui/Squares";
import LoginAdmin from './components/LoginAdmin';
import Admin from './components/Admin';
import UserLogin from './components/UserLogin';
import UserSignUp from './components/UserSignUp';

// Auth checks
const isAdminAuthenticated = () => localStorage.getItem('adminToken') !== null;
const isAuthenticated = () => localStorage.getItem("userToken") !== null;

// Protected Route Component
const ProtectedRoute = ({ children, authCheck }) => {
  if (!authCheck()) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

function App() {
  const [isChatOpen, setIsChatOpen] = useState(false);

  useEffect(() => {
    const handleKeyPress = (event) => {
      // Toggle chat with Ctrl + /
      if (event.ctrlKey && event.key === '/') {
        event.preventDefault();
        setIsChatOpen(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);

  return (
    <Router>
      <Routes>
        {/* Main chat route */}
        <Route path="/" element={
          <div className="h-screen w-screen bg-cyan-950">
            <Squares
              speed={0.5}
              squareSize={40}
              direction="down" // up, down, left, right, diagonal
              borderColor="#fff"
              hoverFillColor="#222"
            />
            <div className="relative">
              {isChatOpen && <ChatBox onClose={() => setIsChatOpen(false)} />}
              {!isChatOpen && (
                <div onClick={() => setIsChatOpen(true)}>
                  <ChatButton />
                </div>
              )}
            </div>
          </div>
        } />
        
        {/* User routes */}
        <Route path="/login" element={<UserLogin />} />
        <Route path="/signup" element={<UserSignUp />} />
        
        {/* Admin routes */}
        <Route path="/admin" element={<LoginAdmin />} />
        <Route 
          path="/admin/dashboard" 
          element={
            <ProtectedRoute authCheck={isAdminAuthenticated}>
              <Admin />
            </ProtectedRoute>
          } 
        />
      </Routes>
    </Router>
  );
}

export default App;