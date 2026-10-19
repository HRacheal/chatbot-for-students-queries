import React, { useState, useEffect } from 'react';
import { RiCloseLine, RiDownloadLine, RiLoader4Line, RiRefreshLine } from 'react-icons/ri';

function PDFPreview({ url, onClose }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [viewerType, setViewerType] = useState('google'); // 'google' or 'iframe'
  
  // Generate viewer URLs
  const googleDocsUrl = `https://docs.google.com/viewer?url=${encodeURIComponent(url)}&embedded=true`;
  
  // Handle backdrop click to close
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };
  
  // Check if the URL is accessible
  useEffect(() => {
    const checkUrl = async () => {
      try {
        const response = await fetch(url, { method: 'HEAD' });
        if (!response.ok) {
          setError(true);
        }
      } catch (err) {
        console.error("Error checking PDF URL:", err);
        setError(true);
      }
    };
    
    checkUrl();
  }, [url]);
  
  // Reset loading state when switching viewer type
  useEffect(() => {
    setLoading(true);
  }, [viewerType]);
  
  // Handle direct download
  const handleDownload = () => {
    window.open(url, '_blank');
  };
  
  // Switch viewer type
  const toggleViewer = () => {
    setViewerType(viewerType === 'google' ? 'iframe' : 'google');
  };

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-80 flex justify-center items-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-gray-900 rounded-lg w-full max-w-4xl h-full max-h-[90vh] flex flex-col">
        <div className="flex justify-between items-center p-4 border-b border-gray-700">
          <h3 className="text-white text-lg font-medium">PDF Preview</h3>
          <div className="flex">
            <button 
              onClick={toggleViewer}
              className="text-gray-400 hover:text-white focus:outline-none mr-3"
              title={`Switch to ${viewerType === 'google' ? 'direct' : 'Google Docs'} viewer`}
            >
              <RiRefreshLine size={20} />
            </button>
            <button 
              onClick={handleDownload}
              className="text-gray-400 hover:text-white focus:outline-none mr-3"
              title="Open PDF in new tab"
            >
              <RiDownloadLine size={20} />
            </button>
            <button 
              onClick={onClose}
              className="text-gray-400 hover:text-white focus:outline-none"
            >
              <RiCloseLine size={24} />
            </button>
          </div>
        </div>
        
        <div className="flex-grow overflow-hidden p-1 bg-gray-800 relative">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-800 bg-opacity-70 z-10">
              <RiLoader4Line className="animate-spin text-white text-4xl" />
            </div>
          )}
          
          {error ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <p className="text-red-400 mb-4">Unable to load PDF preview</p>
              <button 
                onClick={handleDownload}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
              >
                Open PDF in new tab
              </button>
            </div>
          ) : viewerType === 'google' ? (
            <iframe
              src={googleDocsUrl}
              className="w-full h-full rounded border-0"
              title="PDF Preview (Google Docs)"
              frameBorder="0"
              onLoad={() => setLoading(false)}
              onError={() => setError(true)}
            />
          ) : (
            <iframe
              src={url}
              className="w-full h-full rounded border-0"
              title="PDF Preview (Direct)"
              frameBorder="0"
              onLoad={() => setLoading(false)}
              onError={() => setError(true)}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default PDFPreview;
