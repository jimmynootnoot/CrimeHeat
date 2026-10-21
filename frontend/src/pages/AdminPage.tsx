import { useEffect, useState, type FormEvent } from 'react';
import axios from 'axios';
import { createUserAccount, fetchUsers, type ManagedUser } from '../api/endpoints';
import { ROLE_DESCRIPTIONS, ROLE_LABELS, type UserRole } from '../types';

export function AdminPage() {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>('viewer');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  function loadUsers() {
    setLoading(true);
    setError('');
    fetchUsers()
      .then(setUsers)
      .catch(() => setError('Could not load user accounts.'))
      .finally(() => setLoading(false));
  }

  useEffect(loadUsers, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const created = await createUserAccount({ email, password, role });
      setUsers((current) => [created, ...current]);
      setEmail('');
      setPassword('');
      setRole('viewer');
      setSuccess(`${created.email} was created as ${ROLE_LABELS[created.role]}.`);
    } catch (err) {
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : undefined;
      setError(typeof detail === 'string' ? detail : 'Could not create this account.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="h-full overflow-y-auto bg-slate-50 p-6">
      <div className="mx-auto max-w-5xl space-y-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900">Administration</h1>
            <span className="rounded-full bg-amber-200 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-amber-950">
              Administrator only
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Create accounts and assign the least privilege each person needs.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]">
          <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-4 py-3">
              <h2 className="font-semibold text-slate-900">User accounts</h2>
            </div>
            {loading ? (
              <p className="p-4 text-sm text-slate-500">Loading accounts…</p>
            ) : users.length === 0 ? (
              <p className="p-4 text-sm text-slate-500">No accounts found.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <tr><th className="px-4 py-2">Email</th><th className="px-4 py-2">Role</th><th className="px-4 py-2">Created</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {users.map((account) => (
                      <tr key={account.id}>
                        <td className="px-4 py-3 font-medium text-slate-800">{account.email}</td>
                        <td className="px-4 py-3"><span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">{ROLE_LABELS[account.role]}</span></td>
                        <td className="px-4 py-3 text-slate-500">{account.created_at ? new Date(account.created_at).toLocaleDateString() : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <form onSubmit={submit} className="h-fit space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="font-semibold text-slate-900">Create account</h2>
            <label className="block text-sm font-medium text-slate-700">Email
              <input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} className="mt-1 block w-full rounded border border-slate-300 px-3 py-2" />
            </label>
            <label className="block text-sm font-medium text-slate-700">Temporary password
              <input type="password" required minLength={8} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} className="mt-1 block w-full rounded border border-slate-300 px-3 py-2" />
              <span className="mt-1 block text-xs font-normal text-slate-500">At least 8 characters. Share it securely.</span>
            </label>
            <label className="block text-sm font-medium text-slate-700">Role
              <select value={role} onChange={(event) => setRole(event.target.value as UserRole)} className="mt-1 block w-full rounded border border-slate-300 px-3 py-2">
                {(Object.keys(ROLE_LABELS) as UserRole[]).map((value) => <option key={value} value={value}>{ROLE_LABELS[value]}</option>)}
              </select>
              <span className="mt-1 block text-xs font-normal text-slate-500">{ROLE_DESCRIPTIONS[role]}</span>
            </label>
            {error && <p role="alert" className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
            {success && <p className="rounded bg-emerald-50 p-2 text-sm text-emerald-800">{success}</p>}
            <button disabled={saving} className="w-full rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
              {saving ? 'Creating…' : 'Create account'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
