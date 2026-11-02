import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import {
  createStaffAccount,
  fetchStaffAccounts,
  getErrorMessage,
  resetStaffPassword,
  updateStaffAccount,
} from "../lib/api";
import { ENQUIRY_DEPARTMENTS, ROLE_LABELS } from "../lib/workflow";

const field = "mt-1 rounded-lg border border-slate-600 bg-slate-900 p-1.5 text-sm text-white";
const EMPTY = { email: "", name: "", role: "department_staff", departments: [], scope: "department" };
const formatDate = (value) => (value ? new Date(value).toLocaleString() : "never");

function DepartmentPicker({ value, onChange, disabled = false }) {
  return (
    <fieldset className="flex flex-wrap gap-x-4 gap-y-1" disabled={disabled}>
      {Object.entries(ENQUIRY_DEPARTMENTS).map(([key, label]) => (
        <label key={key} className="flex items-center gap-1.5 text-xs text-slate-300">
          <input type="checkbox" checked={value.includes(key)}
            onChange={(e) => onChange(e.target.checked ? [...value, key] : value.filter((d) => d !== key))} />
          {label}
        </label>
      ))}
    </fieldset>
  );
}

DepartmentPicker.propTypes = { value: PropTypes.array.isRequired, onChange: PropTypes.func.isRequired, disabled: PropTypes.bool };

