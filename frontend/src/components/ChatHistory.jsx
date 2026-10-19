import React, { useState, useEffect } from 'react';
import { api } from "../lib/api";
import { format } from 'date-fns';
import SpotlightCard from './ui/SpotlightCard';

function ChatHistory() {
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchChatHistory = async () => {
      try {
        const token = localStorage.getItem('userToken');
        const response = await api.get('/api/chat-history', {
          headers: { Authorization: `Bearer ${token}` }
        });
        setChatHistory(response.data.history);
      } catch (err) {
        setError('Failed to load chat history');
        console.error('Error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchChatHistory();
  }, []);

  if (loading) return <div className="text-white text-center">Loading...</div>;
  if (error) return <div className="text-red-500 text-center">{error}</div>;

  return (
    <div className="p-6">
      <h2 className="text-2xl text-white mb-4">Chat History</h2>
      <div className="space-y-4">
        {chatHistory.map((chat) => (
          <SpotlightCard key={chat._id} className="p-4">
            <div className="text-gray-400 text-sm mb-2">
              {format(new Date(chat.timestamp), 'MMM d, yyyy h:mm a')}
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
          </SpotlightCard>
        ))}
        {chatHistory.length === 0 && (
          <div className="text-gray-400 text-center">No chat history found</div>
        )}
      </div>
    </div>
  );
}

export default ChatHistory;
