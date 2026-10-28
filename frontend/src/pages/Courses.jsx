import { BookOpen, GraduationCap, Plus, Trash2, Users } from 'lucide-react'
import { useState } from 'react'
import { Card, Empty, ErrorBox, Field, Modal, PageHeader, Spinner, useToast } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import api, { errorMessage } from '../lib/api'
import { useApi } from '../lib/hooks'

const EMPTY = { course_name: '', course_code: '', semester: '', credits: 3, description: '' }

export default function Courses() {
  const { user } = useAuth()
  const toast = useToast()
  const mine = useApi('/courses')
  const catalog = useApi('/courses/catalog')
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [roster, setRoster] = useState(null)

  const refresh = () => { mine.reload(); catalog.reload() }

  const create = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.post('/courses', { ...form, credits: Number(form.credits) || 3, course_code: form.course_code || null, semester: form.semester || null })
      setForm(EMPTY)
      setOpen(false)
      toast('Course created')
      refresh()
    } catch (err) { setError(errorMessage(err)) }
  }

  const act = async (fn, msg) => {
    try { await fn(); toast(msg); refresh() } catch (err) { toast(errorMessage(err), 'error') }
  }

  const showRoster = async (c) => {
    try { setRoster({ course: c, students: (await api.get(`/courses/${c.course_id}/students`)).data }) }
    catch (err) { toast(errorMessage(err), 'error') }
  }

  const others = (catalog.data || []).filter((c) => !c.enrolled && !c.can_manage)

  return (
    <div>
      <PageHeader title="Courses" subtitle="Manage the courses you take or teach">
        <button className="btn-primary" onClick={() => setOpen(true)}><Plus className="h-4 w-4" /> New course</button>
      </PageHeader>

      <Card title="My courses" icon={GraduationCap}>
        {mine.loading && !mine.data ? <Spinner /> : mine.error ? <ErrorBox message={mine.error} onRetry={mine.reload} /> :
          mine.data.length === 0 ? <Empty icon={BookOpen} title="No courses yet">Create one or join from the catalog below.</Empty> : (
            <div className="grid gap-4 md:grid-cols-2">
              {mine.data.map((c) => (
                <div key={c.course_id} className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-lg font-bold text-white">{c.course_name}</p>
                      <p className="text-sm text-ink-2">{[c.course_code, c.semester, `${c.credits} credits`].filter(Boolean).join(' · ')}</p>
                      {c.instructor_name && <p className="mt-1 text-xs text-ink-3">Instructor: {c.instructor_name}</p>}
                    </div>
                    <div className="flex gap-1">
                      {c.can_manage && user.role !== 'student' && (
                        <button className="rounded-lg p-2 text-ink-2 hover:bg-white/10" title="Roster" onClick={() => showRoster(c)}><Users className="h-4 w-4" /></button>
                      )}
                      {c.can_manage ? (
                        <button className="rounded-lg p-2 text-rose-400 hover:bg-rose-500/10" title="Delete course"
                          onClick={() => window.confirm(`Delete "${c.course_name}" and all its records?`) && act(() => api.delete(`/courses/${c.course_id}`), 'Course deleted')}>
                          <Trash2 className="h-4 w-4" />
                        </button>
                      ) : (
                        <button className="btn-ghost btn-sm" onClick={() => act(() => api.delete(`/courses/${c.course_id}/enroll`), 'Left course')}>Leave</button>
                      )}
                    </div>
                  </div>
                  {c.description && <p className="mt-3 text-sm text-ink-2">{c.description}</p>}
                  <p className="mt-3 text-xs text-ink-3">{c.student_count} student{c.student_count === 1 ? '' : 's'} enrolled</p>
                </div>
              ))}
            </div>
          )}
      </Card>

      <Card title="Course catalog" subtitle="Join a course created by an instructor or classmate" className="mt-6">
        {catalog.loading && !catalog.data ? <Spinner /> : others.length === 0 ? <p className="text-sm text-ink-2">No other courses available.</p> : (
          <ul className="divide-y divide-white/5">
            {others.map((c) => (
              <li key={c.course_id} className="flex items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="truncate font-medium text-white">{c.course_name} <span className="text-ink-3">{c.course_code}</span></p>
                  <p className="text-xs text-ink-2">{c.instructor_name ? `Instructor: ${c.instructor_name}` : 'Self-study course'} · {c.student_count} enrolled</p>
                </div>
                <button className="btn-green btn-sm" onClick={() => act(() => api.post(`/courses/${c.course_id}/enroll`), 'Enrolled')}>Enroll</button>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Modal open={open} title="New course" onClose={() => setOpen(false)}>
        <form onSubmit={create} className="space-y-4">
          <Field label="Course name"><input className="input" required maxLength={150} value={form.course_name} onChange={(e) => setForm({ ...form, course_name: e.target.value })} /></Field>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Code"><input className="input" maxLength={30} placeholder="BSC 401" value={form.course_code} onChange={(e) => setForm({ ...form, course_code: e.target.value })} /></Field>
            <Field label="Semester"><input className="input" maxLength={40} placeholder="Fall 2026" value={form.semester} onChange={(e) => setForm({ ...form, semester: e.target.value })} /></Field>
            <Field label="Credits"><input className="input" type="number" min={1} max={30} value={form.credits} onChange={(e) => setForm({ ...form, credits: e.target.value })} /></Field>
          </div>
          <Field label="Description"><textarea className="input" rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
          <ErrorBox message={error} />
          <button className="btn-primary w-full">Create course</button>
        </form>
      </Modal>

      <Modal open={!!roster} title={`Students - ${roster?.course.course_name}`} onClose={() => setRoster(null)}>
        {roster?.students.length ? (
          <ul className="divide-y divide-white/5">
            {roster.students.map((s) => (
              <li key={s.user_id} className="flex justify-between py-2 text-sm"><span className="text-white">{s.name}</span><span className="text-ink-2">{s.email} · ID {s.user_id}</span></li>
            ))}
          </ul>
        ) : <p className="text-sm text-ink-2">No students enrolled yet.</p>}
        <p className="mt-3 text-xs text-ink-3">Use a student's ID on the Grades and Attendance pages to record results for them.</p>
      </Modal>
    </div>
  )
}
