import { useEffect, useState } from "react";
import { fetchRouting, getErrorMessage, importRoutingContacts, updateRouting } from "../lib/api";

// Admin page: where unresolved questions and enquiries go, per department.
// * Staff delivery addresses are entered by an administrator (never filled automatically).
// * Published contacts can be copied from the dataset as printed; they stay hidden from
//   students until the administrator ticks "Show to students" after the university confirms them.
function RoutingManagement() {
  const [departments, setDepartments] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState("");
  // Super Administrators change everything; a department administrator only their addresses and notes.
  const [fullAccess, setFullAccess] = useState(true);

  const toDraft = (d) => ({
    delivery_emails: (d.delivery_emails || []).join(", "),
    notes: d.notes || "",
    publish_contacts: Boolean(d.publish_contacts),
  });

  const apply = (list) => {
    setDepartments(list);
    setDrafts(Object.fromEntries(list.map((d) => [d.department, toDraft(d)])));
  };

  const load = async () => {
    setError("");
    try {
      const data = await fetchRouting();
      setFullAccess(data.full_access !== false);
      apply(data.departments || []);
    } catch (err) {
      setError(getErrorMessage(err, "Could not load the routing settings."));
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const change = (dept, field, value) => setDrafts((prev) => ({ ...prev, [dept]: { ...prev[dept], [field]: value } }));

  const save = async (dept) => {
    setBusy(dept);
    setError("");
    setNotice("");
    try {
      const draft = drafts[dept];
      const payload = {
        delivery_emails: draft.delivery_emails.split(/[,;]/).map((e) => e.trim()).filter(Boolean),
        notes: draft.notes,
      };
      if (fullAccess) payload.publish_contacts = draft.publish_contacts;
      const { department } = await updateRouting(dept, payload);
      setDepartments((prev) => prev.map((d) => (d.department === dept ? department : d)));
      setDrafts((prev) => ({ ...prev, [dept]: toDraft(department) }));
      setNotice(`${department.label} routing saved.`);
    } catch (err) {
      setError(getErrorMessage(err, "Could not save the routing settings."));
    } finally {
      setBusy("");
    }
  };

  const importContacts = async () => {
    setBusy("import");
    setError("");
    setNotice("");
    try {
      const { report, departments: list } = await importRoutingContacts();
      apply(list);
      setNotice(`Copied ${report.contacts} published contacts for ${report.filled.length} department(s)` +
        (report.skipped_existing.length ? `; ${report.skipped_existing.length} already had contacts and were not changed` : "") +
        ". They are not shown to students until you publish them.");
    } catch (err) {
      setError(getErrorMessage(err, "Could not import the contacts."));
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="space-y-4 text-white">
      <div>
        <h2 className="text-2xl font-bold">Department Routing</h2>
        <p className="mt-1 text-sm text-gray-400">
          Questions USIUBOT cannot answer from approved sources are recorded as unresolved and suggested to one of
          these departments; students can then send an enquiry. Enter staff addresses only when the department has
          confirmed them. Without an address, enquiries are still listed in the Enquiries tab. Contacts copied from
          the dataset are shown exactly as printed by USIU-Africa and are not verified.
        </p>
      </div>
      {error && <p className="rounded bg-red-900/60 px-3 py-2 text-red-200">{error}</p>}
      {notice && <p className="rounded bg-green-900/60 px-3 py-2 text-green-200">{notice}</p>}
      {fullAccess && (
        <button onClick={importContacts} disabled={Boolean(busy)}
          className="rounded bg-gray-700 px-3 py-1 text-sm hover:bg-gray-600 disabled:opacity-50">
          {busy === "import" ? "Copying..." : "Copy published contacts from the dataset"}
        </button>
      )}

      <div className="space-y-3">
        {departments.map((d) => {
          const draft = drafts[d.department] || toDraft(d);
          return (
            <div key={d.department} className="space-y-2 rounded-lg bg-gray-900 p-4 text-sm" aria-label={`${d.label} routing`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-lg font-medium">{d.label}</h3>
                <span className="text-xs text-gray-400">
                  {d.delivery_emails.length ? `${d.delivery_emails.length} staff address(es)`
                    : d.env_delivery_configured ? "staff address set in the server configuration"
                      : "no staff address: enquiries only in the dashboard"}
                </span>
              </div>
              <label className="flex flex-col">
                Staff addresses notified of new enquiries (comma-separated; confirmed by the department)
                <input className="mt-1 rounded bg-gray-700 p-2" value={draft.delivery_emails}
                  onChange={(e) => change(d.department, "delivery_emails", e.target.value)} />
              </label>
              <label className="flex flex-col">
                Notes
                <textarea rows={2} className="mt-1 rounded bg-gray-700 p-2" value={draft.notes}
                  onChange={(e) => change(d.department, "notes", e.target.value)} />
              </label>
              {d.public_contacts.length > 0 && (
                <div>
                  <p className="font-medium text-gray-300">Published contacts (as printed; unverified)</p>
                  <ul className="mt-1 space-y-0.5 text-xs text-gray-300">
                    {d.public_contacts.map((c, i) => (
                      <li key={`${c.record_id || i}`}>
                        {c.office ? `${c.office}: ` : ""}{c.type} {c.value}
                        <span className="text-gray-500"> · {c.source}{c.issue_ids ? ` · check ${c.issue_ids}` : ""}</span>
                      </li>
                    ))}
                  </ul>
                  <label className="mt-1 flex items-center gap-2">
                    <input type="checkbox" checked={draft.publish_contacts} disabled={!fullAccess}
                      onChange={(e) => change(d.department, "publish_contacts", e.target.checked)} />
                    Show these contacts to students with unresolved questions (only after the university confirms them)
                  </label>
                </div>
              )}
              <div className="flex justify-end">
                <button onClick={() => save(d.department)} disabled={Boolean(busy)}
                  className="rounded bg-blue-600 px-3 py-1 hover:bg-blue-500 disabled:opacity-50">
                  {busy === d.department ? "Saving..." : "Save"}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default RoutingManagement;
