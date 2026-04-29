import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { authApi } from "../lib/api";

export default function Login() {
  const { login, verifyOtp } = useAuth();
  const navigate = useNavigate();

  const [step,     setStep]     = useState("credentials"); // "credentials" | "otp"
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [otp,      setOtp]      = useState("");
  const [otpHint,  setOtpHint]  = useState("");
  const [error,    setError]    = useState("");
  const [loading,  setLoading]  = useState(false);

  async function handleCredentials(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await login(email, password);
      if (res.status === "otp_required") {
        setOtpHint(res.message);
        setStep("otp");
      }
    } catch (err) {
      setError(err?.response?.data?.detail || "Invalid email or password");
    } finally {
      setLoading(false);
    }
  }

  async function handleOtp(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await verifyOtp(email, otp.trim());
      navigate("/");
    } catch (err) {
      setError(err?.response?.data?.detail || "Invalid or expired code");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-sm">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M3 8h10M8 3v10" stroke="white" strokeWidth="2.2" strokeLinecap="round"/>
            </svg>
          </div>
          <div>
            <span className="font-semibold text-zinc-100 text-base tracking-tight">MCP Hub</span>
            <span className="block text-[9px] text-zinc-600 uppercase tracking-widest -mt-0.5">middleware</span>
          </div>
        </div>

        <div className="card p-6 space-y-5">
          {step === "credentials" ? (
            <>
              <div>
                <h1 className="text-lg font-semibold text-zinc-100">Sign in</h1>
                <p className="text-sm text-zinc-500 mt-0.5">Welcome back to MCP Hub</p>
              </div>

              {/* Social sign-in */}
              <div className="space-y-2">
                <a
                  href={authApi.googleLoginUrl()}
                  className="flex items-center justify-center gap-2.5 w-full px-4 py-2.5 rounded-lg
                             border border-zinc-700 bg-zinc-900 text-zinc-300 text-sm
                             hover:bg-zinc-800 hover:border-zinc-600 transition-colors"
                >
                  <GoogleIcon />
                  Continue with Google
                </a>
                <a
                  href={authApi.githubLoginUrl()}
                  className="flex items-center justify-center gap-2.5 w-full px-4 py-2.5 rounded-lg
                             border border-zinc-700 bg-zinc-900 text-zinc-300 text-sm
                             hover:bg-zinc-800 hover:border-zinc-600 transition-colors"
                >
                  <GitHubIcon />
                  Continue with GitHub
                </a>
              </div>

              <div className="flex items-center gap-3">
                <div className="flex-1 h-px bg-zinc-800" />
                <span className="text-xs text-zinc-600">or</span>
                <div className="flex-1 h-px bg-zinc-800" />
              </div>

              <form onSubmit={handleCredentials} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="block text-xs font-medium text-zinc-400">Email</label>
                  <input
                    type="email"
                    className="input w-full"
                    placeholder="you@example.com"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    required
                    autoFocus
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="block text-xs font-medium text-zinc-400">Password</label>
                  <input
                    type="password"
                    className="input w-full"
                    placeholder="••••••••"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                  />
                </div>

                {error && (
                  <p className="text-xs text-red-400 bg-red-950/40 border border-red-800/40 rounded-lg px-3 py-2">
                    {error}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="btn-primary w-full justify-center disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {loading ? "Checking…" : "Continue"}
                </button>
              </form>
            </>
          ) : (
            <>
              <div>
                <h1 className="text-lg font-semibold text-zinc-100">Check your email</h1>
                <p className="text-sm text-zinc-500 mt-0.5">{otpHint}</p>
              </div>

              <form onSubmit={handleOtp} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="block text-xs font-medium text-zinc-400">6-digit code</label>
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="\d{6}"
                    maxLength={6}
                    className="input w-full text-center text-xl tracking-[0.35em] font-mono"
                    placeholder="000000"
                    value={otp}
                    onChange={e => setOtp(e.target.value.replace(/\D/g, ""))}
                    required
                    autoFocus
                  />
                </div>

                {error && (
                  <p className="text-xs text-red-400 bg-red-950/40 border border-red-800/40 rounded-lg px-3 py-2">
                    {error}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={loading || otp.length !== 6}
                  className="btn-primary w-full justify-center disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {loading ? "Verifying…" : "Sign in"}
                </button>

                <button
                  type="button"
                  onClick={() => { setStep("credentials"); setOtp(""); setError(""); }}
                  className="w-full text-center text-xs text-zinc-600 hover:text-zinc-400 transition-colors py-1"
                >
                  ← Back
                </button>
              </form>
            </>
          )}

          {step === "credentials" && (
            <p className="text-center text-sm text-zinc-500">
              No account?{" "}
              <Link to="/register" className="text-blue-400 hover:text-blue-300 transition-colors">
                Create one
              </Link>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 18 18" fill="none">
      <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853"/>
      <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z" fill="#FBBC05"/>
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z" fill="#EA4335"/>
    </svg>
  );
}

function GitHubIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2C6.477 2 2 6.477 2 12c0 4.418 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.009-.868-.013-1.703-2.782.604-3.369-1.342-3.369-1.342-.454-1.155-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0 1 12 6.836a9.59 9.59 0 0 1 2.504.337c1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.202 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.163 22 16.418 22 12c0-5.523-4.477-10-10-10Z"/>
    </svg>
  );
}
