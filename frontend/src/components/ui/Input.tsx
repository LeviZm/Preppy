interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, id, className = "", ...rest }: InputProps) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-stone-700">
          {label}
        </label>
      )}
      <input
        id={id}
        {...rest}
        className={`w-full px-3 py-2 rounded-xl border ${error ? "border-clay-500" : "border-stone-300"} bg-white text-stone-800 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-sage-400 focus:border-transparent transition ${className}`}
      />
      {error && <p className="text-xs text-clay-500">{error}</p>}
    </div>
  );
}

interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export function TextArea({ label, error, id, className = "", ...rest }: TextAreaProps) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-stone-700">
          {label}
        </label>
      )}
      <textarea
        id={id}
        {...rest}
        className={`w-full px-3 py-2 rounded-xl border ${error ? "border-clay-500" : "border-stone-300"} bg-white text-stone-800 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-sage-400 focus:border-transparent transition resize-none ${className}`}
      />
      {error && <p className="text-xs text-clay-500">{error}</p>}
    </div>
  );
}
