import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { RiShieldUserLine } from "react-icons/ri";
import {
  changeStaffPassword,
  clearStaffSession,
  getErrorMessage,
  getStaffProfile,
  saveStaffSession,
  staffLogin,
} from "../lib/api";

const inputClass =
  "mt-1 block w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white placeholder-slate-500 " +
  "focus:border-amber-400 focus:outline-none focus:ring-2 focus:ring-amber-400/40";

// Sign-in for authorised USIU-Africa staff (all roles). There is no public registration:
// accounts are created by a Super Administrator. A temporary password must be changed
// before the dashboard can be used (the API enforces this too).
function LoginAdmin() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const pendingProfile = getStaffProfile();
  const [step, setStep] = useState(
    params.get("change-password") && pendingProfile?.must_change_password ? "password" : "login");
  const [form, setForm] = useState({ email: "", password: "" });
  const [pw, setPw] = useState({ current: "", next: "", repeat: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const data = await staffLogin({ email: form.email, password: form.password });
      saveStaffSession(data.token, data.staff);
      if (data.staff?.must_change_password) {
        setPw({ current: form.password, next: "", repeat: "" });
        setStep("password");
      } else {
        navigate("/admin/dashboard");
      }
    } catch (err) {
      setError(getErrorMessage(err, "Sign-in failed. Please try again."));
    } finally {
      setBusy(false);
    }
  };

  const handlePassword = async (e) => {
    e.preventDefault();
    setError("");
    if (pw.next !== pw.repeat) {
      setError("The new passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const data = await changeStaffPassword({ current_password: pw.current, new_password: pw.next });
      saveStaffSession(null, data.staff);
      navigate("/admin/dashboard");
    } catch (err) {
      setError(getErrorMessage(err, "The password could not be changed."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-900 ring-2 ring-amber-400/70">
            <RiShieldUserLine className="text-4xl text-amber-300" aria-hidden="true" />
          </div>
          <h1 className="mt-4 text-2xl font-bold text-white">USIUBOT Staff Portal</h1>
          <p className="mt-1 text-sm text-slate-400">USIU-Africa enquiry management · authorised personnel only</p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl">
          {step === "login" ? (
            <form className="space-y-4" onSubmit={handleLogin}>
              <h2 className="text-lg font-semibold text-white">Sign in</h2>
              <label className="block text-sm text-slate-300">
                Work email
                <input type="email" required autoComplete="username" className={inputClass} value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </label>
              <label className="block text-sm text-slate-300">
                Password
                <input type="password" required autoComplete="current-password" className={inputClass}
                  value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
              </label>
              {error && <p className="rounded-lg bg-red-900/50 px-3 py-2 text-sm text-red-200" role="alert">{error}</p>}
              <button type="submit" disabled={busy}
                className="w-full rounded-lg bg-amber-400 px-4 py-2 font-semibold text-slate-950 hover:bg-amber-300 disabled:opacity-60">
                {busy ? "Signing in…" : "Sign in"}
              </button>
              <p className="text-xs text-slate-500">
                No account? Staff accounts are created by the USIUBOT Super Administrator. Sessions end
                automatically after a few hours.
              </p>
            </form>
          ) : (
            <form className="space-y-4" onSubmit={handlePassword}>
              <h2 className="text-lg font-semibold text-white">Choose your own password</h2>
              <p className="text-sm text-slate-400">
                You signed in with a temporary password. Choose a new one (at least 10 characters, with letters
                and numbers) to continue.
              </p>
              <label className="block text-sm text-slate-300">
                Current (temporary) password
                <input type="password" required autoComplete="current-password" className={inputClass}
                  value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} />
              </label>
              <label className="block text-sm text-slate-300">
                New password
                <input type="password" required minLength={10} autoComplete="new-password" className={inputClass}
                  value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} />
              </label>
              <label className="block text-sm text-slate-300">
                Repeat new password
                <input type="password" required minLength={10} autoComplete="new-password" className={inputClass}
                  value={pw.repeat} onChange={(e) => setPw({ ...pw, repeat: e.target.value })} />
              </label>
              {error && <p className="rounded-lg bg-red-900/50 px-3 py-2 text-sm text-red-200" role="alert">{error}</p>}
              <button type="submit" disabled={busy}
                className="w-full rounded-lg bg-amber-400 px-4 py-2 font-semibold text-slate-950 hover:bg-amber-300 disabled:opacity-60">
                {busy ? "Saving…" : "Save password and continue"}
              </button>
              <button type="button" onClick={() => { clearStaffSession(); setStep("login"); }}
                className="w-full text-sm text-slate-400 underline hover:text-slate-200">
                Cancel and sign out
              </button>
            </form>
          )}
        </div>
        <button type="button" onClick={() => navigate("/")}
          className="mt-4 w-full text-center text-sm text-slate-400 hover:text-white">
          ← Back to the USIUBOT assistant
        </button>
      </div>
    </div>
  );
}

export default LoginAdmin;
