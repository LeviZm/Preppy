import { NavLink } from "react-router-dom";
import { UtensilsCrossed, CalendarDays, ShoppingBasket, Sparkles, LogOut, Settings } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

const NAV = [
  { to: "/recipes",  label: "Recipes",   icon: UtensilsCrossed },
  { to: "/plan",     label: "Meal Plan", icon: CalendarDays },
  { to: "/pantry",   label: "Pantry",    icon: ShoppingBasket },
  { to: "/ai",       label: "AI",        icon: Sparkles },
  { to: "/settings", label: "Settings",  icon: Settings },
];

export function Header() {
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-20 bg-white border-b border-stone-200 shadow-sm">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between gap-4">
        <span className="font-display font-bold text-xl text-sage-700 shrink-0">Preppy</span>

        <nav className="flex items-center gap-1">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-sage-100 text-sage-700"
                    : "text-stone-500 hover:bg-stone-100 hover:text-stone-700"
                }`
              }
            >
              <Icon size={15} />
              <span className="hidden sm:inline">{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-2 shrink-0">
          {user && <span className="hidden md:block text-sm text-stone-500">{user.username}</span>}
          <button
            onClick={logout}
            className="p-1.5 rounded-lg text-stone-400 hover:text-clay-500 hover:bg-clay-400/10 transition-colors"
            title="Log out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </header>
  );
}
