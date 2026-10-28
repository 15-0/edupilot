import { Trash2, UserCheck } from 'lucide-react'
import { useState } from 'react'
import { BarSeries } from '../components/charts'
import { Badge, Card, CourseSelect, Empty, ErrorBox, Field, PageHeader, Spinner, useToast } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import api, { errorMessage } from '../lib/api'
import { fmtDate, todayISO, useApi } from '../lib/hooks'

const STATUSES = ['present', 'late', 'absent', 'excused']

export default function Attendance() {
  const { user } = useAuth()
  const toast = useToast()
  const courses = useApi('/courses')
  const list = useApi('/attendance')
  const summary = useApi('/attendance/summary')
  const [form, setForm] = useState({ course_id: null, attendance_date: todayISO(), status: 'present', student_id: '' })
  const [error, setError] = useState('')

  const refresh = () => { list.reload(); summary.reload() }

  const mark = async (status) => {
    setError('')
    if (!form.course_id) return setError('Choose a course')
    try {
      await api.post('/attendance', { ...form, status, student_id: form.student_id ? Number(form.student_id) : null })
      toast(`Marked ${status}`)
      refresh()
    } catch (err) { setError(errorMessage(err)) }
  }

  const remove = async (a) => {
    try { await api.delete(`/attendance/${a.attendance_id}`); refresh() } catch (err) { toast(errorMessage(err), 'error') }
  }

  const chart = (summary.data || []).filter((s) => s.rate != null).map((s) => ({ course: s.course_name, rate: s.rate }))

  return (
    <div>
      <PageHeader title="Attendance" subtitle="Late counts as 75%; excused classes are not counted" />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Mark attendance" icon={UserCheck}>
          <div className="space-y-4">
            <Field label="Course"><CourseSelect courses={courses.data} value={form.course_id} onChange={(v) => setForm({ ...form, course_id: v })} required /></Field>
            <Field label="Date"><input type="date" className="input" value={form.attendance_date} onChange={(e) => setForm({ ...form, attendance_date: e.target.value })} /></Field>
            {user.role !== 'student' && (
              <Field label="Student ID (instructors, optional)"><input type="number" className="input" value={form.student_id} onChange={(e) => setForm({ ...form, student_id: e.target.value })} /></Field>
            )}
            <div className="grid grid-cols-2 gap-2">
              {STATUSES.map((s) => (
                <button key={s} type="button" onClick={() => mark(s)} className={s === 'present' ? 'btn-green' : s === 'absent' ? 'btn-pink' : 'btn-ghost'}>{s}</button>
              ))}
            </div>
            <ErrorBox message={error} />
          </div>
        </Card>
        <Card title="Attendance rate by course" className="lg:col-span-2">
          {chart.length ? <BarSeries data={chart} x="course" y="rate" unit="%" color="#34d399" domain={[0, 100]} /> : <Empty title="No attendance recorded yet" />}
          {summary.data?.length > 0 && (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {summary.data.map((s) => (
                <div key={s.course_id} className="rounded-xl bg-white/[0.03] p-3 text-sm">
                  <p className="font-medium text-white">{s.course_name} <span className="text-ink-2">· {s.rate ?? '-'}%</span></p>
                  <p className="text-xs text-ink-2">{s.present} present · {s.late} late · {s.absent} absent · {s.excused} excused</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
      <Card title="History" className="mt-6">
        {list.loading && !list.data ? <Spinner /> : list.error ? <ErrorBox message={list.error} /> : list.data.length === 0 ? <Empty title="No records" /> : (
          <ul className="divide-y divide-white/5">
            {list.data.map((a) => (
              <li key={a.attendance_id} className="flex items-center justify-between py-2.5">
                <span className="text-sm"><span className="text-ink-2">{fmtDate(a.attendance_date, { weekday: 'short', day: 'numeric', month: 'short' })}</span> · <span className="text-white">{a.course_name}</span></span>
                <span className="flex items-center gap-2"><Badge kind={a.status} /><button className="rounded-lg p-1.5 text-rose-400 hover:bg-rose-500/10" onClick={() => remove(a)} aria-label="Delete"><Trash2 className="h-4 w-4" /></button></span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
