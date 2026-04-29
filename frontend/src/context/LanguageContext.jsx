import { createContext, useContext, useState, useEffect } from "react";
import en from "../i18n/en";
import ja from "../i18n/ja";

const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(
    () => localStorage.getItem("mcp-hub-lang") || "en"
  );

  useEffect(() => {
    localStorage.setItem("mcp-hub-lang", lang);
    document.documentElement.setAttribute("lang", lang);
  }, [lang]);

  function toggle() {
    setLang(l => (l === "en" ? "ja" : "en"));
  }

  return (
    <LanguageContext.Provider value={{ lang, toggle }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider");
  const { lang, toggle } = ctx;
  const dict = lang === "ja" ? ja : en;
  function t(key) {
    return dict[key] ?? key;
  }
  return { lang, toggle, t };
}
