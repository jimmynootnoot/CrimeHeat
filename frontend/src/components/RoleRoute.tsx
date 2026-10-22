import type { ReactNode } from 'react';
import { useAuth } from '../context/AuthContext';
import { ROLE_LABELS, type UserRole } from '../types';

export function RoleRoute({
  children,
  allowed,
}: {
  children: ReactNode;
  allowed: UserRole[];
}) {
  const { user } = useAuth();

  if (!user || !allowed.includes(user.role)) {
    return (
      <div className="flex h-full items-center justify-center bg-slate-50 p-6">
        <div className="max-w-md rounded-lg border border-amber-200 bg-white p-6 text-center shadow-sm">
          <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-amber-100 text-xl text-amber-800">
            !
          </div>
          <h1 className="text-lg font-bold text-slate-900">Access restricted</h1>
          <p className="mt-2 text-sm text-slate-600">
            Your {user ? ROLE_LABELS[user.role] : 'current'} account does not have permission to use this area.
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
