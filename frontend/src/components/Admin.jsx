import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PropTypes from 'prop-types'
import {
  RiDashboardLine, RiLogoutBoxLine, RiMessage2Line, RiDeleteBin6Line, RiBarChart2Line, RiFileTextLine,
  RiQuestionAnswerLine, RiGraduationCapLine, RiLinksLine, RiRouteLine, RiTeamLine, RiHistoryLine,
  RiUserStarLine, RiBuilding2Line, RiMenuLine, RiCloseLine, RiQuestionLine, RiBookOpenLine,
} from 'react-icons/ri'
import QueryAnalytics from './QueryAnalytics';
import PDFManagement from './PDFManagement';
import SourceManagement from './SourceManagement';
import EnquiryManagement from './EnquiryManagement';
import ProgrammeRequirements from './ProgrammeRequirements';
import OfficialLinks from './OfficialLinks';
import RoutingManagement from './RoutingManagement';
import DashboardOverview from './DashboardOverview';
import StaffManagement from './StaffManagement';
import AuditLog from './AuditLog';
import {
  api, clearStaffSession, getErrorMessage, getLiveRetrievalStatus, getStaffMe, getStaffProfile, saveStaffSession,
  staffLogout,
} from '../lib/api';
import SafeMarkdown from "./SafeMarkdown";
import Citations from "./Citations";

const panel = "rounded-xl border border-slate-700/70 bg-slate-800/60 p-4 md:p-6";

// Questions USIUBOT could not answer (Super Administrators). Answers become draft sources
// that are used only after review under Knowledge Sources.
function UnansweredQueries() {
  const [queries, setQueries] = useState([]);
  const [response, setResponse] = useState({});
  const [liveStatus, setLiveStatus] = useState(null);

  useEffect(() => {
    api.get("/api/unanswered-queries").then((res) => setQueries(res.data.queries)).catch(() => setQueries([]));
    getLiveRetrievalStatus().then(setLiveStatus).catch(() => setLiveStatus(null));
  }, []);

  const submit = async (id) => {
    try {
      const res = await api.post("/api/add-response", { id, response: response[id] || "" });
      setQueries((prev) => prev.filter((q) => q._id !== id));
      const emailStatus = res.data.email_notification;
      let message = "Response saved.";
      if (emailStatus === "sent") message += " The user was notified by email.";
      if (emailStatus === "failed") message += " WARNING: the email notification could not be sent; please contact the user another way.";
      message += res.data.draft_source_created
        ? " It was saved as a draft source. USIUBOT will only use it after you review and approve it under Knowledge Sources."
        : " WARNING: it could not be saved as a draft source.";
      alert(message);
    } catch (error) {
      alert(getErrorMessage(error, "Failed to submit response"));
    }
  };

  const remove = async (id) => {
    if (!window.confirm('Are you sure you want to delete this question?')) return;
    try {
      await api.delete(`/api/delete-query/${id}`);
      setQueries((prev) => prev.filter((q) => q._id !== id));
    } catch (error) {
      alert(getErrorMessage(error, "Failed to delete query"));
    }
  };

  return (
    <div className="space-y-4 text-white">
      <div>
        <h2 className="text-2xl font-bold">Unresolved chatbot questions</h2>
        <p className="mt-1 text-sm text-slate-400">
          Questions USIUBOT could not answer from approved sources. Answers you write are saved on the question and as
          draft sources; USIUBOT uses an answer only after it is approved under Knowledge Sources.
        </p>
        {liveStatus && (
          <p className="mt-1 text-xs text-slate-400">
            Live website retrieval: {liveStatus.enabled ? 'enabled' : 'disabled'} · {liveStatus.reviewed_pages ?? 0} of{' '}
            {liveStatus.catalogue_pages ?? 0} catalogue pages reviewed
          </p>
        )}
      </div>
      {queries.length === 0 && <p className="text-slate-400">No unresolved questions.</p>}
      {queries.map((query) => (
        <div key={query._id} className="rounded-xl border border-slate-700 bg-slate-900 p-4">
          <div className="flex items-start justify-between gap-2">
            <p>Q: {query.question}</p>
            <button onClick={() => remove(query._id)} className="p-1 text-red-400 hover:text-red-300" title="Delete question" aria-label="Delete question">
              <RiDeleteBin6Line size={18} />
            </button>
          </div>
          {query.department && <p className="text-xs text-slate-400">Suggested department: {query.department}</p>}
          <textarea value={response[query._id] || ""} onChange={(e) => setResponse((prev) => ({ ...prev, [query._id]: e.target.value }))}
            placeholder="Type your response" className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-800 p-2 text-white" />
          <button onClick={() => submit(query._id)} className="mt-2 rounded-lg bg-amber-400 px-4 py-1.5 font-semibold text-slate-950 hover:bg-amber-300">Submit</button>
        </div>
      ))}
    </div>
  );
}

