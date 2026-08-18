import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const links = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/map', label: 'Map' },
  { to: '/records', label: 'Records' },
  { to: '/upload', label: 'Upload' },
  { to: '/reports', label: 'Reports' },
];

export function NavBar() {
  const { user, logout } = useAuth();

  return (
    <nav className="flex items-center justify-between bg-slate-900 text-slate-100 px-4 py-2">
      <div className="flex items-center gap-4">
        <span className="font-bold tracking-wide">PPALMA Crime Watch</span>
        <div className="flex gap-1">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `px-3 py-1.5 rounded text-sm font-medium ${
                  isActive ? 'bg-slate-700 text-white' : 'text-slate-300 hover:bg-slate-800'
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-3 text-sm">
        <span className="text-slate-400">{user?.email}</span>
        <button
          onClick={logout}
          className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200"
        >
          Log out
        </button>
      </div>
    </nav>
  );
}
