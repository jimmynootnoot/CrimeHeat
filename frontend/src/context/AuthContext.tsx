import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { apiClient } from '../api/client';
import type { UserRole } from '../types';

interface AuthUser {
  email: string;
  role: UserRole;
}

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  /** Full access: user management, imports, deletions, analytical parameters. */
  isAdmin: boolean;
  /** Can upload, validate, and run analyses (analyst or admin). */
  canAnalyze: boolean;
  /** Read-only account. */
  isViewer: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function readStoredUser(): AuthUser | null {
  const email = localStorage.getItem('user_email');
  const role = localStorage.getItem('user_role') as UserRole | null;
  if (!email || !role) return null;
  return { email, role };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(readStoredUser);

  const login = useCallback(async (email: string, password: string) => {
    const normalizedEmail = email.trim().toLowerCase();
    const form = new URLSearchParams();
    form.set('username', normalizedEmail);
    form.set('password', password);
    const response = await apiClient.post('/api/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    // Fall back to the least-privileged role if the server omits it, so a
    // malformed response can never silently grant elevated access.
    const role: UserRole = response.data.role ?? 'viewer';
    localStorage.setItem('access_token', response.data.access_token);
    localStorage.setItem('user_email', normalizedEmail);
    localStorage.setItem('user_role', role);
    setUser({ email: normalizedEmail, role });
  }, []);

  const logout = useCallback(async () => {
    // Record the logout for the audit trail, but never block signing out on it.
    try {
      await apiClient.post('/api/auth/logout');
    } catch {
      /* already signed out, offline, or token expired — proceed regardless */
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_email');
    localStorage.removeItem('user_role');
    setUser(null);
  }, []);

  const role = user?.role;

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isAdmin: role === 'admin',
        canAnalyze: role === 'admin' || role === 'analyst',
        isViewer: role === 'viewer',
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
