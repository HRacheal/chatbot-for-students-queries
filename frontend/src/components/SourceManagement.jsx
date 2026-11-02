import { useEffect, useState } from "react";
import {
  bulkSetSourceStatus, createSource, fetchSources, getErrorMessage, getSource, rebuildSourceIndex, setSourceStatus,
  updateSource,
} from "../lib/api";
import { CATEGORY_NAMES, DEPARTMENT_LABELS, citationLink, formatSourceDate } from "../lib/citations";
import DatasetImport from "./DatasetImport";

const EMPTY_FORM = {
  url: "",
  title: "",
  department: "admissions",
  content_type: "html",
  source_date: "",
  retrieved_at: "",
  notes: "",
  text: "",
};

const STATUS_STYLES = {
  draft: "bg-gray-600",
  approved: "bg-green-700",
  rejected: "bg-orange-800",
  archived: "bg-red-800",
};

// Review flags set by the import tool; check each one before approving.
const FLAG_LABELS = {
  undated: "no date",
  possibly_outdated: "possibly outdated",
  duplicate_content: "duplicate text",
  personal_data_form: "form / personal data",
  extraction_problem: "check extracted text",
  suspicious_instructions: "contains instructions to AI",
  date_from_file_metadata: "date only in file metadata",
  // Set by the USIUBOT dataset import
  external_source: "external (not USIU-Africa)",
  payment_details: "payment details: confirm with Finance",
  conflict: "unresolved conflict",
  unresolved_issue: "open verification note",
  no_public_url: "no public link (cited by file and page)",
};

const EMPTY_FILTERS = { status: "", kind: "", category: "", origin: "", department: "", flagged: "", search: "" };

const pageRange = (d) => {
  if (!d || !Number.isInteger(d.page_start)) return "";
  return d.page_end && d.page_end !== d.page_start ? `${d.page_start}-${d.page_end}` : `${d.page_start}`;
};

