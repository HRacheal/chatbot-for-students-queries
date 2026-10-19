import React, { useState, useEffect } from 'react';
import { api } from "../lib/api";
import SpotlightCard from './ui/SpotlightCard';

function QueryAnalytics() {
  const [data, setData] = useState({ sentiment_analytics: [], trending_topics: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const token = localStorage.getItem('adminToken');
        const response = await api.get('/api/admin/query-analytics', {
          headers: { Authorization: `Bearer ${token}` }
        });
        setData(response.data);
      } catch (err) {
        console.error('Error fetching analytics:', err);
        setError('Failed to load analytics');
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  if (loading) return <div className="text-white text-center">Loading...</div>;
  if (error) return <div className="text-red-500 text-center">{error}</div>;

  return (
    <div className="p-6">
      <h2 className="text-2xl text-white mb-4">Query Analytics</h2>
      <SpotlightCard className="p-4 mb-4">
        <h3 className="text-white text-xl mb-2">Sentiment Analytics Over Time</h3>
        {data.sentiment_analytics.length > 0 ? (
          data.sentiment_analytics.map((item, index) => (
            <div key={index} className="text-white">
              <strong>{item.date}:</strong> Avg Sentiment: {item.avg_sentiment.toFixed(2)} (Count: {item.count})
            </div>
          ))
        ) : (
          <p className="text-gray-400">No sentiment data available.</p>
        )}
      </SpotlightCard>
      <SpotlightCard className="p-4">
        <h3 className="text-white text-xl mb-2">Trending Topics</h3>
        {data.trending_topics.length > 0 ? (
          data.trending_topics.map((topic, index) => (
            <div key={index} className="text-white">
              {topic[0]}: {topic[1]}
            </div>
          ))
        ) : (
          <p className="text-gray-400">No trending topics available.</p>
        )}
      </SpotlightCard>
    </div>
  );
}

export default QueryAnalytics;