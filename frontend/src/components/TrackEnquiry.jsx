import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { getErrorMessage, getMyEnquiries, trackEnquiry } from "../lib/api";

function EnquiryStatus({ enquiry }) {
  return (
    <div className="rounded border border-gray-700 p-2 text-sm">
      <p className="font-medium">{enquiry.reference} · {enquiry.department_label}</p>
      <p className="text-gray-300">{enquiry.question}</p>
      <p className="mt-1 text-xs text-gray-400">
        Status: <span className="text-white">{enquiry.status_label}</span>
        {enquiry.created_at && <> · sent {enquiry.created_at.slice(0, 10)}</>}
        {enquiry.updated_at && <> · updated {enquiry.updated_at.slice(0, 10)}</>}
      </p>
      {enquiry.staff_response && (
        <p className="mt-1 rounded bg-gray-800 p-2 text-gray-200">Reply from USIU staff: {enquiry.staff_response}</p>
      )}
    </div>
  );
}

EnquiryStatus.propTypes = {
  enquiry: PropTypes.shape({
    reference: PropTypes.string,
    department_label: PropTypes.string,
    question: PropTypes.string,
    status_label: PropTypes.string,
    created_at: PropTypes.string,
    updated_at: PropTypes.string,
    staff_response: PropTypes.string,
  }).isRequired,
};

// Check the progress of an enquiry with its reference and tracking key, or (when
// logged in) see every enquiry sent from this account.
function TrackEnquiry({ onClose }) {
  const [reference, setReference] = useState("");
  const [trackingKey, setTrackingKey] = useState("");
  const [found, setFound] = useState(null);
  const [mine, setMine] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("userToken");
    if (token) getMyEnquiries(token).then((d) => setMine(d.enquiries || [])).catch(() => setMine([]));
  }, []);

  const handleTrack = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    setFound(null);
    try {
      setFound((await trackEnquiry(reference.trim(), trackingKey.trim())).enquiry);
    } catch (err) {
      setError(getErrorMessage(err, "No enquiry matches that reference and tracking key."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4 text-white">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-medium">Track an enquiry</h2>
        <button type="button" onClick={onClose} className="rounded bg-gray-700 px-3 py-1 text-sm hover:bg-gray-600">Back to chat</button>
      </div>
      <form onSubmit={handleTrack} className="space-y-2 rounded bg-gray-900 p-3 text-sm">
        <label className="flex flex-col">
          Reference
          <input className="mt-1 rounded bg-gray-700 p-1.5 font-mono" value={reference} onChange={(e) => setReference(e.target.value)} placeholder="ENQ-XXXXXXXX" required />
        </label>
        <label className="flex flex-col">
          Tracking key
          <input className="mt-1 rounded bg-gray-700 p-1.5 font-mono" value={trackingKey} onChange={(e) => setTrackingKey(e.target.value)} required />
        </label>
        <button type="submit" disabled={busy} className="rounded bg-blue-600 px-3 py-1.5 hover:bg-blue-500 disabled:opacity-50">
          {busy ? "Checking…" : "Check status"}
        </button>
      </form>
      {error && <p className="rounded bg-red-900/60 px-2 py-1 text-sm text-red-200" role="alert">{error}</p>}
      {found && <EnquiryStatus enquiry={found} />}
      {mine.length > 0 && (
        <div className="space-y-2">
          <p className="font-medium">Your enquiries</p>
          {mine.map((e) => <EnquiryStatus key={e.reference} enquiry={e} />)}
        </div>
      )}
    </div>
  );
}

TrackEnquiry.propTypes = {
  onClose: PropTypes.func.isRequired,
};

export { EnquiryStatus };
export default TrackEnquiry;
