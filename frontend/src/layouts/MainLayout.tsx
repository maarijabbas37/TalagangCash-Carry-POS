import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

interface NavItem {
  to: string;
  label: string;
  icon: string;
  ownerOnly?: boolean;
}

// Section 2 of the blueprint: employees never see modules they don't need.
// Phase 1 only wires up POS (placeholder) and Products; the rest of the
// nav is scaffolded here so later phases just add routes, not this shell.
const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "POS", icon: "🧾" },
  { to: "/products", label: "Products", icon: "📦" },
  { to: "/users", label: "Users", icon: "👥", ownerOnly: true },
];

export function MainLayout() {
  const { user, logout } = useAuth();

  const visibleItems = NAV_ITEMS.filter((item) => !item.ownerOnly || user?.role === "OWNER");

  return (
    <div className="min-h-screen flex bg-gray-50">
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-4 py-5 border-b border-gray-200">
          <h1 className="font-bold text-sm leading-tight">TALAGANG CASH &amp; CARRY</h1>
        </div>
        <nav className="flex-1 py-2">
          {visibleItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-2 px-4 py-2.5 text-sm font-medium ${
                  isActive
                    ? "bg-brand-50 text-brand-700 border-r-2 border-brand-600"
                    : "text-gray-600 hover:bg-gray-50"
                }`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-gray-200 text-xs text-gray-500">
          <div className="font-medium text-gray-700">{user?.full_name}</div>
          <div>
            {user?.role} · {user?.default_counter?.name ?? "No counter"}
          </div>
          <button onClick={logout} className="mt-2 text-brand-600 hover:underline">
            Log out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
