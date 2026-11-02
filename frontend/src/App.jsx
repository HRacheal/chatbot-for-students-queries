import { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import ChatButton from "./components/ChatButton";
import ChatBox from "./components/ChatBox";
import LoginAdmin from './components/LoginAdmin';
import Admin from './components/Admin';
import UserLogin from './components/UserLogin';
import UserSignUp from './components/UserSignUp';
import PropTypes from "prop-types";
import { RiChatSmile3Line, RiGraduationCapLine, RiShieldCheckLine, RiCustomerService2Line } from "react-icons/ri";

// A staff session exists (the backend re-checks the token, role and department on every request).
const isStaffAuthenticated = () => localStorage.getItem('adminToken') !== null;

// Protected Route Component
const ProtectedRoute = ({ children, authCheck, redirectTo = "/admin" }) => {
  if (!authCheck()) {
    return <Navigate to={redirectTo} replace />;
  }
  return children;
};

ProtectedRoute.propTypes = {
  children: PropTypes.node.isRequired,
  authCheck: PropTypes.func.isRequired,
  redirectTo: PropTypes.string,
};

const AUDIENCES = [
  "Current students", "Prospective students", "Parents and guardians", "Faculty members",
  "University administrators and staff",
];
const TOPICS = [
  "Admissions and applications", "Academic programmes", "Fees and payments", "Registration and the academic calendar",
  "Academic administration (transcripts, exams)", "Campus services and student affairs", "ICT and library services",
];

function Landing({ onOpenChat }) {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <div className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-900 font-bold text-amber-300 ring-1 ring-amber-400/60">U</span>
          <span className="font-semibold">USIUBOT</span>
        </div>
        <Link to="/admin" className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800">
          Staff sign-in
        </Link>
      </header>

      <main className="mx-auto max-w-6xl px-4 pb-32">
        <section className="py-10 md:py-16">
          <p className="text-sm font-medium uppercase tracking-wider text-amber-300">United States International University – Africa</p>
          <h1 className="mt-2 max-w-3xl text-3xl font-bold leading-tight md:text-5xl">
            Ask USIUBOT about USIU-Africa — any time.
          </h1>
          <p className="mt-4 max-w-2xl text-slate-300">
            Answers come only from approved USIU-Africa sources and show where the information came from.
            When USIUBOT cannot answer reliably, it says so and lets you send your question to the right
            university office.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <button type="button" onClick={onOpenChat}
              className="flex items-center gap-2 rounded-lg bg-amber-400 px-5 py-2.5 font-semibold text-slate-950 hover:bg-amber-300">
              <RiChatSmile3Line aria-hidden="true" /> Start a conversation
            </button>
            <span className="self-center text-xs text-slate-500">or press Ctrl + /</span>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Available 24 hours a day, subject to service availability. No sign-in is needed for ordinary questions.
          </p>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <RiShieldCheckLine className="text-2xl text-amber-300" aria-hidden="true" />
            <h2 className="mt-2 font-semibold">Cited, official answers</h2>
            <p className="mt-1 text-sm text-slate-400">
              Every answer links to its supporting source. Information from outside bodies (for example KUCCPS)
              is labelled as external and never presented as USIU-Africa policy.
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <RiCustomerService2Line className="text-2xl text-amber-300" aria-hidden="true" />
            <h2 className="mt-2 font-semibold">Human follow-up</h2>
            <p className="mt-1 text-sm text-slate-400">
              If USIUBOT cannot verify an answer, you can send an enquiry to the relevant department and track it
              with a reference number.
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <RiGraduationCapLine className="text-2xl text-amber-300" aria-hidden="true" />
            <h2 className="mt-2 font-semibold">Programme guidance</h2>
            <p className="mt-1 text-sm text-slate-400">
              Prospective students can check results-slip grades against verified entry requirements (open the
              assistant and choose &quot;Degree guidance&quot;). Guidance only — never an admission decision.
            </p>
          </div>
        </section>

        <section className="mt-10 grid gap-6 md:grid-cols-2">
          <div>
            <h2 className="font-semibold text-slate-200">Who USIUBOT helps</h2>
            <ul className="mt-2 flex flex-wrap gap-2">
              {AUDIENCES.map((a) => <li key={a} className="rounded-full bg-slate-800 px-3 py-1 text-sm text-slate-300">{a}</li>)}
            </ul>
          </div>
          <div>
            <h2 className="font-semibold text-slate-200">What you can ask about</h2>
            <ul className="mt-2 flex flex-wrap gap-2">
              {TOPICS.map((t) => <li key={t} className="rounded-full bg-slate-800 px-3 py-1 text-sm text-slate-300">{t}</li>)}
            </ul>
          </div>
        </section>
        <p className="mt-10 text-xs text-slate-500">
          USIUBOT answers questions about USIU-Africa only. It does not make admission decisions or change university
          records. For official confirmation, contact the office concerned.
        </p>
      </main>
    </div>
  );
}

Landing.propTypes = { onOpenChat: PropTypes.func.isRequired };

function App() {
  const [isChatOpen, setIsChatOpen] = useState(false);

  useEffect(() => {
    const handleKeyPress = (event) => {
      // Toggle chat with Ctrl + /
      if (event.ctrlKey && event.key === '/') {
        event.preventDefault();
        setIsChatOpen(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);

  return (
    <Router>
      <Routes>
        {/* Public assistant */}
        <Route path="/" element={
          <div className="relative">
            <Landing onOpenChat={() => setIsChatOpen(true)} />
            {isChatOpen && <ChatBox onClose={() => setIsChatOpen(false)} />}
            {!isChatOpen && (
              <div onClick={() => setIsChatOpen(true)}>
                <ChatButton />
              </div>
            )}
          </div>
        } />

        {/* Optional accounts for public users (chat history, enquiry tracking) */}
        <Route path="/login" element={<UserLogin />} />
        <Route path="/signup" element={<UserSignUp />} />

        {/* Staff dashboard (no public staff registration) */}
        <Route path="/admin" element={<LoginAdmin />} />
        <Route
          path="/admin/dashboard"
          element={
            <ProtectedRoute authCheck={isStaffAuthenticated}>
              <Admin />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