function ChatHistoryView() {
  const [history, setHistory] = useState([]);
  useEffect(() => {
    api.get('/api/admin/chat-history').then((res) => setHistory(res.data.history)).catch(() => setHistory([]));
  }, []);
  return (
    <div className="space-y-4 text-white">
      <h2 className="text-2xl font-bold">User chat history</h2>
      {history.length === 0 && <p className="text-slate-400">No chat history from registered users yet.</p>}
      {history.map((chat) => (
        <div key={chat._id} className="rounded-xl border border-slate-700 bg-slate-900 p-4">
          <div className="mb-2 text-sm text-slate-400">{new Date(chat.timestamp).toLocaleString()} - {chat.username}</div>
          <p><span className="font-medium text-sky-300">Question: </span>{chat.question}</p>
          <div className="mt-2">
            <span className="font-medium text-emerald-300">Answer: </span>
            <SafeMarkdown className="text-white chat-response" text={chat.answer} />
            <Citations citations={chat.citations} />
          </div>
        </div>
      ))}
    </div>
  );
}

function NavButton({ active, icon: Icon, label, onClick, badge = null }) {
  return (
    <button type="button" onClick={onClick}
      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition ${
        active ? 'bg-amber-400/15 font-medium text-amber-200 ring-1 ring-amber-400/40' : 'text-slate-300 hover:bg-slate-800 hover:text-white'}`}
      aria-current={active ? 'page' : undefined}>
      <Icon className="shrink-0 text-base" aria-hidden="true" />
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {badge}
    </button>
  );
}

NavButton.propTypes = {
  active: PropTypes.bool.isRequired, icon: PropTypes.elementType.isRequired, label: PropTypes.string.isRequired,
  onClick: PropTypes.func.isRequired, badge: PropTypes.node,
};

// The USIUBOT staff dashboard. What appears depends on the signed-in person's role and departments,
// as reported by the API (/api/staff/me); the API enforces the same rules on every request.
function Admin() {
  const navigate = useNavigate();
  const [me, setMe] = useState(getStaffProfile());
  const [view, setView] = useState({ tab: 'overview' });
  const [menuOpen, setMenuOpen] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    getStaffMe()
      .then(({ staff }) => {
        saveStaffSession(null, staff);
        setMe(staff);
        if (staff.must_change_password) navigate('/admin?change-password=1');
      })
      .catch((err) => {
        if (err.response?.status !== 401) setError(getErrorMessage(err, 'Could not load your account.'));
      });
  }, [navigate]);

  const go = (tab, extra = {}) => {
    setView({ tab, ...extra, key: Date.now() });
    setMenuOpen(false);
  };

  const handleLogout = async () => {
    try {
      await staffLogout();
    } catch {
      // The session is cleared locally either way.
    }
    clearStaffSession();
    navigate('/admin');
  };

  if (!me) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">
        {error ? <p role="alert">{error}</p> : <p>Loading dashboard…</p>}
      </div>
    );
  }

  const p = me.permissions || {};
  const departments = Object.entries(me.department_labels || {});
  const openEnquiries = (filter) => (filter.department && !p.view_all_departments
    ? go('department', { department: filter.department, initial: filter })
    : go('enquiries', { initial: filter }));

  const sidebar = (
    <nav className="flex h-full flex-col gap-1 overflow-y-auto p-3" aria-label="Dashboard">
      <NavButton active={view.tab === 'overview'} icon={RiDashboardLine} label="Overview" onClick={() => go('overview')} />
      <NavButton active={view.tab === 'mine'} icon={RiUserStarLine} label="Assigned to me" onClick={() => go('mine')} />
      {p.view_all_departments && (
        <NavButton active={view.tab === 'enquiries'} icon={RiQuestionAnswerLine} label="All enquiries" onClick={() => go('enquiries')} />
      )}

      <p className="mt-4 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Departments</p>
      {departments.map(([key, label]) => (
        <NavButton key={key} active={view.tab === 'department' && view.department === key} icon={RiBuilding2Line}
          label={label} onClick={() => go('department', { department: key })} />
      ))}

      {(p.manage_sources || p.manage_programmes || p.manage_department_settings || p.view_staff_directory) && (
        <p className="mt-4 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Administration</p>
      )}
      {p.manage_sources && <NavButton active={view.tab === 'unanswered'} icon={RiQuestionLine} label="Unresolved questions" onClick={() => go('unanswered')} />}
      {p.view_staff_directory && <NavButton active={view.tab === 'staff'} icon={RiTeamLine} label={p.manage_staff ? 'Staff accounts' : 'Department staff'} onClick={() => go('staff')} />}
      {p.manage_sources && <NavButton active={view.tab === 'sources'} icon={RiBookOpenLine} label="Knowledge sources" onClick={() => go('sources')} />}
      {p.manage_programmes && <NavButton active={view.tab === 'programmes'} icon={RiGraduationCapLine} label="Programme requirements" onClick={() => go('programmes')} />}
      {p.manage_department_settings && <NavButton active={view.tab === 'routing'} icon={RiRouteLine} label={p.manage_routing ? 'Department routing' : 'Department settings'} onClick={() => go('routing')} />}
      {p.manage_sources && <NavButton active={view.tab === 'links'} icon={RiLinksLine} label="Official links" onClick={() => go('links')} />}
      {p.view_chat_history && <NavButton active={view.tab === 'chat-history'} icon={RiMessage2Line} label="Chat history" onClick={() => go('chat-history')} />}
      {p.view_chat_history && <NavButton active={view.tab === 'analytics'} icon={RiBarChart2Line} label="Question analytics" onClick={() => go('analytics')} />}
      {p.manage_sources && <NavButton active={view.tab === 'pdfs'} icon={RiFileTextLine} label="PDF management (legacy)" onClick={() => go('pdfs')} />}
      {p.view_audit_log && <NavButton active={view.tab === 'audit'} icon={RiHistoryLine} label="System activity" onClick={() => go('audit')} />}
    </nav>
  );

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-slate-800 bg-slate-950/95 px-4 backdrop-blur">
        <button type="button" className="rounded p-1 text-slate-300 hover:bg-slate-800 md:hidden" onClick={() => setMenuOpen((v) => !v)}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'} aria-expanded={menuOpen}>
          {menuOpen ? <RiCloseLine size={22} /> : <RiMenuLine size={22} />}
        </button>
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-900 text-sm font-bold text-amber-300 ring-1 ring-amber-400/60">U</span>
          <div className="leading-tight">
            <p className="text-sm font-semibold">USIUBOT Staff Dashboard</p>
            <p className="hidden text-xs text-slate-400 sm:block">USIU-Africa enquiry management</p>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <div className="hidden text-right text-xs sm:block">
            <p className="font-medium text-slate-200">{me.name || me.email}</p>
            <p className="text-slate-400">{me.role_label}</p>
          </div>
          <button type="button" onClick={handleLogout} className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800">
            <RiLogoutBoxLine aria-hidden="true" /> Sign out
          </button>
        </div>
      </header>

      <aside className={`fixed bottom-0 left-0 top-14 z-20 w-64 border-r border-slate-800 bg-slate-950 transition-transform md:translate-x-0 ${menuOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        {sidebar}
      </aside>
      {menuOpen && <div className="fixed inset-0 top-14 z-10 bg-black/50 md:hidden" onClick={() => setMenuOpen(false)} aria-hidden="true" />}

      <main className="p-4 md:ml-64 md:p-8">
        {error && <p className="mb-4 rounded-lg bg-red-900/50 p-3 text-red-200" role="alert">{error}</p>}
        {view.tab === 'overview' && <DashboardOverview key={view.key} me={me} onOpenEnquiries={openEnquiries} />}
        {view.tab === 'mine' && <div className={panel}><EnquiryManagement key={view.key} me={me} mine /></div>}
        {view.tab === 'enquiries' && <div className={panel}><EnquiryManagement key={view.key} me={me} initial={view.initial} /></div>}
        {view.tab === 'department' && (
          <div className={panel}><EnquiryManagement key={view.key} me={me} department={view.department} initial={view.initial} /></div>
        )}
        {view.tab === 'unanswered' && <div className={panel}><UnansweredQueries /></div>}
        {view.tab === 'staff' && <div className={panel}><StaffManagement me={me} /></div>}
        {view.tab === 'audit' && <div className={panel}><AuditLog /></div>}
        {view.tab === 'chat-history' && <div className={panel}><ChatHistoryView /></div>}
        {view.tab === 'analytics' && <QueryAnalytics />}
        {view.tab === 'programmes' && <div className={panel}><ProgrammeRequirements /></div>}
        {view.tab === 'links' && <div className={panel}><OfficialLinks /></div>}
        {view.tab === 'routing' && <div className={panel}><RoutingManagement /></div>}
        {view.tab === 'sources' && <div className={panel}><SourceManagement /></div>}
        {view.tab === 'pdfs' && <div className={panel}><PDFManagement /></div>}
      </main>
    </div>
  )
}

export default Admin
