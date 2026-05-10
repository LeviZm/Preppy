import { Spinner } from "./Spinner";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: React.ReactNode;
}

const variantCls: Record<Variant, string> = {
  primary:   "bg-sage-600 text-white hover:bg-sage-700 active:bg-sage-800",
  secondary: "bg-stone-100 text-stone-700 hover:bg-stone-200 active:bg-stone-300",
  ghost:     "bg-transparent text-stone-600 hover:bg-stone-100 active:bg-stone-200",
  danger:    "bg-clay-500 text-white hover:bg-clay-600 active:bg-clay-600",
};
const sizeCls: Record<Size, string> = {
  sm: "px-3 py-1.5 text-sm rounded-lg",
  md: "px-4 py-2 text-sm rounded-xl",
  lg: "px-6 py-3 text-base rounded-xl",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  icon,
  children,
  disabled,
  className = "",
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`inline-flex items-center gap-2 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${variantCls[variant]} ${sizeCls[size]} ${className}`}
    >
      {loading ? <Spinner size="sm" /> : icon}
      {children}
    </button>
  );
}
