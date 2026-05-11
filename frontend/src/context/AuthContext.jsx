import { createContext, useContext, useEffect, useState } from "react";
import { authApi } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("mcp_token");
    if (!token) { setLoading(false); return; }
    authApi.me()
      .then(setUser)
      .catch(() => localStorage.removeItem("mcp_token"))
      .finally(() => setLoading(false));
  }, []);

  async function _hydrateFromToken(token) {
    localStorage.setItem("mcp_token", token);
    try {
      const me = await authApi.me();
      setUser(me);
    } catch (err) {
      // Keep the token so the user can retry or inspect the failure.
      // The caller can decide how to surface the exact backend error.
      throw err;
    }
  }

  async function login(email, password) {
    return await authApi.login(email, password);
  }

  async function loginWithToken(token) {
    await _hydrateFromToken(token);
  }

  async function register(email, password, fullName) {
    const { access_token } = await authApi.register(email, password, fullName);
    await _hydrateFromToken(access_token);
  }

  function logout() {
    localStorage.removeItem("mcp_token");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, loginWithToken, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
