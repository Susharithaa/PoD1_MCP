import axios from "axios";

const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ||
  `${window.location.protocol}//${window.location.hostname}:8000`;

const http = axios.create({ baseURL: apiBaseUrl });

http.interceptors.request.use(config => {
  const token = localStorage.getItem("mcp_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

http.interceptors.response.use(
  r => r,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem("mcp_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const authApi = {
  register: (email, password, fullName) =>
    http.post("/api/auth/register", { email, password, full_name: fullName }).then(r => r.data),
  login: (email, password) =>
    http.post("/api/auth/login", { email, password }).then(r => r.data),
  me: () => http.get("/api/auth/me").then(r => r.data),
  googleLoginUrl:    () => `${apiBaseUrl}/api/auth/google`,
  githubLoginUrl: () => `${apiBaseUrl}/api/auth/github`,
};

export const adminApi = {
  listUsers:    ()               => http.get("/api/auth/admin/users").then(r => r.data),
  updateRole:   (id, role)       => http.patch(`/api/auth/admin/users/${id}/role`, { role }).then(r => r.data),
  setActive:    (id, isActive)   => http.patch(`/api/auth/admin/users/${id}/active`, { is_active: isActive }).then(r => r.data),
};

export const adminOpsApi = {
  audit:       (limit = 100) => http.get(`/api/admin/audit?limit=${limit}`).then(r => r.data),
  liveLogs:    (limit = 100) => http.get(`/api/admin/logs/live?limit=${limit}`).then(r => r.data),
  costs:       ()            => http.get("/api/admin/llm-costs").then(r => r.data),
  incidents:   ()            => http.get("/api/admin/incidents").then(r => r.data),
  aggregate:   ()            => http.post("/api/admin/incidents/aggregate").then(r => r.data),
  plugins:     ()            => http.get("/api/admin/plugins").then(r => r.data),
  savePlugin:  (name, data)  => http.put(`/api/admin/plugins/${name}`, data).then(r => r.data),
  rbac:        ()            => http.get("/api/admin/rbac").then(r => r.data),
  saveRbac:    (data)        => http.put("/api/admin/rbac", data).then(r => r.data),
  exportConfig: ()           => http.get("/api/admin/config/export").then(r => r.data),
  importConfig: (data)       => http.post("/api/admin/config/import", data).then(r => r.data),
};

export const securityApi = {
  listTokens:   ()             => http.get("/api/security/tokens").then(r => r.data),
  createToken:  (name, scopes) => http.post("/api/security/tokens", { name, scopes }).then(r => r.data),
  rotateToken:  (id)           => http.post(`/api/security/tokens/${id}/rotate`).then(r => r.data),
  revokeToken:  (id)           => http.delete(`/api/security/tokens/${id}`),
};

export const agentApi = {
  startChat: (message) =>
    http.post("/api/agent/chat", { message }).then((r) => r.data),

  startUpload: (file) => {
    const form = new FormData();
    form.append("file", file);
    return http.post("/api/agent/upload", form).then((r) => r.data);
  },

  getSession: (id) => http.get(`/api/agent/${id}`).then((r) => r.data),

  submitHITL: (id, edits, authCredentials = null, saveAnyway = false) =>
    http.post(`/api/agent/${id}/hitl`, { edits, auth_credentials: authCredentials, save_anyway: saveAnyway }).then((r) => r.data),

  confirm: (id) =>
    http.post(`/api/agent/${id}/confirm`).then((r) => r.data),

  discard: (id) =>
    http.post(`/api/agent/${id}/discard`).then((r) => r.data),

  restart: (id) =>
    http.post(`/api/agent/${id}/restart`).then((r) => r.data),

  patchDraft: (id, partial) =>
    http.patch(`/api/agent/${id}/draft`, partial).then((r) => r.data),

  listSessions: () => http.get("/api/agent/").then((r) => r.data),

  manual: (data) =>
    http.post("/api/agent/manual", data).then((r) => r.data),
};

export const registryApi = {
  list:           ()             => http.get("/api/registry/").then(r => r.data),
  get:            (id)           => http.get(`/api/registry/${id}`).then(r => r.data),
  update:         (id, data)     => http.patch(`/api/registry/${id}`, data).then(r => r.data),
  updateAuth:     (id, authType, authCreds) => http.patch(`/api/registry/${id}/auth`, { auth_type: authType, auth_credentials: authCreds || null }).then(r => r.data),
  delete:         (id)           => http.delete(`/api/registry/${id}`),
  createEndpoint: (id, data)     => http.post(`/api/registry/${id}/endpoints`, data).then(r => r.data),
  updateEndpoint: (id, epId, data) => http.put(`/api/registry/${id}/endpoints/${epId}`, data).then(r => r.data),
  deleteEndpoint: (id, epId)     => http.delete(`/api/registry/${id}/endpoints/${epId}`),
};

export const monitorApi = {
  overview:       () => http.get("/api/monitor/overview").then(r => r.data),
  active:         () => http.get("/api/monitor/active").then(r => r.data),
  sessions:       (limit = 30) => http.get(`/api/monitor/sessions?limit=${limit}`).then(r => r.data),
  toolCalls:      (limit = 30) => http.get(`/api/monitor/tool-calls?limit=${limit}`).then(r => r.data),
  audit:          (limit = 50) => http.get(`/api/monitor/audit?limit=${limit}`).then(r => r.data),
  pipeline:       () => http.get("/api/monitor/pipeline").then(r => r.data),
  apiToolCalls:   (apiId, limit = 20) => http.get(`/api/monitor/api-tool-calls/${apiId}?limit=${limit}`).then(r => r.data),
};

export const subscriptionApi = {
  requestAccess: ()             => http.post("/api/subscription/request").then(r => r.data),
  getStatus:     ()             => http.get("/api/subscription/status").then(r => r.data),
  adminRequests: ()             => http.get("/api/subscription/admin/requests").then(r => r.data),
  adminAllUsers: ()             => http.get("/api/subscription/admin/all-users").then(r => r.data),
  approve:       (userId)       => http.patch(`/api/subscription/admin/${userId}/approve`).then(r => r.data),
  reject:        (userId)       => http.patch(`/api/subscription/admin/${userId}/reject`).then(r => r.data),
  topUp:         (userId, amt)  => http.post(`/api/subscription/admin/${userId}/top-up`, { amount: amt }).then(r => r.data),
};

export const chatgptApi = {
  getStats:     ()             => http.get("/api/chatgpt/stats").then((r) => r.data),
  getRegistry:  ()             => http.get("/api/chatgpt/registry").then((r) => r.data),
  listSessions: (limit = 20)   => http.get(`/api/chatgpt/sessions?limit=${limit}`).then((r) => r.data),
  connect:      (id)           => http.post(`/api/chatgpt/connect/${id}`).then((r) => r.data),
  disconnect:   (id)           => http.delete(`/api/chatgpt/disconnect/${id}`).then((r) => r.data),
  getSession:   (id)           => http.get(`/api/chatgpt/session/${id}`).then((r) => r.data),
  clearSession: (id)           => http.delete(`/api/chatgpt/session/${id}`).then((r) => r.data),
  getTools:     (id)           => http.get(`/api/chatgpt/tools/${id}`).then((r) => r.data),
  chat:         (message, api_ids = [], session_id = null, dry_run = false) =>
    http.post("/api/chatgpt/chat", { message, api_ids, session_id, dry_run }).then((r) => r.data),
};

export const domainApi = {
  appInfo:       () => http.get("/api/domain/application-info").then(r => r.data),
  listReports:   () => http.get("/api/domain/expense-reports").then(r => r.data),
  createReport:  (data) => http.post("/api/domain/expense-reports", data).then(r => r.data),
  listFiles:     () => http.get("/api/domain/files").then(r => r.data),
  downloadFile:  (url) => http.post(`/api/domain/file-download?url=${encodeURIComponent(url)}`).then(r => r.data),
};

export const systemApi = {
  controls:     () => http.get("/api/admin/system-controls").then(r => r.data),
  saveControls: (data) => http.put("/api/admin/system-controls", data).then(r => r.data),
};
