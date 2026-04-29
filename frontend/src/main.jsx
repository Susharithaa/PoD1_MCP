import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import "./index.css";

import App           from "./App";
import Home          from "./pages/Home";
import ChatBuilder   from "./pages/ChatBuilder";
import DocUpload     from "./pages/DocUpload";
import HITLValidator from "./pages/HITLValidator";
import Registry      from "./pages/Registry";
import ToolDetail    from "./pages/ToolDetail";
import ChatGPTHub    from "./pages/ChatGPTHub";
import Monitor       from "./pages/Monitor";
import Admin         from "./pages/Admin";
import Login         from "./pages/Login";
import Register      from "./pages/Register";
import AuthCallback  from "./pages/AuthCallback";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";

const router = createBrowserRouter([
  { path: "/login",         element: <Login /> },
  { path: "/register",      element: <Register /> },
  { path: "/auth/callback", element: <AuthCallback /> },
  {
    path: "/",
    element: <ProtectedRoute><App /></ProtectedRoute>,
    children: [
      { index: true,                 element: <Home /> },
      { path: "create/chat",         element: <ChatBuilder /> },
      { path: "create/upload",       element: <DocUpload /> },
      { path: "validate/:sessionId", element: <HITLValidator /> },
      { path: "registry",            element: <Registry /> },
      { path: "registry/:id",        element: <ToolDetail /> },
      { path: "chatgpt",             element: <ChatGPTHub /> },
      { path: "monitor",             element: <Monitor /> },
      { path: "admin",               element: <Admin /> },
    ],
  },
]);

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  </StrictMode>
);
