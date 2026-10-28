import { ClipboardCheck, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Badge, Card, CourseSelect, Empty, ErrorBox, Field, PageHeader, Spinner, useToast } from '../components/ui'
import api, { errorMessage } from '../lib/api'
import { fmtDate, todayISO, useApi } from '../lib/hooks'

const STATUSES = ['pending', 'in_progress', 'completed']

export default function Assignments() {
  const toast = useToast()
  const courses = useApi('/courses')
  const [filter, setFilter] = useState({ course_id: null, status: '' })
  const params = { ...(filter.course_id ? { course_id: filter.course_id } : {}), ...(filter.status ? { status: filter.status } : {}) }
  const list = useApi('/assignments', params)
  const [form, setForm] = useState({ course_id: null, title: '', due_date: todayISO(), priority: 'medium', description: '' })
  const [error, setError] = useState('')

  const create = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.course_id) return setError('Choose a course')
    try {
      await api.post('/assignments', { ...form, description: form.description || null })
      setForm({ ...form, title: '', description: '' })
      toast('Assignment added')
      list.reload()
    } catch (err) { setError(errorMessage(err)) }
  }

  const update = async (a, changes) => {
    try { await api.patch(`/assignments/${a.assignment_id}`, changes); list.reload() } catch (err) { toast(errorMessage(err), 'error') }
  }
  const remove = async (a) => {
    try { await api.delete(`/assignments/${a.assignment_id}`); toast('Deleted'); list.reload() } catch (err) { toast(errorMessage(err), 'error') }
  }

  return (
    <div>
      <PageHeader title="Assignments & Deadlines" subtitle="Track coursework and never miss a due date" />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Add assignment" icon={Plus}>
          <form onSubmit={create} className="space-y-4">
            <Field label="Course"><CourseSelect courses={courses.data} value={form.course_id} onChange={(v) => setForm({ ...form, course_id: v })} required /></Field>
            <Field label="Title"><input className="input" required maxLength={200} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Due date"><input type="date" className="input" required value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} /></Field>
              <Field label="Priority">
                <select className="input" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                  <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
                </select>
              </Field>
            </div>
            <Field label="Notes (optional)"><textarea className="input" rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
            <ErrorBox message={error} />
            <button className="btn-primary w-full">Add</button>
          </form>
        </Card>

        <Card title="Your assignments" icon={ClipboardCheck} className="lg:col-span-2"
          action={
            <div className="flex gap-2">
              <div className="w-44"><CourseSelect courses={courses.data} value={filter.course_id} onChange={(v) => setFilter({ ...filter, course_id: v })} allowAll /></div>
              <select className="input w-36" value={filter.status} onChange={(e) => setFilter({ ...filter, status: e.target.value })}>
                <option value="">Any status</option>
                {STATUSES.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
              </select>
            </div>
          }>
          {list.loading && !list.data ? <Spinner /> : list.error ? <ErrorBox message={list.error} onRetry={list.reload} /> :
            list.data.length === 0 ? <Empty icon={ClipboardCheck} title="No assignments">Add one to start tracking.</Empty> : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead><tr><th className="table-head">Title</th><th className="table-head">Course</th><th className="table-head">Due</th><th className="table-head">Priority</th><th className="table-head">Status</th><th className="table-head" /></tr></thead>
                  <tbody>
                    {list.data.map((a) => (
                      <tr key={a.assignment_id}>
                        <td className="table-cell font-medium text-white">{a.title}</td>
                        <td className="table-cell text-ink-2">{a.course_name}</td>
                        <td className="table-cell whitespace-nowrap">{fmtDate(a.due_date)} {a.is_overdue && <Badge kind="overdue">Overdue</Badge>}</td>
                        <td className="table-cell"><Badge kind={a.priority} /></td>
                        <td className="table-cell">
                          <select className="input py-1.5" value={a.status} onChange={(e) => update(a, { status: e.target.value })}>
                            {STATUSES.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
                          </select>
                        </td>
                        <td className="table-cell text-right">
                          <button className="rounded-lg p-2 text-rose-400 hover:bg-rose-500/10" onClick={() => remove(a)} aria-label="Delete"><Trash2 className="h-4 w-4" /></button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
        </Card>
      </div>
    </div>
  )
}
