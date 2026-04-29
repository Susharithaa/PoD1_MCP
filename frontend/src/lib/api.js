import axios from "axios";

const http = axios.create({ baseURL: "http://localhost:8000" });

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
  verifyOtp: (email, otp) =>
    http.post("/api/auth/verify-otp", { email, otp }).then(r => r.data),
  me: () => http.get("/api/auth/me").then(r => r.data),
  googleLoginUrl:    () => "http://localhost:8000/api/auth/google",
  githubLoginUrl: () => "http://localhost:8000/api/auth/github",
};

export const adminApi = {
  listUsers:    ()               => http.get("/api/auth/admin/users").then(r => r.data),
  updateRole:   (id, role)       => http.patch(`/api/auth/admin/users/${id}/role`, { role }).then(r => r.data),
  setActive:    (id, isActive)   => http.patch(`/api/auth/admin/users/${id}/active`, { is_active: isActive }).then(r => r.data),
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
  updateAuth:     (id, authType) => http.patch(`/api/registry/${id}/auth`, { auth_type: authType }).then(r => r.data),
  delete:         (id)           => http.delete(`/api/registry/${id}`),
  createEndpoint: (id, data)     => http.post(`/api/registry/${id}/endpoints`, data).then(r => r.data),
  updateEndpoint: (id, epId, data) => http.put(`/api/registry/${id}/endpoints/${epId}`, data).then(r => r.data),
  deleteEndpoint: (id, epId)     => http.delete(`/api/registry/${id}/endpoints/${epId}`),
};

export const monitorApi = {
  overview:   () => http.get("/api/monitor/overview").then(r => r.data),
  active:     () => http.get("/api/monitor/active").then(r => r.data),
  sessions:   (limit = 30) => http.get(`/api/monitor/sessions?limit=${limit}`).then(r => r.data),
  toolCalls:  (limit = 30) => http.get(`/api/monitor/tool-calls?limit=${limit}`).then(r => r.data),
  pipeline:   () => http.get("/api/monitor/pipeline").then(r => r.data),
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
  getStats:    ()      => http.get("/api/chatgpt/stats").then((r) => r.data),
  getRegistry: ()      => http.get("/api/chatgpt/registry").then((r) => r.data),
  connect:     (id)    => http.post(`/api/chatgpt/connect/${id}`).then((r) => r.data),
  disconnect:  (id)    => http.delete(`/api/chatgpt/disconnect/${id}`).then((r) => r.data),
  getTools:    (id)    => http.get(`/api/chatgpt/tools/${id}`).then((r) => r.data),
  chat:        (message, api_ids = [], session_id = null) =>
    http.post("/api/chatgpt/chat", { message, api_ids, session_id }).then((r) => r.data),
};
