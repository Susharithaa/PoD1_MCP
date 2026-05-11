import { useState } from "react";
import { useLanguage } from "../context/LanguageContext";
import ChatBuilder from "./ChatBuilder";
import DocUpload from "./DocUpload";

export default function McpOnboarding() {
  const { t } = useLanguage();
  const [selected, setSelected] = useState(null); // null | "manual" | "automatic"

  return (
    <div className="animate-slide-up">
      <div className="mb-8">
        <p className="eyebrow">{t("Register")}</p>
        <h1 className="h-page mt-2">{t("MCP Onboarding")}</h1>
        <p className="lead mt-2">
          {t("Choose how to register your API as an MCP tool. Use Manual for full control over endpoints, or Automatic to parse an existing API spec or document.")}
        </p>
      </div>

      {/* Choice cards */}
      <div className="grid grid-cols-2 gap-5 mb-8">
        <button
          onClick={() => setSelected(selected === "manual" ? null : "manual")}
          className={`card p-6 text-left flex flex-col gap-4 transition-all
            ${selected === "manual"
              ? "border-[var(--ink)] ring-1 ring-[var(--ink)]"
              : "hover:border-[var(--muted)] cursor-pointer"}`}
        >
          <div className={`w-12 h-12 rounded-xl border flex items-center justify-center transition-colors
            ${selected === "manual"
              ? "bg-[var(--ink)] border-[var(--ink)] text-[var(--bg)]"
              : "bg-[var(--surface)] border-[var(--line)] text-[var(--muted)]"}`}>
            <FormIcon />
          </div>
          <div className="flex-1">
            <h2 className="text-base font-semibold text-[var(--ink)]">{t("Manual")}</h2>
            <p className="text-sm text-[var(--muted)] mt-1.5 leading-relaxed">
              {t("Define endpoints, parameters, and auth manually using the guided form. Ideal when you know your API structure.")}
            </p>
          </div>
          {selected === "manual" && (
            <span className="text-xs text-[var(--muted)] font-medium">{t("Selected")} ↓</span>
          )}
        </button>

        <button
          onClick={() => setSelected(selected === "automatic" ? null : "automatic")}
          className={`card p-6 text-left flex flex-col gap-4 transition-all
            ${selected === "automatic"
              ? "border-[var(--ink)] ring-1 ring-[var(--ink)]"
              : "hover:border-[var(--muted)] cursor-pointer"}`}
        >
          <div className={`w-12 h-12 rounded-xl border flex items-center justify-center transition-colors
            ${selected === "automatic"
              ? "bg-[var(--ink)] border-[var(--ink)] text-[var(--bg)]"
              : "bg-[var(--surface)] border-[var(--line)] text-[var(--muted)]"}`}>
            <UploadIcon />
          </div>
          <div className="flex-1">
            <h2 className="text-base font-semibold text-[var(--ink)]">{t("Automatic")}</h2>
            <p className="text-sm text-[var(--muted)] mt-1.5 leading-relaxed">
              {t("Upload an OpenAPI spec, YAML, PDF, or plain text and let the system parse endpoints and schema automatically.")}
            </p>
          </div>
          {selected === "automatic" && (
            <span className="text-xs text-[var(--muted)] font-medium">{t("Selected")} ↓</span>
          )}
        </button>
      </div>

      {/* Inline form */}
      {selected === "manual" && (
        <div className="border-t border-[var(--line)] pt-8 animate-slide-up">
          <ChatBuilder embedded />
        </div>
      )}
      {selected === "automatic" && (
        <div className="border-t border-[var(--line)] pt-8 animate-slide-up">
          <DocUpload embedded />
        </div>
      )}
    </div>
  );
}

function FormIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="1.6"/>
      <path d="M7 8h10M7 12h10M7 16h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path d="M12 15V3M8 7l4-4 4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  );
}
