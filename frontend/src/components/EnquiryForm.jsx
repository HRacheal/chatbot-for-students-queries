import { useState } from "react";
import PropTypes from "prop-types";
import { getErrorMessage, submitEnquiry } from "../lib/api";
import { CONSENT_TEXT, ENQUIRY_DEPARTMENTS, USER_GROUPS } from "../lib/workflow";

// Asks for the minimum contact details, with explicit consent, and sends an unanswered
// question to the chosen department's dashboard. Who the person is (student, parent, ...)
// is optional. The confirmation is shown only after the backend has saved the enquiry.
function EnquiryForm({ question, queryId = null, suggestedDepartment = null, onDone = null }) {
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    department: suggestedDepartment || "",
    user_group: "",
    consent: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const update = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    if (!form.department) {
      setError("Please choose the department.");
      return;
    }
    if (!form.consent) {
      setError("Please confirm that USIU staff may use your contact details to reply.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const data = await submitEnquiry(
        { question, query_id: queryId, ...form, phone: form.phone.trim() || undefined,
          user_group: form.user_group || undefined },
        localStorage.getItem("userToken")
      );
      setResult(data);
      if (onDone) onDone(data);
    } catch (err) {
      setError(getErrorMessage(err, "Your enquiry could not be sent. Please try again."));
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    const { enquiry } = result;
    return (
      <div className="mt-3 rounded border border-green-700 bg-green-900/40 p-3 text-sm text-green-100" role="status">
        <p className="font-medium">{result.message}</p>
        <p className="mt-1">
          Reference: <span className="font-mono">{enquiry.reference}</span> · Status: {enquiry.status_label}
        </p>
        {result.tracking_key && (
          <p className="mt-1">
            Tracking key: <span className="font-mono break-all">{result.tracking_key}</span>
            <span className="block text-xs text-green-200">
              Save the reference and tracking key to check progress under &quot;Track enquiry&quot;. The key is shown only once.
            </span>
          </p>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="mt-3 space-y-2 rounded bg-gray-900 p-3 text-sm text-white" aria-label="Send to USIU staff">
      <p className="font-medium">Ask USIU staff to follow up</p>
      <p className="text-xs text-gray-400">Question: {question}</p>
      <label className="flex flex-col">
        Department
        <select className="mt-1 rounded bg-gray-700 p-1.5" value={form.department} onChange={update("department")} required>
          <option value="">Choose…</option>
          {Object.entries(ENQUIRY_DEPARTMENTS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </label>
      <label className="flex flex-col">
        I am a… (optional)
        <select className="mt-1 rounded bg-gray-700 p-1.5" value={form.user_group} onChange={update("user_group")}>
          <option value="">Prefer not to say</option>
          {Object.entries(USER_GROUPS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </label>
      <label className="flex flex-col">
        Name
        <input className="mt-1 rounded bg-gray-700 p-1.5" value={form.name} onChange={update("name")} required maxLength={100} autoComplete="name" />
      </label>
      <label className="flex flex-col">
        Email
        <input type="email" className="mt-1 rounded bg-gray-700 p-1.5" value={form.email} onChange={update("email")} required maxLength={254} autoComplete="email" />
      </label>
      <label className="flex flex-col">
        Phone (optional)
        <input type="tel" className="mt-1 rounded bg-gray-700 p-1.5" value={form.phone} onChange={update("phone")} maxLength={20} autoComplete="tel" />
      </label>
      <label className="flex items-start gap-2">
        <input type="checkbox" className="mt-1" checked={form.consent} onChange={update("consent")} />
        <span className="text-xs text-gray-300">{CONSENT_TEXT}</span>
      </label>
      {error && <p className="rounded bg-red-900/60 px-2 py-1 text-red-200" role="alert">{error}</p>}
      <button type="submit" disabled={submitting}
        className="rounded bg-blue-600 px-3 py-1.5 font-medium hover:bg-blue-500 disabled:opacity-50">
        {submitting ? "Sending…" : "Send enquiry"}
      </button>
    </form>
  );
}

EnquiryForm.propTypes = {
  question: PropTypes.string.isRequired,
  queryId: PropTypes.string,
  suggestedDepartment: PropTypes.string,
  onDone: PropTypes.func,
};

export default EnquiryForm;