// Admin page for approved knowledge sources. The chatbot answers only from
// sources with status "approved". Content is entered by an administrator
// (pasted page text or an uploaded PDF) or imported as drafts by
// tools/knowledge_sources.py; automated website crawling is disabled.
function SourceManagement() {
  const [sources, setSources] = useState([]);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [selected, setSelected] = useState([]);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [viewing, setViewing] = useState(null);
  const [rebuilding, setRebuilding] = useState(false);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
      const data = await fetchSources(params);
      setSources(data.sources || []);
      setSelected([]);
    } catch (err) {
      setError(getErrorMessage(err, "Could not load sources."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  const setFilterValue = (field) => (e) => setFilters((prev) => ({ ...prev, [field]: e.target.value }));
  const toggle = (id) => setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  const allSelected = sources.length > 0 && selected.length === sources.length;

  const bulk = async (status) => {
    if (!selected.length) return;
    const verb = { approved: "Approve", rejected: "Reject", archived: "Archive", draft: "Return to draft" }[status];
    // Approving makes the text available to the chatbot: the administrator confirms explicitly.
    if (typeof window !== "undefined" && window.confirm &&
        !window.confirm(`${verb} ${selected.length} selected source(s)? Check each source's text and warnings first.`)) {
      return;
    }
    setBulkBusy(true);
    setError("");
    setNotice("");
    try {
      const { report } = await bulkSetSourceStatus(selected, status);
      const failed = report.failed.length
        ? ` ${report.failed.length} could not be changed: ${report.failed.slice(0, 3).map((f) => f.error).join("; ")}`
        : "";
      setNotice(`${report.changed.length} source(s) now ${status}.${failed}`);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, "Could not change the selected sources."));
    } finally {
      setBulkBusy(false);
    }
  };

  const update = (field) => (e) => setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      let payload = { ...form };
      if (file) {
        payload = new FormData();
        Object.entries(form).forEach(([key, value]) => {
          if (key !== "text" && key !== "content_type" && value) payload.append(key, value);
        });
        payload.append("content_type", "pdf");
        payload.append("file", file);
      }
      await createSource(payload);
      setForm(EMPTY_FORM);
      setFile(null);
      setNotice("Source saved as a draft. Review it, then approve it to make it available to the chatbot.");
      await load();
    } catch (err) {
      setError(getErrorMessage(err, "Could not save the source."));
    } finally {
      setSaving(false);
    }
  };

  const changeDepartment = async (source, department) => {
    setError("");
    setNotice("");
    try {
      await updateSource(source.id, { department });
      setNotice(`"${source.title}" moved to ${DEPARTMENT_LABELS[department]}.`);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, "Could not change the department."));
    }
  };

  const changeStatus = async (source, status) => {
    setError("");
    setNotice("");
    try {
      await setSourceStatus(source.id, status);
      setNotice(`"${source.title}" is now ${status}.`);
      if (viewing?.id === source.id) setViewing(null);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, "Could not change the status."));
    }
  };

  const view = async (source) => {
    setError("");
    try {
      setViewing((await getSource(source.id)).source);
    } catch (err) {
      setError(getErrorMessage(err, "Could not open the source."));
    }
  };

  const rebuild = async () => {
    setRebuilding(true);
    setError("");
    setNotice("");
    try {
      const { report } = await rebuildSourceIndex();
      setNotice(`Search index rebuilt: ${report.approved_sources} approved sources, ${report.chunks} passages` +
        (report.failed.length ? `; ${report.failed.length} could not be indexed.` : ".") +
        " Source records and approvals were not changed.");
    } catch (err) {
      setError(getErrorMessage(err, "Could not rebuild the index."));
    } finally {
      setRebuilding(false);
    }
  };

  return (
    <div className="space-y-6 text-white">
      <div>
        <h2 className="text-2xl font-bold">Approved Sources</h2>
        <p className="mt-1 text-sm text-gray-400">
          USIUBOT answers only from approved sources and cites them. Paste the text of an official
          USIU-Africa page, or upload an official PDF. Answers written for logged questions appear
          here as draft staff answers. Automatic website crawling is disabled until permitted access
          is in place.
        </p>
      </div>

      {error && <p className="rounded bg-red-900/60 px-3 py-2 text-red-200">{error}</p>}
      {notice && <p className="rounded bg-green-900/60 px-3 py-2 text-green-200">{notice}</p>}

      <DatasetImport onImported={load} />

      <form onSubmit={handleCreate} className="grid gap-3 rounded-lg bg-gray-900 p-4 md:grid-cols-2">
        <label className="flex flex-col text-sm">
          Official URL (https, usiu.ac.ke)
          <input required className="mt-1 rounded bg-gray-700 p-2" value={form.url} onChange={update("url")}
            placeholder="https://www.usiu.ac.ke/..." />
        </label>
        <label className="flex flex-col text-sm">
          Title
          <input required className="mt-1 rounded bg-gray-700 p-2" value={form.title} onChange={update("title")} />
        </label>
        <label className="flex flex-col text-sm">
          Department
          <select className="mt-1 rounded bg-gray-700 p-2" value={form.department} onChange={update("department")}>
            {Object.entries(DEPARTMENT_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-sm">
          Source date (as printed: YYYY, YYYY-MM or YYYY-MM-DD; optional)
          <input className="mt-1 rounded bg-gray-700 p-2" value={form.source_date} onChange={update("source_date")} />
        </label>
        <label className="flex flex-col text-sm">
          Date the content was copied (YYYY-MM-DD; default today)
          <input className="mt-1 rounded bg-gray-700 p-2" value={form.retrieved_at} onChange={update("retrieved_at")} />
        </label>
        <label className="flex flex-col text-sm">
          Notes (optional)
          <input className="mt-1 rounded bg-gray-700 p-2" value={form.notes} onChange={update("notes")} />
        </label>
        <label className="flex flex-col text-sm md:col-span-2">
          Page text {file ? "(ignored: text will be extracted from the PDF)" : ""}
          <textarea rows={6} className="mt-1 rounded bg-gray-700 p-2" value={form.text} onChange={update("text")}
            disabled={Boolean(file)} />
        </label>
        <label className="flex flex-col text-sm">
          Or upload an official PDF (optional)
          <input type="file" accept="application/pdf,.pdf" className="mt-1"
            onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </label>
        <div className="flex items-end justify-end">
          <button type="submit" disabled={saving}
            className="rounded bg-blue-600 px-4 py-2 font-medium hover:bg-blue-500 disabled:opacity-50">
            {saving ? "Saving..." : "Save as draft"}
          </button>
        </div>
      </form>

      <div className="flex flex-wrap items-center gap-3" aria-label="Source filters">
        <label className="text-sm">
          Show:
          <select className="ml-2 rounded bg-gray-700 p-1" value={filters.status} onChange={setFilterValue("status")}>
            <option value="">All</option>
            <option value="draft">Draft</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="archived">Archived</option>
          </select>
        </label>
        <label className="text-sm">
          Kind:
          <select className="ml-2 rounded bg-gray-700 p-1" value={filters.kind} onChange={setFilterValue("kind")}>
            <option value="">All</option>
            <option value="dataset">From the dataset</option>
            <option value="manual">Added here</option>
          </select>
        </label>
        <label className="text-sm">
          Category:
          <select className="ml-2 rounded bg-gray-700 p-1" value={filters.category} onChange={setFilterValue("category")}>
            <option value="">All</option>
            {Object.entries(CATEGORY_NAMES).map(([id, name]) => <option key={id} value={id}>{id} {name}</option>)}
          </select>
        </label>
        <label className="text-sm">
          Origin:
          <select className="ml-2 rounded bg-gray-700 p-1" value={filters.origin} onChange={setFilterValue("origin")}>
            <option value="">All</option>
            <option value="official">Official USIU-Africa</option>
            <option value="external">External</option>
          </select>
        </label>
        <label className="text-sm">
          Department:
          <select className="ml-2 rounded bg-gray-700 p-1" value={filters.department} onChange={setFilterValue("department")}>
            <option value="">All</option>
            {Object.entries(DEPARTMENT_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
        <label className="text-sm">
          Warnings:
          <select className="ml-2 rounded bg-gray-700 p-1" value={filters.flagged} onChange={setFilterValue("flagged")}>
            <option value="">All</option>
            <option value="yes">With review flags</option>
            <option value="no">Without flags</option>
          </select>
        </label>
        <label className="text-sm">
          Title:
          <input className="ml-2 rounded bg-gray-700 p-1" value={filters.search} maxLength={200}
            onChange={setFilterValue("search")} />
        </label>
        <button onClick={load} className="rounded bg-gray-700 px-3 py-1 text-sm hover:bg-gray-600">Refresh</button>
        <button onClick={rebuild} disabled={rebuilding}
          title="Re-creates the search passages of approved sources; never changes sources or approvals"
          className="rounded bg-gray-700 px-3 py-1 text-sm hover:bg-gray-600 disabled:opacity-50">
          {rebuilding ? "Rebuilding..." : "Rebuild search index"}
        </button>
      </div>

      {selected.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded bg-gray-800 p-2 text-sm" aria-label="Bulk actions">
          <span>{selected.length} selected</span>
          <button onClick={() => bulk("approved")} disabled={bulkBusy}
            className="rounded bg-green-700 px-2 py-1 text-xs hover:bg-green-600 disabled:opacity-40">Approve selected</button>
          <button onClick={() => bulk("rejected")} disabled={bulkBusy}
            className="rounded bg-orange-800 px-2 py-1 text-xs hover:bg-orange-700 disabled:opacity-40">Reject selected</button>
          <button onClick={() => bulk("archived")} disabled={bulkBusy}
            className="rounded bg-red-800 px-2 py-1 text-xs hover:bg-red-700 disabled:opacity-40">Archive selected</button>
          <button onClick={() => bulk("draft")} disabled={bulkBusy}
            className="rounded bg-gray-600 px-2 py-1 text-xs hover:bg-gray-500 disabled:opacity-40">Back to draft</button>
          <button onClick={() => setSelected([])} className="text-xs text-gray-300 underline">Clear selection</button>
        </div>
      )}

      {loading ? (
        <p className="text-gray-400">Loading sources...</p>
      ) : sources.length === 0 ? (
        <p className="text-gray-400">No sources yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-gray-400">
              <tr>
                <th className="p-2">
                  <input type="checkbox" aria-label="Select all shown sources" checked={allSelected}
                    onChange={() => setSelected(allSelected ? [] : sources.map((s) => s.id))} />
                </th>
                <th className="p-2">Title</th>
                <th className="p-2">Department</th>
                <th className="p-2">Status</th>
                <th className="p-2">Dates</th>
                <th className="p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => (
                <tr key={s.id} className="border-t border-gray-700 align-top">
                  <td className="p-2">
                    <input type="checkbox" aria-label={`Select ${s.title}`} checked={selected.includes(s.id)}
                      onChange={() => toggle(s.id)} />
                  </td>
                  <td className="p-2">
                    {s.data_origin === "external" && (
                      <span className="mr-1 rounded bg-orange-800 px-1.5 py-0.5 text-xs text-orange-100">External</span>
                    )}
                    {citationLink({ url: s.url, external: s.data_origin === "external" }) ? (
                      <a href={s.url} target="_blank" rel="noopener noreferrer" className="text-blue-300 underline">
                        {s.title}
                      </a>
                    ) : (
                      <span>{s.title}</span>
                    )}
                    {s.content_type === "pdf" && <span className="ml-2 text-xs text-gray-400">PDF</span>}
                    {s.dataset && (
                      <span className="block text-xs text-gray-400">
                        {s.category} {CATEGORY_NAMES[s.category] || ""}
                        {s.dataset.document_file ? ` · ${s.dataset.document_file}` : ""}
                        {pageRange(s.dataset) ? ` · p. ${pageRange(s.dataset)}` : ""}
                        {s.passage_count ? ` · ${s.passage_count} passage(s)` : ""}
                      </span>
                    )}
                    {s.content_type === "staff_answer" && (
                      <span className="ml-2 text-xs text-blue-300">Staff answer (no link)</span>
                    )}
                    {!s.has_text && <span className="ml-2 text-xs text-yellow-300">no text</span>}
                    {s.review_flags?.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1" aria-label="Review flags">
                        {s.review_flags.map((flag) => (
                          <span key={flag} className="rounded bg-yellow-900/60 px-1.5 py-0.5 text-xs text-yellow-200">
                            {FLAG_LABELS[flag] || flag}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="p-2">
                    {s.status === "approved" ? (
                      DEPARTMENT_LABELS[s.department] || s.department
                    ) : (
                      <select className="rounded bg-gray-700 p-1 text-xs" value={s.department}
                        onChange={(e) => changeDepartment(s, e.target.value)}>
                        {Object.entries(DEPARTMENT_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    )}
                  </td>
                  <td className="p-2">
                    <span className={`rounded px-2 py-0.5 text-xs ${STATUS_STYLES[s.status] || "bg-gray-600"}`}>
                      {s.status}
                    </span>
                    {s.stale && <span className="ml-2 text-xs text-yellow-300">may be out of date</span>}
                  </td>
                  <td className="p-2 text-xs text-gray-300">
                    {s.source_date && <div>Dated {s.source_date}</div>}
                    {s.retrieved_at && <div>Retrieved {formatSourceDate(s.retrieved_at)}</div>}
                  </td>
                  <td className="p-2 space-x-2 whitespace-nowrap">
                    <button onClick={() => view(s)} className="rounded bg-gray-600 px-2 py-1 text-xs hover:bg-gray-500">
                      View
                    </button>
                    {s.status !== "approved" && (
                      <button onClick={() => changeStatus(s, "approved")} disabled={!s.has_text}
                        className="rounded bg-green-700 px-2 py-1 text-xs hover:bg-green-600 disabled:opacity-40">
                        Approve
                      </button>
                    )}
                    {s.status === "draft" && (
                      <button onClick={() => changeStatus(s, "rejected")}
                        className="rounded bg-orange-800 px-2 py-1 text-xs hover:bg-orange-700">
                        Reject
                      </button>
                    )}
                    {s.status !== "archived" && (
                      <button onClick={() => changeStatus(s, "archived")}
                        className="rounded bg-red-800 px-2 py-1 text-xs hover:bg-red-700">
                        Archive
                      </button>
                    )}
                    {(s.status === "archived" || s.status === "rejected") && (
                      <button onClick={() => changeStatus(s, "draft")}
                        className="rounded bg-gray-600 px-2 py-1 text-xs hover:bg-gray-500">
                        Back to draft
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {viewing && (
        <div className="space-y-2 rounded-lg bg-gray-900 p-4 text-sm" aria-label="Source details">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium">{viewing.title}</h3>
            <button onClick={() => setViewing(null)} className="rounded bg-gray-700 px-2 py-1 text-xs hover:bg-gray-600">Close</button>
          </div>
          <div className="grid gap-1 text-gray-300 md:grid-cols-2">
            <p>Status: {viewing.status}</p>
            <p>Department: {DEPARTMENT_LABELS[viewing.department] || viewing.department}</p>
            <p className="break-all">
              URL: {citationLink({ url: viewing.url, external: viewing.data_origin === "external" }) || "(none)"}
            </p>
            <p>Dated: {viewing.source_date || "unknown"} · Retrieved: {formatSourceDate(viewing.retrieved_at) || "unknown"}</p>
            {viewing.approved_by && <p>Approved by {viewing.approved_by} {formatSourceDate(viewing.approved_at)}</p>}
            {viewing.notes && <p className="md:col-span-2">Notes: {viewing.notes}</p>}
            {viewing.dataset && (
              <>
                <p>
                  Origin: {viewing.data_origin === "external"
                    ? `external (${viewing.dataset.publisher || "not USIU-Africa"})` : "official USIU-Africa"}
                </p>
                <p>Category: {viewing.category} {CATEGORY_NAMES[viewing.category] || ""}</p>
                <p>Dataset section: {viewing.dataset.section_id}</p>
                <p>
                  Document: {viewing.dataset.document_title}
                  {viewing.dataset.document_file ? ` (${viewing.dataset.document_file})` : ""}
                </p>
                {pageRange(viewing.dataset) && <p>Pages: {pageRange(viewing.dataset)}</p>}
                <p>
                  Collected: {viewing.dataset.collected_at || "unknown"} · Published:{" "}
                  {viewing.dataset.publication_date || "not stated"}
                </p>
                <p>
                  Verification: {viewing.dataset.verification_status} · Text fidelity:{" "}
                  {viewing.dataset.content_fidelity || "n/a"}
                </p>
                {viewing.dataset.issues?.length > 0 && (
                  <div className="rounded border border-yellow-700 bg-yellow-900/30 p-2 text-yellow-100 md:col-span-2">
                    <p className="font-medium">Open items in the conflict and verification register</p>
                    <ul className="list-disc pl-5">
                      {viewing.dataset.issues.map((i) => (
                        <li key={i.id}>
                          {i.id} ({i.type}, {i.severity}, {i.status}
                          {i.user_warning ? ", shown to students as a warning" : ""}): {i.summary}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
          </div>
          <p className="font-medium">
            Text the chatbot would use ({(viewing.text || "").length} characters). Compare it with the official page before approving.
          </p>
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded bg-gray-800 p-3 text-xs text-gray-200">
            {viewing.text || "(no text)"}
          </pre>
          {viewing.status_history?.length > 0 && (
            <ul className="text-xs text-gray-400">
              {viewing.status_history.map((h, i) => (
                <li key={i}>{formatSourceDate(h.at)} · {h.status} · {h.by}{h.note ? ` · ${h.note}` : ""}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export default SourceManagement;
