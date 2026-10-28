import { Shield } from 'lucide-react'
import { Card, ErrorBox, PageHeader, Spinner, useToast } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import api, { errorMessage } from '../lib/api'
import { fmtDate, useApi } from '../lib/hooks'

export default function Admin() {
  const { user: me } = useAuth()
  const toast = useToast()
  const users = useApi('/admin/users')

  const setRole = async (u, role) => {
    try { await api.patch(`/admin/users/${u.user_id}/role`, { role }); toast('Role updated'); users.reload() }
    catch (err) { toast(errorMessage(err), 'error') }
  }

  return (
    <div>
      <PageHeader title="Administration" subtitle="Manage users and roles" />
      <Card title="Users" icon={Shield}>
        {users.loading && !users.data ? <Spinner /> : users.error ? <ErrorBox message={users.error} /> : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr><th className="table-head">ID</th><th className="table-head">Name</th><th className="table-head">Email</th><th className="table-head">Joined</th><th className="table-head">Role</th></tr></thead>
              <tbody>
                {users.data.map((u) => (
                  <tr key={u.user_id}>
                    <td className="table-cell text-ink-3">{u.user_id}</td>
                    <td className="table-cell text-white">{u.name}</td>
                    <td className="table-cell text-ink-2">{u.email}</td>
                    <td className="table-cell text-ink-2">{fmtDate(u.created_at?.slice(0, 10), { day: 'numeric', month: 'short', year: 'numeric' })}</td>
                    <td className="table-cell">
                      <select className="input py-1.5" value={u.role} disabled={u.user_id === me.user_id} onChange={(e) => setRole(u, e.target.value)}>
                        <option value="student">student</option><option value="instructor">instructor</option><option value="admin">admin</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
