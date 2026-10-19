import React, { useState } from 'react';
import ReactDOM from 'react-dom/client';
import PDFPreview from './components/PDFPreview';
import './index.css';

function TestPreview() {
  const [showPreview, setShowPreview] = useState(false);
  // Test with a public PDF URL
  const testPdfUrl = 'https://res.cloudinary.com/example/raw/upload/test.pdf';

  return (
    <div className="bg-gray-900 min-h-screen p-8">
      <h1 className="text-white text-2xl mb-4">PDF Preview Test</h1>
      
      <button 
        onClick={() => setShowPreview(true)}
        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
      >
        Open PDF Preview
      </button>
      
      {showPreview && (
        <PDFPreview url={testPdfUrl} onClose={() => setShowPreview(false)} />
      )}
    </div>
  );
}

// You can uncomment this to test the component directly:
// ReactDOM.createRoot(document.getElementById('root')).render(
//   <React.StrictMode>
//     <TestPreview />
//   </React.StrictMode>
// );

export default TestPreview;
