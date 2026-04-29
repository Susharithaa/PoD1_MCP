const variants = {
  // state badges
  SAVED:              "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  HITL_PENDING:       "bg-amber-500/10  text-amber-400  border border-amber-500/20",
  FAILED:             "bg-red-500/10    text-red-400    border border-red-500/20",
  INIT:               "bg-zinc-800      text-zinc-400   border border-zinc-700",
  CLASSIFYING:        "bg-blue-500/10   text-blue-400   border border-blue-500/20",
  PARSING:            "bg-blue-500/10   text-blue-400   border border-blue-500/20",
  SCHEMA_GENERATING:  "bg-violet-500/10 text-violet-400 border border-violet-500/20",
  CONFIDENCE_SCORING: "bg-violet-500/10 text-violet-400 border border-violet-500/20",
  VALIDATING:         "bg-amber-500/10  text-amber-400  border border-amber-500/20",
  SAVING:             "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",

  // http methods
  GET:    "bg-blue-500/10   text-blue-300   border border-blue-500/20",
  POST:   "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20",
  PUT:    "bg-amber-500/10  text-amber-300  border border-amber-500/20",
  PATCH:  "bg-orange-500/10 text-orange-300 border border-orange-500/20",
  DELETE: "bg-red-500/10    text-red-300    border border-red-500/20",

  // visibility
  PRIVATE: "bg-zinc-800 text-zinc-400 border border-zinc-700",
  PUBLIC:  "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  TEAM:    "bg-blue-500/10   text-blue-400   border border-blue-500/20",

  // confidence
  HIGH:    "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  MEDIUM:  "bg-amber-500/10  text-amber-400  border border-amber-500/20",
  LOW:     "bg-red-500/10    text-red-400    border border-red-500/20",
  MISSING: "bg-red-500/15    text-red-300    border border-red-500/30",
};

export default function Badge({ label, variant, className = "" }) {
  const cls = variants[variant] || variants[label] || "bg-zinc-800 text-zinc-400 border border-zinc-700";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium font-mono ${cls} ${className}`}>
      {label}
    </span>
  );
}
