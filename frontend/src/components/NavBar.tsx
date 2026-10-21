import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { APP_NAME } from '../api/client';
import { ROLE_LABELS, type UserRole } from '../types';

const links = [
  { to: '/dashboard', label: 'Dashboard', roles: ['viewer', 'analyst', 'admin'] },
  { to: '/map', label: 'Map', roles: ['viewer', 'analyst', 'admin'] },
  { to: '/records', label: 'Records', roles: ['viewer', 'analyst', 'admin'] },
  { to: '/upload', label: 'Upload', roles: ['analyst', 'admin'] },
  { to: '/reports', label: 'Reports', roles: ['viewer', 'analyst', 'admin'] },
  { to: '/admin', label: 'Administration', roles: ['admin'] },
];

export function NavBar() {
  const { user, logout } = useAuth();

  return (
    <nav className="flex items-center justify-between bg-slate-900 text-slate-100 px-4 py-2">
      <div className="flex items-center gap-4">
        <span className="font-bold tracking-wide" title={APP_NAME}>
          PPALMA
        </span>
        <div className="flex gap-1">
          {links.filter((link) => user && link.roles.includes(user.role)).map((link) => (
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
        {user && (
          <span
            className={`rounded-full px-2.5 py-1 text-xs font-bold uppercase tracking-wide ${
              user.role === 'admin'
                ? 'bg-amber-300 text-amber-950'
                : user.role === 'analyst'
                  ? 'bg-violet-300 text-violet-950'
                  : 'bg-sky-300 text-sky-950'
            }`}
          >
            {ROLE_LABELS[user.role as UserRole]}{user.role === 'viewer' ? ' · Read only' : ''}
          </span>
        )}
        <span className="hidden text-slate-400 lg:inline">{user?.email}</span>
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
