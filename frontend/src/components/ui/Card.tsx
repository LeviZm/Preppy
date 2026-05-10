interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export function Card({ children, className = "", onClick }: CardProps) {
  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-2xl border border-stone-200 shadow-sm ${onClick ? "cursor-pointer hover:shadow-md hover:border-stone-300 transition-all" : ""} ${className}`}
    >
      {children}
    </div>
  );
}
