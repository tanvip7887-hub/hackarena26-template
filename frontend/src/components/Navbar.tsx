import { Link, useLocation } from "react-router-dom";

const links = [
  { to: "/",         label: "Dashboard" },
  { to: "/live",     label: "Live View" },
  { to: "/alerts",   label: "Alerts"    },
  { to: "/history",  label: "History"   },
];

export default function Navbar() {
  const { pathname } = useLocation();

  return (
    <nav className="flex items-center justify-between px-6 py-3 bg-bg2 border-b border-border">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 border-2 border-green rounded flex items-center justify-center">
          <div className="w-3 h-3 bg-green rounded-sm" />
        </div>
        <span className="font-head text-lg font-bold text-green tracking-widest">
          THREAT<span className="text-cyan">SENSE</span>
          <span className="text-text-dim font-normal text-xs ml-1">AI</span>
        </span>
      </div>

      {/* Nav links */}
      <div className="flex gap-1">
        {links.map(({ to, label }) => (
          <Link
            key={to}
            to={to}
            className={`px-4 py-1.5 rounded text-sm font-semibold font-body tracking-wide transition-all
              ${pathname === to
                ? "bg-green text-bg font-bold"
                : "text-text-dim hover:text-green hover:bg-green/10"
              }`}
          >
            {label}
          </Link>
        ))}
      </div>

      {/* Status indicator */}
      <div className="flex items-center gap-2 text-xs font-mono">
        <span className="pulse w-2 h-2 rounded-full bg-green inline-block" />
        <span className="text-green">SYSTEM ONLINE</span>
        <span className="text-text-dim ml-3">Admin User</span>
      </div>
    </nav>
  );
}   




navabar.tsx