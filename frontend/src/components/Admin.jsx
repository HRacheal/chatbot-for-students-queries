import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { RiDashboardLine, RiLogoutBoxLine, RiMessage2Line, RiDeleteBin6Line, RiBarChart2Line, RiFileTextLine, RiRefreshLine } from 'react-icons/ri'
import QueryAnalytics from './QueryAnalytics';
import PDFManagement from './PDFManagement';
import { rebuildEmbeddings } from '../lib/api';
import { api } from "../lib/api";

function Admin() {
  const navigate = useNavigate();
  const [unansweredQueries, setUnansweredQueries] = useState([]);
  const [response, setResponse] = useState({});
  const [activeTab, setActiveTab] = useState('dashboard');
  const [adminChatHistory, setAdminChatHistory] = useState([]);
  const [rebuilding, setRebuilding] = useState(false);
  const [stats, setStats] = useState({
    total_users: 0,
    total_chats: 0,
    unanswered_queries: 0
  });

  // Fetch unanswered queries
  useEffect(() => {
    const fetchUnansweredQueries = async () => {
      try {
        const res = await api.get("/api/unanswered-queries");
        setUnansweredQueries(res.data.queries);
      } catch (error) {
        console.error("Error fetching unanswered queries:", error);
      }
    };
    fetchUnansweredQueries();
  }, []);

  // Fetch stats
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const token = localStorage.getItem('adminToken');
        const res = await api.get('/api/admin/stats', {
          headers: { Authorization: `Bearer ${token}` }
        });
        setStats(res.data);
      } catch (error) {
        console.error("Error fetching stats:", error);
      }
    };
    fetchStats();
  }, []);

  const fetchAdminChatHistory = async () => {
    try {
      const token = localStorage.getItem('adminToken');
      const res = await api.get('/api/admin/chat-history', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAdminChatHistory(res.data.history);
    } catch (error) {
      console.error("Error fetching chat history:", error);
    }
  };

  const handleResponseSubmit = async (id) => {
    try {
      await api.post("/api/add-response", {
        id,
        response: response[id],
      });
      setUnansweredQueries((prev) => prev.filter((query) => query._id !== id));
      alert("Response submitted successfully!");
    } catch (error) {
      console.error("Error submitting response:", error);
    }
  };

  const handleDeleteQuery = async (id) => {
    if (window.confirm('Are you sure you want to delete this query?')) {
      try {
        await api.delete(`/api/delete-query/${id}`);
        setUnansweredQueries((prev) => prev.filter((query) => query._id !== id));
      } catch (error) {
        console.error("Error deleting query:", error);
        alert("Failed to delete query");
      }
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('adminToken');
    navigate('/admin');
  };
  
  const handleRebuildEmbeddings = async () => {
    setRebuilding(true);
    try {
      await rebuildEmbeddings();
      alert('Embeddings rebuilt successfully');
    } catch (error) {
      console.error('Error rebuilding embeddings:', error);
      alert('Failed to rebuild embeddings');
    } finally {
      setRebuilding(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Sidebar */}
      <div className="fixed w-64 h-full bg-gray-800">
        <div className="flex flex-col h-full">
          <div className="flex items-center justify-center h-20 border-b border-gray-700">
            <h1 className="text-white text-2xl font-bold">Admin Dashboard</h1>
          </div>
          
          <nav className="flex-grow py-4">
            <a 
              href="#" 
              className={`flex items-center px-6 py-3 text-gray-300 hover:bg-gray-700 ${activeTab === 'dashboard' ? 'bg-gray-700' : ''}`}
              onClick={() => setActiveTab('dashboard')}
            >
              <RiDashboardLine className="mr-3" />
              Dashboard
            </a>
            <a 
              href="#" 
              className={`flex items-center px-6 py-3 text-gray-300 hover:bg-gray-700 ${activeTab === 'chat-history' ? 'bg-gray-700' : ''}`}
              onClick={() => {
                setActiveTab('chat-history');
                fetchAdminChatHistory();
              }}
            >
              <RiMessage2Line className="mr-3" />
              Chat History
            </a>
            <a 
              href="#" 
              className={`flex items-center px-6 py-3 text-gray-300 hover:bg-gray-700 ${activeTab === 'analytics' ? 'bg-gray-700' : ''}`}
              onClick={() => setActiveTab('analytics')}
            >
              <RiBarChart2Line className="mr-3" />
              Analytics
            </a>
            <a 
              href="#" 
              className={`flex items-center px-6 py-3 text-gray-300 hover:bg-gray-700 ${activeTab === 'pdfs' ? 'bg-gray-700' : ''}`}
              onClick={() => setActiveTab('pdfs')}
            >
              <RiFileTextLine className="mr-3" />
              PDF Management
            </a>
          </nav>

          <div className="p-4">
            <button
              onClick={handleLogout}
              className="flex items-center w-full px-4 py-2 text-gray-300 hover:bg-gray-700 rounded"
            >
              <RiLogoutBoxLine className="mr-3" />
              Logout
            </button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="ml-64 p-8">
            {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="bg-gray-800 rounded-lg p-6">
            {/* Header with title and rebuild button */}
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl text-white">Welcome, Admin</h2>
              
              {/* Rebuild Embeddings Button - moved to right side */}
              <button
                onClick={handleRebuildEmbeddings}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded flex items-center"
                disabled={rebuilding}
              >
                <RiRefreshLine className="mr-2" />
                {rebuilding ? "Rebuilding..." : "Rebuild Embeddings"}
              </button>
            </div>
            
            {/* Info cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="bg-gray-700 p-4 rounded-lg">
                <h3 className="text-white text-lg mb-2">Total Chats</h3>
                <p className="text-blue-400 text-2xl font-bold">{stats.total_chats}</p>
              </div>
              <div className="bg-gray-700 p-4 rounded-lg">
                <h3 className="text-white text-lg mb-2">Active Users</h3>
                <p className="text-green-400 text-2xl font-bold">{stats.total_users}</p>
              </div>
              <div className="bg-gray-700 p-4 rounded-lg">
                <h3 className="text-white text-lg mb-2">Total Unanswered Queries</h3>
                <p className="text-purple-400 text-2xl font-bold">{stats.unanswered_queries}</p>
              </div>
            </div>
            
            {/* Embeddings info text */}
            <p className="text-gray-400 text-sm mt-4">
              Remember to rebuild embeddings after answering questions to update the AI knowledge base.
            </p>

            {/* Unanswered Queries Section */}
            <div className="mt-8 text-white">
              <h2 className="text-xl font-bold mb-4">Unanswered Queries</h2>
              {unansweredQueries.length > 0 ? (
                unansweredQueries.map(query => (
                  <div key={query._id} className="mb-4 bg-gray-800 p-4 rounded-lg">
                    <p className="mb-2">Q: {query.question}</p>
                    <button
                      onClick={() => handleDeleteQuery(query._id)}
                      className="text-red-500 hover:text-red-700 p-1"
                      title="Delete query"
                    >
                      <RiDeleteBin6Line size={20} />
                    </button>
                    <textarea
                      value={response[query._id] || ""}
                      onChange={(e) => setResponse(prev => ({...prev, [query._id]: e.target.value}))}
                      placeholder="Type your response"
                      className="w-full bg-gray-700 text-white rounded p-2 mb-2"
                    />
                    <button
                      onClick={() => handleResponseSubmit(query._id)}
                      className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                    >
                      Submit
                    </button>
                  </div>
                ))
              ) : (
                <div className="text-gray-400">No unanswered queries.</div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'chat-history' && (
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-2xl text-white mb-4">User Chat History</h2>
            <div className="space-y-4">
              {adminChatHistory.map((chat) => (
                <div key={chat._id} className="bg-gray-700 p-4 rounded-lg">
                  <div className="text-gray-400 text-sm mb-2">
                    {new Date(chat.timestamp).toLocaleString()} - {chat.username}
                  </div>
                  <div className="space-y-2">
                    <div>
                      <span className="text-blue-400 font-medium">Question: </span>
                      <span className="text-white">{chat.question}</span>
                    </div>
                    <div>
                      <span className="text-green-400 font-medium">Answer: </span>
                      <span 
                        className="text-white chat-response"
                        dangerouslySetInnerHTML={{ __html: chat.answer }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'analytics' && (
          <QueryAnalytics />
        )}
        
        {activeTab === 'pdfs' && (
          <div className="bg-gray-800 rounded-lg p-6">
            <PDFManagement />
          </div>
        )}
      </div>
    </div>
  )
}

export default Admin;