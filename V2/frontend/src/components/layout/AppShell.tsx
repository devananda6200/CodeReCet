import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/settings", label: "Settings" }
];

export function AppShell() {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(249,115,22,0.2),_transparent_22%),linear-gradient(180deg,_#081019,_#0e1726_35%,_#081019)] text-white">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-6 lg:flex-row lg:gap-6 lg:px-6">
        <aside className="mb-6 rounded-3xl border border-white/10 bg-black/15 p-5 backdrop-blur lg:mb-0 lg:w-72">
          <p className="text-xs uppercase tracking-[0.32em] text-accent">YOLO11 Ops Safety</p>
          <h1 className="mt-3 font-display text-3xl leading-tight">
            Industrial visibility for CPU-first deployments.
          </h1>
          <p className="mt-3 text-sm leading-6 text-mist">
            Demo shell for PPE compliance, no-go zones, and machine proximity alerts.
          </p>

          <nav className="mt-8 space-y-2">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === "/"}
                className={({ isActive }) =>
                  `block rounded-2xl px-4 py-3 text-sm font-medium transition ${
                    isActive ? "bg-accent text-slate-950" : "bg-white/5 text-white hover:bg-white/10"
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
        </aside>

        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

