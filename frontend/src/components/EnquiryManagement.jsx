import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import {
  addEnquiryNote,
  fetchEnquiries,
  fetchStaffDirectory,
  getEnquiry,
  getErrorMessage,
  updateEnquiryStatus,
} from "../lib/api";
import {
  ENQUIRY_DEPARTMENTS,
  ENQUIRY_STATUS_LABELS as STATUS_LABELS,
  ENQUIRY_STATUS_STYLES as STATUS_STYLES,
  OPEN_ENQUIRY_STATUSES,
} from "../lib/workflow";

const NEXT_STATUS = { new: "pending", pending: "in_progress", in_progress: "awaiting_response",
  awaiting_response: "resolved", resolved: "closed" };
const NOTIFICATION_TEXT = { sent: "email sent", failed: "email FAILED", not_configured: "email not configured",
  disabled: "email disabled" };
const formatDate = (value) => (value ? new Date(value).toLocaleString() : "");
const field = "mt-1 rounded-lg border border-slate-600 bg-slate-900 p-1.5 text-sm text-white";

function StatusBadge({ status, label }) {
  return <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs ${STATUS_STYLES[status] || "bg-slate-600"}`}>{label}</span>;
}

StatusBadge.propTypes = { status: PropTypes.string.isRequired, label: PropTypes.string.isRequired };

// Enquiry management for one department (``department``), the enquiries assigned to the signed-in
// person (``mine``), or every department the person may see. The API limits everything to the
// caller's departments and role; this page only hides controls the API would refuse.
function EnquiryManagement({ me = null, department: fixedDepartment = "", mine = false, initial = null }) {
  const permissions = me?.permissions || { assign_enquiries: true, move_enquiries: true };
  const [department, setDepartment] = useState(fixedDepartment || initial?.department || "");
  const [status, setStatus] = useState(initial?.status ?? "open");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [dates, setDates] = useState({ from: "", to: "" });
  const [data, setData] = useState({ enquiries: [], stats: null, notifications: null, departments: null });
  const [selected, setSelected] = useState(null);
  const [directory, setDirectory] = useState([]);
  const [form, setForm] = useState({ status: "pending", note: "", staff_response: "", resolution: "", department: "", assigned_to_id: "" });
  const [noteText, setNoteText] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    setDepartment(fixedDepartment || initial?.department || "");
    setSelected(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fixedDepartment]);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const params = {};
      if (department) params.department = department;
      if (status) params.status = status;
      if (query) params.q = query;
      if (mine) params.assigned = "me";
      if (dates.from) params.from = dates.from;
      if (dates.to) params.to = dates.to;
      setData(await fetchEnquiries(params));
    } catch (err) {
      setError(getErrorMessage(err, "Could not load enquiries."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [department, status, query, mine, dates.from, dates.to]);

  const open = async (id) => {
    setError("");
    setNotice("");
    try {
      const { enquiry } = await getEnquiry(id);
      setSelected(enquiry);
      setNoteText("");
      setForm({
        status: NEXT_STATUS[enquiry.status] || enquiry.status,
        note: "",
        staff_response: enquiry.staff_response || "",
        resolution: enquiry.resolution || "",
        department: "",
        assigned_to_id: enquiry.assigned_to_id || "",
      });
      if (permissions.assign_enquiries) {
        fetchStaffDirectory(enquiry.department).then((d) => setDirectory(d.staff || [])).catch(() => setDirectory([]));
      }
    } catch (err) {
      setError(getErrorMessage(err, "Could not open the enquiry."));
    }
  };

  useEffect(() => {
    if (initial?.open) open(initial.open);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initial?.open]);

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = { status: form.status, note: form.note };
      if (form.staff_response.trim() !== (selected.staff_response || "")) payload.staff_response = form.staff_response;
      if (form.resolution.trim() !== (selected.resolution || "")) payload.resolution = form.resolution;
      if (form.department) payload.department = form.department;
      if (form.assigned_to_id !== (selected.assigned_to_id || "")) payload.assigned_to_id = form.assigned_to_id;
      const result = await updateEnquiryStatus(selected.id, payload);
      const { enquiry } = result;
      if (result.visible === false) {
        setSelected(null);
        setNotice(`${enquiry.reference} was moved to ${enquiry.department_label}.`);
      } else {
        setSelected(enquiry);
        setForm((prev) => ({ ...prev, note: "", department: "", status: NEXT_STATUS[enquiry.status] || enquiry.status }));
        setNotice(`${enquiry.reference} saved · ${STATUS_LABELS[enquiry.status]}.`);
      }
      await load();
    } catch (err) {
      setError(getErrorMessage(err, "Could not update the enquiry."));
    } finally {
      setSaving(false);
    }
  };

  const takeIt = async () => {
    try {
      const { enquiry } = await updateEnquiryStatus(selected.id, { assigned_to_id: "me" });
      setSelected(enquiry);
      setForm((prev) => ({ ...prev, assigned_to_id: enquiry.assigned_to_id || "" }));
      setNotice(`${enquiry.reference} is now assigned to you.`);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, "Could not assign the enquiry."));
    }
  };

  const addNote = async (e) => {
    e.preventDefault();
    try {
      const { enquiry } = await addEnquiryNote(selected.id, noteText);
      setSelected(enquiry);
      setNoteText("");
    } catch (err) {
      setError(getErrorMessage(err, "Could not add the note."));
    }
  };

  const departments = data.departments || ENQUIRY_DEPARTMENTS;
  const stats = data.stats;
  const notifications = data.notifications;
  const missingEmail = notifications
    ? Object.entries(notifications.departments).filter(([, ok]) => !ok).map(([d]) => ENQUIRY_DEPARTMENTS[d])
    : [];
  const title = mine ? "Assigned to me" : fixedDepartment ? `${ENQUIRY_DEPARTMENTS[fixedDepartment]} enquiries` : "All enquiries";

  return (
    <div className="space-y-5 text-white">
      <div>
        <h2 className="text-2xl font-bold">{title}</h2>
        <p className="mt-1 text-sm text-slate-400">
          Questions USIUBOT could not answer reliably, sent by people who asked USIU-Africa staff to follow up (with consent).
        </p>
      </div>

      {notifications && (!notifications.smtp_configured || missingEmail.length > 0) && (
        <p className="rounded-lg border border-amber-700/60 bg-amber-900/20 p-2 text-sm text-amber-100">
          Email notifications are not fully set up
          {!notifications.smtp_configured && " (SMTP is not configured)"}
          {missingEmail.length > 0 && ` (no staff address for ${missingEmail.join(", ")})`}.
          Enquiries are still saved and managed here; enquirers are told their enquiry was recorded, not emailed.
        </p>
      )}

      {stats && !fixedDepartment && !mine && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {Object.entries(departments).map(([key, label]) => {
            const s = stats.by_department[key] || {};
            const openCount = OPEN_ENQUIRY_STATUSES.reduce((n, k) => n + (s[k] || 0), 0);
            return (
              <button type="button" key={key} onClick={() => setDepartment(key)}
                className="rounded-lg border border-slate-700 bg-slate-800 p-3 text-left text-sm hover:border-amber-400/60">
                <p className="font-medium">{label}</p>
                <p className="text-slate-300">Open {openCount} · Resolved {s.resolved || 0} · Closed {s.closed || 0}</p>
              </button>
            );
          })}
        </div>
      )}

      <div className="flex flex-wrap items-end gap-3 text-sm">
        <form className="flex items-end gap-2" onSubmit={(e) => { e.preventDefault(); setQuery(search.trim()); }}>
          <label className="flex flex-col">
            Search
            <input type="search" className={field} placeholder="Reference, question, name or email" value={search}
              maxLength={200} onChange={(e) => setSearch(e.target.value)} />
          </label>
          <button type="submit" className="rounded-lg bg-slate-700 px-3 py-1.5 hover:bg-slate-600">Search</button>
        </form>
        {!fixedDepartment && (
          <label className="flex flex-col">
            Department
            <select className={field} value={department} onChange={(e) => setDepartment(e.target.value)}>
              <option value="">All</option>
              {Object.entries(departments).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
        )}
        <label className="flex flex-col">
          Status
          <select className={field} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="open">Open (all unresolved)</option>
            <option value="attention">Awaiting attention (new, pending)</option>
            <option value="done">Resolved or closed</option>
            <option value="">All</option>
            {Object.entries(STATUS_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
        <label className="flex flex-col">
          From
          <input type="date" className={field} value={dates.from} onChange={(e) => setDates({ ...dates, from: e.target.value })} />
        </label>
        <label className="flex flex-col">
          To
          <input type="date" className={field} value={dates.to} onChange={(e) => setDates({ ...dates, to: e.target.value })} />
        </label>
        <button type="button" onClick={load} className="rounded-lg bg-slate-700 px-3 py-1.5 hover:bg-slate-600">Refresh</button>
      </div>

      {error && <p className="rounded-lg bg-red-900/50 px-3 py-2 text-red-200" role="alert">{error}</p>}
      {notice && <p className="rounded-lg bg-emerald-900/40 px-3 py-2 text-emerald-200" role="status">{notice}</p>}

      {loading ? (
        <p className="text-slate-400">Loading enquiries…</p>
      ) : data.enquiries.length === 0 ? (
        <p className="text-slate-400">No enquiries match these filters.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-700">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-slate-800 text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="p-2">Reference</th>
                <th className="p-2">Question</th>
                <th className="p-2">From</th>
                {!fixedDepartment && <th className="p-2">Department</th>}
                <th className="p-2">Status</th>
                <th className="p-2">Assigned to</th>
                <th className="p-2">Received</th>
                <th className="p-2"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {data.enquiries.map((e) => (
                <tr key={e.id} className={`border-t border-slate-700 align-top ${selected?.id === e.id ? "bg-slate-800/70" : ""}`}>
                  <td className="p-2 font-mono text-xs">{e.reference}</td>
                  <td className="max-w-xs p-2">{e.question}</td>
                  <td className="p-2 text-xs text-slate-300">{e.contact?.name}{e.user_group_label && <span className="block text-slate-400">{e.user_group_label}</span>}</td>
                  {!fixedDepartment && <td className="p-2 text-xs">{e.department_label}</td>}
                  <td className="p-2"><StatusBadge status={e.status} label={e.status_label} /></td>
                  <td className="p-2 text-xs text-slate-300">{e.assigned_to || "—"}</td>
                  <td className="p-2 text-xs text-slate-300">{formatDate(e.created_at)}</td>
                  <td className="p-2">
                    <button type="button" onClick={() => open(e.id)} className="rounded-lg bg-blue-700 px-2 py-1 text-xs hover:bg-blue-600">Open</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <div className="space-y-4 rounded-xl border border-slate-700 bg-slate-900 p-4 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="flex items-center gap-2 text-lg font-semibold">
              <span className="font-mono">{selected.reference}</span>
              <StatusBadge status={selected.status} label={selected.status_label} />
            </h3>
            <div className="flex gap-2">
              {selected.assigned_to_id !== me?.id && me && (
                <button type="button" onClick={takeIt} className="rounded-lg bg-slate-700 px-2 py-1 text-xs hover:bg-slate-600">Assign to me</button>
              )}
              <button type="button" onClick={() => setSelected(null)} className="rounded-lg bg-slate-700 px-2 py-1 text-xs hover:bg-slate-600">Close</button>
            </div>
          </div>
          <div className="rounded-lg bg-slate-800 p-3">
            <p className="text-xs uppercase tracking-wide text-slate-400">Original question</p>
            <p className="mt-1 whitespace-pre-wrap">{selected.question}</p>
          </div>
          <div className="grid gap-1 text-slate-300 md:grid-cols-2">
            <p>Received: {formatDate(selected.created_at)}</p>
            <p>Department: {selected.department_label} ({selected.department_source})</p>
            <p>Name: {selected.contact.name}</p>
            <p>Email: <a className="text-sky-300 underline" href={`mailto:${selected.contact.email}`}>{selected.contact.email}</a></p>
            {selected.contact.phone && <p>Phone: {selected.contact.phone}</p>}
            {selected.user_group_label && <p>Enquirer: {selected.user_group_label}</p>}
            <p>Consent: {selected.consent.given ? `given ${formatDate(selected.consent.at)}` : "not recorded"}</p>
            <p>Assigned to: {selected.assigned_to || "nobody yet"}</p>
            <p>Registered user: {selected.registered_user ? "yes" : "no"}</p>
            {selected.resolved_at && <p>Resolved: {formatDate(selected.resolved_at)}</p>}
          </div>

          <form onSubmit={save} className="grid gap-3 md:grid-cols-2">
            <label className="flex flex-col">
              Status
              <select className={field} value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                {Object.entries(STATUS_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </label>
            {permissions.assign_enquiries ? (
              <label className="flex flex-col">
                Assigned staff member
                <select className={field} value={form.assigned_to_id} onChange={(e) => setForm({ ...form, assigned_to_id: e.target.value })}>
                  <option value="">Unassigned</option>
                  {selected.assigned_to_id && !directory.some((p) => p.id === selected.assigned_to_id) && (
                    <option value={selected.assigned_to_id}>{selected.assigned_to}</option>
                  )}
                  {directory.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.email})</option>)}
                </select>
              </label>
            ) : <div />}
            {permissions.move_enquiries && (
              <label className="flex flex-col">
                Move to department (optional)
                <select className={field} value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })}>
                  <option value="">Keep {selected.department_label}</option>
                  {Object.entries(ENQUIRY_DEPARTMENTS).filter(([v]) => v !== selected.department)
                    .map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </label>
            )}
            <label className="flex flex-col">
              History note for this change (optional)
              <input className={field} value={form.note} maxLength={2000} onChange={(e) => setForm({ ...form, note: e.target.value })} />
            </label>
            <label className="flex flex-col md:col-span-2">
              Response to the enquirer (shown when they track the enquiry; emailed to them only if email is configured)
              <textarea rows={3} className={field} value={form.staff_response} maxLength={5000}
                onChange={(e) => setForm({ ...form, staff_response: e.target.value })} />
            </label>
            <label className="flex flex-col md:col-span-2">
              Resolution details (internal; a response or resolution is required to mark it resolved)
              <textarea rows={2} className={field} value={form.resolution} maxLength={5000}
                onChange={(e) => setForm({ ...form, resolution: e.target.value })} />
            </label>
            <div className="flex flex-wrap gap-2 md:col-span-2">
              <button type="submit" disabled={saving} className="rounded-lg bg-amber-400 px-4 py-1.5 font-semibold text-slate-950 hover:bg-amber-300 disabled:opacity-50">
                {saving ? "Saving…" : "Save changes"}
              </button>
            </div>
          </form>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="font-medium">Internal notes <span className="text-xs text-slate-400">(staff only, never shown to the enquirer)</span></p>
              <ul className="mt-2 space-y-2">
                {(selected.notes || []).map((n) => (
                  <li key={n.id} className="rounded-lg bg-slate-800 p-2">
                    <p className="whitespace-pre-wrap">{n.text}</p>
                    <p className="mt-1 text-xs text-slate-400">{n.by} · {formatDate(n.at)}</p>
                  </li>
                ))}
                {!(selected.notes || []).length && <li className="text-xs text-slate-400">No notes yet.</li>}
              </ul>
              <form onSubmit={addNote} className="mt-2 flex gap-2">
                <input className={`${field} mt-0 flex-1`} value={noteText} maxLength={2000} placeholder="Add an internal note"
                  onChange={(e) => setNoteText(e.target.value)} />
                <button type="submit" disabled={!noteText.trim()} className="rounded-lg bg-slate-700 px-3 hover:bg-slate-600 disabled:opacity-50">Add</button>
              </form>
            </div>
            <div>
              <p className="font-medium">History</p>
              <ul className="mt-2 space-y-1 text-xs text-slate-300">
                {(selected.history || []).map((h, i) => (
                  <li key={i}>
                    {formatDate(h.at)} · {STATUS_LABELS[h.status] || h.status} · {h.by}
                    {h.assigned_to && ` · assigned to ${h.assigned_to}`}
                    {h.department && ` · moved to ${ENQUIRY_DEPARTMENTS[h.department]}`}
                    {h.responded && " · response recorded"}
                    {h.note && ` · ${h.note}`}
                  </li>
                ))}
              </ul>
              {(selected.notifications_log || []).length > 0 && (
                <>
                  <p className="mt-3 font-medium">Notifications</p>
                  <ul className="mt-1 space-y-1 text-xs text-slate-300">
                    {selected.notifications_log.map((n, i) => (
                      <li key={i}>{formatDate(n.at)} · {n.event.replace("_", " ")} → {n.to}: {NOTIFICATION_TEXT[n.status] || n.status}</li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

EnquiryManagement.propTypes = {
  me: PropTypes.object,
  department: PropTypes.string,
  mine: PropTypes.bool,
  initial: PropTypes.shape({ department: PropTypes.string, status: PropTypes.string, open: PropTypes.string }),
};

export default EnquiryManagement;
