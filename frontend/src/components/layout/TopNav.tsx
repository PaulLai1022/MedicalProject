import { Link, NavLink, useNavigate } from "react-router-dom";
import { Stethoscope, FileText, LogOut, Plus } from "lucide-react";
import { useAuthStore } from "@/store/authStore";

export function TopNav() {
  const { user, clearAuth } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    clearAuth();
    navigate("/login");
  };

  return (
    <header className="sticky top-0 z-40 border-b border-ink-100 glass">
      <nav className="mx-auto flex h-14 w-full max-w-[1280px] items-center justify-between px-6 lg:px-10">
        <div className="flex items-center gap-1">
          <Link
            to="/"
            className="flex items-center gap-2 rounded-lg px-2 py-1 text-ink-900 transition-colors duration-200 ease-ios hover:bg-ink-100"
          >
            <span className="grid h-7 w-7 place-items-center rounded-lg bg-brand-600 text-white shadow-soft">
              <Stethoscope size={16} strokeWidth={2.25} />
            </span>
            <span className="font-display text-[17px] font-semibold tracking-tight">
              Clinical Notes
            </span>
          </Link>

          <div className="ml-4 hidden items-center gap-1 sm:flex">
            <NavItem to="/" end label="New" icon={<Plus size={15} />} />
            <NavItem to="/cases" label="Cases" icon={<FileText size={15} />} />
          </div>
        </div>

        <div className="flex items-center gap-3">
          {user && (
            <div className="hidden items-center gap-2 rounded-full bg-ink-100/70 py-1 pl-1 pr-3 sm:flex">
              <span className="grid h-7 w-7 place-items-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-[12px] font-semibold text-white">
                {user.email.slice(0, 1).toUpperCase()}
              </span>
              <span className="text-[13px] text-ink-600">{user.email}</span>
            </div>
          )}
          <button
            onClick={handleLogout}
            aria-label="Sign Out"
            className="grid h-9 w-9 place-items-center rounded-full text-ink-500 transition-all duration-200 ease-ios hover:bg-admit-50 hover:text-admit-600"
          >
            <LogOut size={16} />
          </button>
        </div>
      </nav>
    </header>
  );
}

function NavItem({
  to,
  label,
  icon,
  end,
}: {
  to: string;
  label: string;
  icon: React.ReactNode;
  end?: boolean;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        [
          "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[13px] font-medium transition-all duration-200 ease-ios",
          isActive
            ? "bg-brand-50 text-brand-700"
            : "text-ink-600 hover:bg-ink-100 hover:text-ink-900",
        ].join(" ")
      }
    >
      {icon}
      {label}
    </NavLink>
  );
}
