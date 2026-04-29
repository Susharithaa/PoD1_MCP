export default function EmptyState({ icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
      {icon && (
        <div className="w-12 h-12 rounded-xl bg-zinc-800 border border-zinc-700
                        flex items-center justify-center text-zinc-500 text-xl mb-4">
          {icon}
        </div>
      )}
      <p className="text-zinc-200 font-medium mb-1">{title}</p>
      {description && (
        <p className="text-zinc-500 text-sm max-w-xs">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
