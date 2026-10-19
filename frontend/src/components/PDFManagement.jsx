import React, { useState, useEffect } from 'react';
import { RiUpload2Line, RiDeleteBinLine, RiRefreshLine, RiFileTextLine, RiEyeLine } from 'react-icons/ri';
import { fetchPDFs, deletePDF, rebuildEmbeddings } from '../lib/api';
import PDFPreview from './PDFPreview';

function PDFManagement() {
  const [pdfs, setPdfs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [showPreview, setShowPreview] = useState(false);

  // Fetch PDFs on component mount
  useEffect(() => {
    loadPDFs();
  }, []);

  const loadPDFs = async () => {
    setLoading(true);
    try {
      const response = await fetchPDFs();
      setPdfs(response.pdfs || []);
    } catch (error) {
      console.error('Failed to load PDFs:', error);
      // Check if this is an auth error
      if (error.response && error.response.status === 401) {
        // Handle authentication error - possibly redirect to login
        alert('Authentication error. Please log in again.');
        // Clear the token and redirect to admin login
        localStorage.removeItem('adminToken');
        window.location.href = '/admin';
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (file.type !== 'application/pdf') {
      alert('Only PDF files are allowed!');
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const token = localStorage.getItem('adminToken');
      const response = await fetch('/api/pdfs/upload', {
        method: 'POST',
        body: formData,
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Upload failed');
      }

      alert('PDF uploaded successfully!');
      loadPDFs(); // Refresh the list
    } catch (error) {
      alert('Failed to upload PDF: ' + error.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (publicId) => {
    if (!confirm('Are you sure you want to delete this PDF?')) {
      return;
    }
    
    try {
      await deletePDF(publicId);
      alert('PDF deleted successfully');
      loadPDFs(); // Refresh the list
    } catch (error) {
      alert('Failed to delete PDF');
    }
  };

  const handleRebuildEmbeddings = async () => {
    setRebuilding(true);
    try {
      await rebuildEmbeddings();
      alert('Embeddings rebuilt successfully');
    } catch (error) {
      alert('Failed to rebuild embeddings');
    } finally {
      setRebuilding(false);
    }
  };

  const openPreview = (url) => {
    setPreviewUrl(url);
    setShowPreview(true);
  };

  return (
    <div className="text-white">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">PDF Management</h2>
        
        {/* Upload and Rebuild section */}
        <div className="flex gap-4">
          <div className="relative">
            <input
              type="file"
              accept=".pdf"
              onChange={handleUpload}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              disabled={uploading}
            />
            <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded flex items-center">
              <RiUpload2Line className="mr-2" />
              {uploading ? "Uploading..." : "Upload PDF"}
            </button>
          </div>

          <button
            onClick={handleRebuildEmbeddings}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded flex items-center"
            disabled={rebuilding}
          >
            <RiRefreshLine className="mr-2" />
            {rebuilding ? "Rebuilding..." : "Rebuild Embeddings"}
          </button>
        </div>
      </div>

      {/* PDFs list */}
      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      ) : pdfs.length === 0 ? (
        <div className="bg-gray-800 rounded-lg p-8 text-center">
          <RiFileTextLine className="mx-auto text-4xl mb-2 text-gray-400" />
          <p className="text-gray-400">No PDFs found. Upload a PDF to get started.</p>
        </div>
      ) : (
        <div className="bg-gray-800 rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-700">
            <thead className="bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Filename</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Created</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Size</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-gray-800 divide-y divide-gray-700">
              {pdfs.map((pdf) => (
                <tr key={pdf.public_id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <RiFileTextLine className="text-blue-400 mr-2" />
                      <span className="text-sm font-medium" title={pdf.public_id}>
                        {/* Extract and display the best possible name */}
                        {pdf.filename || pdf.public_id.split('/').pop()}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {new Date(pdf.created_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {formatFileSize(pdf.size)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <div className="flex space-x-2">
                      <button
                        onClick={() => openPreview(pdf.url)}
                        className="bg-blue-600 hover:bg-blue-700 px-2 py-1 rounded flex items-center"
                      >
                        <RiEyeLine className="mr-1" /> View
                      </button>
                      <button
                        onClick={() => handleDelete(pdf.public_id)}
                        className="bg-red-600 hover:bg-red-700 px-2 py-1 rounded flex items-center"
                      >
                        <RiDeleteBinLine className="mr-1" /> Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* PDF Preview Modal */}
      {showPreview && (
        <PDFPreview url={previewUrl} onClose={() => setShowPreview(false)} />
      )}
    </div>
  );
}

// Helper function to format file size
function formatFileSize(bytes) {
  if (!bytes) return 'Unknown';
  const kb = bytes / 1024;
  return kb < 1024 ? `${kb.toFixed(2)} KB` : `${(kb / 1024).toFixed(2)} MB`;
}

export default PDFManagement;
