import React, { useState } from 'react';
import { RiCloseLine, RiDownloadLine, RiLoader4Line } from 'react-icons/ri';

// Previews a knowledge-base PDF in the browser's built-in viewer.
// Documents are not sent to third-party viewers (e.g. Google Docs) because
// the URLs grant access to private files.
function PDFPreview({ url, onClose }) {
  const [loading, setLoading] = useState(true);

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleOpen = () => {
    window.open(url, '_blank', 'noopener,noreferrer');
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
              onClick={handleOpen}
              className="text-gray-400 hover:text-white focus:outline-none mr-3"
              title="Open PDF in new tab"
            >
              <RiDownloadLine size={20} />
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white focus:outline-none"
              title="Close"
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
          <iframe
            src={url}
            className="w-full h-full rounded border-0"
            title="PDF Preview"
            onLoad={() => setLoading(false)}
          />
          <p className="absolute bottom-2 left-0 right-0 text-center text-xs text-gray-400">
            If the preview stays blank, use the &quot;open in new tab&quot; button above.
          </p>
        </div>
      </div>
    </div>
  );
}

export default PDFPreview;