// Super Administrators create, edit, (de)activate staff accounts and reset passwords.
// Department Administrators see their department's staff (read-only).
function StaffManagement({ me }) {
  const canManage = Boolean(me?.permissions?.manage_staff);
  const [staff, setStaff] = useState([]);
  const [filter, setFilter] = useState({ active: "all", q: "" });
  const [form, setForm] = useState(EMPTY);
  const [editing, setEditing] = useState(null);
  const [secret, setSecret] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = async () => {
    setError("");
    try {
      setStaff((await fetchStaffAccounts(filter)).staff || []);
    } catch (err) {
      setError(getErrorMessage(err, "Could not load staff accounts."));
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter.active]);

  const create = async (e) => {
    e.preventDefault();
    setError("");
    setNotice("");
    try {
      const data = await createStaffAccount(form);
      setSecret({ email: data.staff.email, password: data.temporary_password });
      setForm(EMPTY);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, "Could not create the account."));
    }
  };

  const saveEdit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const { staff: updated } = await updateStaffAccount(editing.id, {
        name: editing.name, role: editing.role, departments: editing.departments, scope: editing.scope,
      });
      setNotice(`${updated.email} updated.`);
      setEditing(null);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, "Could not update the account."));
    }
  };

  const toggleActive = async (person) => {
    const verb = person.active ? "Deactivate" : "Reactivate";
    if (!window.confirm(`${verb} ${person.email}?${person.active ? " Their current sessions end immediately." : ""}`)) return;
    try {
      await updateStaffAccount(person.id, { active: !person.active });
      setNotice(`${person.email} ${person.active ? "deactivated" : "reactivated"}.`);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, "Could not change the account."));
    }
  };

  const reset = async (person) => {
    if (!window.confirm(`Reset the password of ${person.email}? Their current sessions end immediately.`)) return;
    try {
      const data = await resetStaffPassword(person.id);
      setSecret({ email: person.email, password: data.temporary_password });
      await load();
    } catch (err) {
      setError(getErrorMessage(err, "Could not reset the password."));
    }
  };

  return (
    <div className="space-y-5 text-white">
      <div>
        <h2 className="text-2xl font-bold">Staff accounts</h2>
        <p className="mt-1 text-sm text-slate-400">
          {canManage
            ? "Only Super Administrators can create accounts; there is no public staff registration. Accounts are never deleted (deactivate them instead) so histories stay accurate."
            : "Staff of your department(s). Contact a Super Administrator to add or change accounts."}
        </p>
      </div>

      {error && <p className="rounded-lg bg-red-900/50 px-3 py-2 text-red-200" role="alert">{error}</p>}
      {notice && <p className="rounded-lg bg-emerald-900/40 px-3 py-2 text-emerald-200" role="status">{notice}</p>}
      {secret && (
        <div className="rounded-lg border border-amber-500/60 bg-amber-900/20 p-3 text-sm text-amber-100" role="status">
          <p className="font-medium">Temporary password for {secret.email} (shown once):</p>
          <p className="mt-1 select-all break-all font-mono text-base text-white">{secret.password}</p>
          <p className="mt-1 text-xs">Give it to the staff member in person or through a secure channel. They must choose their own password at first sign-in.</p>
          <button type="button" className="mt-2 text-xs underline" onClick={() => setSecret(null)}>I have recorded it — hide</button>
        </div>
      )}

      {canManage && (
        <form onSubmit={create} className="grid gap-3 rounded-xl border border-slate-700 bg-slate-800/80 p-4 md:grid-cols-2">
          <h3 className="font-semibold md:col-span-2">New staff account</h3>
          <label className="flex flex-col text-sm">Full name
            <input className={field} required maxLength={100} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </label>
          <label className="flex flex-col text-sm">Work email
            <input type="email" className={field} required maxLength={254} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </label>
          <label className="flex flex-col text-sm">Role
            <select className={field} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              {Object.entries(ROLE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          {form.role === "department_staff" && (
            <label className="flex flex-col text-sm">Can see
              <select className={field} value={form.scope} onChange={(e) => setForm({ ...form, scope: e.target.value })}>
                <option value="department">All enquiries of their departments</option>
                <option value="assigned">Only enquiries assigned to them</option>
              </select>
            </label>
          )}
          {form.role !== "super_admin" && (
            <div className="text-sm md:col-span-2">
              <p className="mb-1">Departments</p>
              <DepartmentPicker value={form.departments} onChange={(departments) => setForm({ ...form, departments })} />
            </div>
          )}
          <div className="md:col-span-2">
            <button type="submit" className="rounded-lg bg-amber-400 px-4 py-1.5 font-semibold text-slate-950 hover:bg-amber-300">Create account</button>
          </div>
        </form>
      )}

      <div className="flex flex-wrap items-end gap-3 text-sm">
        <form className="flex items-end gap-2" onSubmit={(e) => { e.preventDefault(); load(); }}>
          <label className="flex flex-col">Search
            <input type="search" className={field} value={filter.q} placeholder="Name or email"
              onChange={(e) => setFilter({ ...filter, q: e.target.value })} />
          </label>
          <button type="submit" className="rounded-lg bg-slate-700 px-3 py-1.5 hover:bg-slate-600">Search</button>
        </form>
        <label className="flex flex-col">Show
          <select className={field} value={filter.active} onChange={(e) => setFilter({ ...filter, active: e.target.value })}>
            <option value="all">All accounts</option>
            <option value="true">Active</option>
            <option value="false">Deactivated</option>
          </select>
        </label>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-700">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="bg-slate-800 text-xs uppercase tracking-wide text-slate-400">
            <tr><th className="p-2">Name</th><th className="p-2">Role</th><th className="p-2">Departments</th>
              <th className="p-2">Status</th><th className="p-2">Last sign-in</th>{canManage && <th className="p-2"><span className="sr-only">Actions</span></th>}</tr>
          </thead>
          <tbody>
            {staff.map((p) => (
              <tr key={p.id} className="border-t border-slate-700 align-top">
                <td className="p-2">{p.name}<span className="block text-xs text-slate-400">{p.email}</span></td>
                <td className="p-2 text-xs">{p.role_label}{p.role === "department_staff" && p.scope === "assigned" && <span className="block text-slate-400">assigned only</span>}</td>
                <td className="p-2 text-xs">{p.role === "super_admin" ? "All" : p.department_labels.join(", ")}</td>
                <td className="p-2 text-xs">
                  {p.active ? "Active" : "Deactivated"}
                  {p.must_change_password && <span className="block text-amber-300">must change password</span>}
                  {p.locked && <span className="block text-red-300">locked (failed sign-ins)</span>}
                </td>
                <td className="p-2 text-xs text-slate-300">{formatDate(p.last_login_at)}</td>
                {canManage && (
                  <td className="space-x-1 whitespace-nowrap p-2">
                    <button type="button" className="rounded bg-slate-700 px-2 py-0.5 text-xs hover:bg-slate-600" onClick={() => setEditing({ ...p })}>Edit</button>
                    <button type="button" className="rounded bg-slate-700 px-2 py-0.5 text-xs hover:bg-slate-600" onClick={() => reset(p)}>Reset password</button>
                    {p.id !== me?.id && (
                      <button type="button" className="rounded bg-slate-700 px-2 py-0.5 text-xs hover:bg-slate-600" onClick={() => toggleActive(p)}>
                        {p.active ? "Deactivate" : "Reactivate"}
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
            {!staff.length && <tr><td className="p-3 text-slate-400" colSpan={6}>No staff accounts yet.</td></tr>}
          </tbody>
        </table>
      </div>

      {editing && (
        <form onSubmit={saveEdit} className="grid gap-3 rounded-xl border border-slate-700 bg-slate-900 p-4 md:grid-cols-2">
          <h3 className="font-semibold md:col-span-2">Edit {editing.email}</h3>
          <label className="flex flex-col text-sm">Full name
            <input className={field} required maxLength={100} value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} />
          </label>
          <label className="flex flex-col text-sm">Role
            <select className={field} value={editing.role} disabled={editing.id === me?.id}
              onChange={(e) => setEditing({ ...editing, role: e.target.value })}>
              {Object.entries(ROLE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          {editing.role === "department_staff" && (
            <label className="flex flex-col text-sm">Can see
              <select className={field} value={editing.scope} onChange={(e) => setEditing({ ...editing, scope: e.target.value })}>
                <option value="department">All enquiries of their departments</option>
                <option value="assigned">Only enquiries assigned to them</option>
              </select>
            </label>
          )}
          {editing.role !== "super_admin" && (
            <div className="text-sm md:col-span-2">
              <p className="mb-1">Departments</p>
              <DepartmentPicker value={editing.departments} onChange={(departments) => setEditing({ ...editing, departments })} />
            </div>
          )}
          <div className="flex gap-2 md:col-span-2">
            <button type="submit" className="rounded-lg bg-amber-400 px-4 py-1.5 font-semibold text-slate-950 hover:bg-amber-300">Save</button>
            <button type="button" className="rounded-lg bg-slate-700 px-4 py-1.5 hover:bg-slate-600" onClick={() => setEditing(null)}>Cancel</button>
          </div>
        </form>
      )}
    </div>
  );
}

StaffManagement.propTypes = { me: PropTypes.object };

export default StaffManagement;
