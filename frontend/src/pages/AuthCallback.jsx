import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const { loginWithToken } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");

  useEffect(() => {
    const token = searchParams.get("token");
    const err   = searchParams.get("error");

    if (err) {
      const messages = {
        google_denied: "Google sign-in was cancelled.",
        google_failed: "Google sign-in failed. Please try again.",
        github_denied: "GitHub sign-in was cancelled.",
        github_failed: "GitHub sign-in failed. Please try again.",
        no_email:      "Could not retrieve your email address from the provider.",
      };
      setError(messages[err] || "Sign-in failed. Please try again.");
      return;
    }

    if (!token) {
      setError("No token received. Please try signing in again.");
      return;
    }

    loginWithToken(token)
      .then(() => navigate("/", { replace: true }))
      .catch(() => setError("Failed to complete sign-in. Please try again."));
  }, []);

  if (error) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center px-4">
        <div className="w-full max-w-sm card p-6 space-y-4 text-center">
          <div className="w-10 h-10 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto">
            <svg width="18" height="18" viewBox="0 0 15 15" fill="none">
              <path d="M7.5 2v6M7.5 11v1" stroke="#f87171" strokeWidth="1.6" strokeLinecap="round"/>
            </svg>
          </div>
          <div>
            <p className="text-sm font-medium text-zinc-200">Sign-in error</p>
            <p className="text-xs text-zinc-500 mt-1">{error}</p>
          </div>
          <a href="/login" className="btn-primary inline-flex justify-center w-full text-sm">
            Back to sign in
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center animate-pulse">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M3 8h10M8 3v10" stroke="white" strokeWidth="2.2" strokeLinecap="round"/>
          </svg>
        </div>
        <p className="text-sm text-zinc-400">Completing sign-in…</p>
      </div>
    </div>
  );
}
