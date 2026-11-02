import { useEffect, useMemo, useState } from "react";
import { fetchOfficialLinks, getErrorMessage, previewOfficialLinks, saveOfficialLink } from "../lib/api";
import { DEPARTMENT_LABELS, isOfficialPageUrl } from "../lib/citations";

const EMPTY = { url: "", title: "", department: "admissions", keywords: "" };

// Admin page for the official pages USIUBOT suggests when it cannot verify an answer.
// Links are metadata only (title, URL, department, keywords): never evidence for an answer.
// Changes are stored in the database; the repository catalogue file is never edited.
function OfficialLinks() {
  const [links, setLinks] = useState([]);
  const [counts, setCounts] = useState(null);
  const [filter, setFilter] = useState("");
  const [form, setForm] = useState(EMPTY);
  const [question, setQuestion] = useState("");
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetchOfficialLinks();
      setLinks(data.links || []);
      setCounts(data.counts || null);
    } catch (err) {
      setError(getErrorMessage(err, "Could not load official links."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const save = async (data, message) => {
    setError("");
    setNotice("");
    try {
      await saveOfficialLink(data);
      setNotice(message);
      await load();
      return true;
    } catch (err) {
      setError(getErrorMessage(err, "Could not save the link."));
      return false;
    }
  };

  const add = async (e) => {
    e.preventDefault();
    const keywords = form.keywords.split(",").map((k) => k.trim()).filter(Boolean);
    if (await save({ ...form, keywords }, `Saved "${form.title}". Open the page to check it, then mark it reviewed.`)) {
      setForm(EMPTY);
    }
  };

  const runPreview = async (e) => {
    e.preventDefault();
    setError("");
    try {
      setPreview(await previewOfficialLinks(question));
    } catch (err) {
      setError(getErrorMessage(err, "Could not preview the links."));
    }
  };

  const shown = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return q ? links.filter((l) => `${l.title} ${l.url} ${l.department}`.toLowerCase().includes(q)) : links;
  }, [links, filter]);

  return (
    <div className="space-y-6 text-white">
      <div>
        <h2 className="text-2xl font-bold">Official Links</h2>
        <p className="mt-1 text-sm text-gray-400">
          Official pages USIUBOT suggests when it cannot verify an answer. They are shown to users as unverified
          suggestions, never as evidence. Open each page before marking it reviewed; hide pages that are wrong or out of date.
        </p>
        {counts && (
          <p className="mt-1 text-sm text-gray-300">
            {counts.total} links · {counts.reviewed} reviewed · {counts.hidden} hidden
          </p>
        )}
      </div>

      <form onSubmit={runPreview} className="flex flex-wrap items-end gap-2 rounded-lg bg-gray-900 p-3 text-sm">
        <label className="flex flex-1 flex-col">
          Check which pages a question would get
          <input className="mt-1 rounded bg-gray-700 p-1.5" value={question} maxLength={500}
            placeholder="e.g. How do I request my transcript?" onChange={(e) => setQuestion(e.target.value)} />
        </label>
        <button type="submit" disabled={!question.trim()} className="rounded bg-blue-600 px-3 py-1.5 hover:bg-blue-500 disabled:opacity-50">
          Preview
        </button>
        {preview && (
          <div className="w-full">
            {preview.places_to_look.length === 0 ? (
              <p className="text-yellow-200">No sufficiently relevant official page: users are told so honestly.</p>
            ) : (
              <ol className="list-decimal pl-5">
                {preview.places_to_look.map((p) => (
                  <li key={p.url}>{p.title} <span className="text-xs text-gray-400">({p.reason})</span></li>
                ))}
              </ol>
            )}
          </div>
        )}
      </form>

      <form onSubmit={add} className="grid gap-2 rounded-lg bg-gray-900 p-3 text-sm md:grid-cols-2">
        <p className="font-medium md:col-span-2">Add or correct a link (only https pages on the official website)</p>
        <input className="rounded bg-gray-700 p-1.5" placeholder="https://www.usiu.ac.ke/..." required value={form.url}
          onChange={(e) => setForm({ ...form, url: e.target.value })} />
        <input className="rounded bg-gray-700 p-1.5" placeholder="Title exactly as shown on the page" required maxLength={300}
          value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <select className="rounded bg-gray-700 p-1.5" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })}>
          {Object.entries(DEPARTMENT_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <input className="rounded bg-gray-700 p-1.5" placeholder="Keywords, comma-separated (optional)" value={form.keywords}
          onChange={(e) => setForm({ ...form, keywords: e.target.value })} />
        <div className="md:col-span-2">
          <button type="submit" className="rounded bg-blue-600 px-4 py-1.5 font-medium hover:bg-blue-500">Save link</button>
        </div>
      </form>

      {error && <p className="rounded bg-red-900/60 px-3 py-2 text-red-200" role="alert">{error}</p>}
      {notice && <p className="rounded bg-green-900/60 px-3 py-2 text-green-200">{notice}</p>}

      <label className="block text-sm">
        Filter:
        <input className="ml-2 rounded bg-gray-700 p-1" value={filter} onChange={(e) => setFilter(e.target.value)} />
      </label>

      {loading ? (
        <p className="text-gray-400">Loading links...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-gray-400">
              <tr>
                <th className="p-2">Title</th>
                <th className="p-2">Department</th>
                <th className="p-2">Keywords</th>
                <th className="p-2">State</th>
                <th className="p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((l) => (
                <tr key={l.url} className={`border-t border-gray-700 align-top ${l.hidden ? "opacity-50" : ""}`}>
                  <td className="p-2">
                    {isOfficialPageUrl(l.url) ? (
                      <a href={l.url} target="_blank" rel="noopener noreferrer" className="text-blue-300 underline">{l.title}</a>
                    ) : (
                      <span>{l.title}</span>
                    )}
                    <span className="block break-all text-xs text-gray-500">{l.url}</span>
                  </td>
                  <td className="p-2">{DEPARTMENT_LABELS[l.department] || l.department}</td>
                  <td className="p-2 text-xs text-gray-300">{(l.keywords || []).join(", ") || "—"}</td>
                  <td className="p-2 text-xs">
                    {l.reviewed ? <span className="text-green-300">reviewed</span> : <span className="text-gray-400">not reviewed</span>}
                    {l.hidden && <span className="ml-2 text-red-300">hidden</span>}
                    <span className="block text-gray-500">{l.origin === "file" ? "catalogue file" : "changed by admin"}</span>
                  </td>
                  <td className="space-x-2 whitespace-nowrap p-2">
                    <button type="button" className="rounded bg-gray-600 px-2 py-1 text-xs hover:bg-gray-500"
                      onClick={() => save({ url: l.url, reviewed: !l.reviewed },
                        `"${l.title}" marked ${l.reviewed ? "not reviewed" : "reviewed"}.`)}>
                      {l.reviewed ? "Unmark reviewed" : "Mark reviewed"}
                    </button>
                    <button type="button" className="rounded bg-red-800 px-2 py-1 text-xs hover:bg-red-700"
                      onClick={() => save({ url: l.url, hidden: !l.hidden }, `"${l.title}" ${l.hidden ? "shown again" : "hidden"}.`)}>
                      {l.hidden ? "Show" : "Hide"}
                    </button>
                    <button type="button" className="rounded bg-gray-700 px-2 py-1 text-xs hover:bg-gray-600"
                      onClick={() => setForm({ url: l.url, title: l.title, department: l.department,
                        keywords: (l.keywords || []).join(", ") })}>
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default OfficialLinks;
