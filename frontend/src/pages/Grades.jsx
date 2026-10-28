import { GraduationCap, Plus, Trash2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { BarSeries, LineSeries } from '../components/charts'
import { Card, CourseSelect, Empty, ErrorBox, Field, PageHeader, Spinner, useToast } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import api, { errorMessage } from '../lib/api'
import { fmtDate, todayISO, useApi } from '../lib/hooks'

const TYPES = ['quiz', 'assignment', 'midterm', 'final', 'project', 'lab', 'other']

export default function Grades() {
  const { user } = useAuth()
  const toast = useToast()
  const courses = useApi('/courses')
  const [courseFilter, setCourseFilter] = useState(null)
  const list = useApi('/grades', courseFilter ? { course_id: courseFilter } : {})
  const [form, setForm] = useState({ course_id: null, assessment_type: 'quiz', title: '', score: '', max_score: 100, weight: 1, graded_on: todayISO(), student_id: '' })
  const [error, setError] = useState('')

  const byCourse = useMemo(() => {
    const agg = {}
    for (const g of list.data || []) {
      const a = (agg[g.course_name] ||= { s: 0, w: 0 })
      a.s += g.percentage * g.weight
      a.w += g.weight
    }
    return Object.entries(agg).map(([course, a]) => ({ course, average: Math.round((a.s / a.w) * 10) / 10 }))
  }, [list.data])

  const create = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.course_id) return setError('Choose a course')
    try {
      await api.post('/grades', {
        ...form,
        score: Number(form.score), max_score: Number(form.max_score), weight: Number(form.weight),
        student_id: form.student_id ? Number(form.student_id) : null,
      })
      setForm({ ...form, title: '', score: '' })
      toast(form.student_id ? 'Grade recorded for student' : 'Grade added - prediction updated')
      list.reload()
    } catch (err) { setError(errorMessage(err)) }
  }

  const remove = async (g) => {
    try { await api.delete(`/grades/${g.grade_id}`); list.reload() } catch (err) { toast(errorMessage(err), 'error') }
  }

  return (
    <div>
      <PageHeader title="Grades & Progress" subtitle="Every grade you add refreshes your AI performance estimate" />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Add grade" icon={Plus}>
          <form onSubmit={create} className="space-y-4">
            <Field label="Course"><CourseSelect courses={courses.data} value={form.course_id} onChange={(v) => setForm({ ...form, course_id: v })} required /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Type">
                <select className="input" value={form.assessment_type} onChange={(e) => setForm({ ...form, assessment_type: e.target.value })}>
                  {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </Field>
              <Field label="Date"><input type="date" className="input" value={form.graded_on} onChange={(e) => setForm({ ...form, graded_on: e.target.value })} /></Field>
            </div>
            <Field label="Title"><input className="input" required maxLength={200} placeholder="Quiz 2: Cell membranes" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
            <div className="grid grid-cols-3 gap-3">
              <Field label="Score"><input type="number" step="any" min={0} className="input" required value={form.score} onChange={(e) => setForm({ ...form, score: e.target.value })} /></Field>
              <Field label="Out of"><input type="number" step="any" min={0.01} className="input" required value={form.max_score} onChange={(e) => setForm({ ...form, max_score: e.target.value })} /></Field>
              <Field label="Weight"><input type="number" step="any" min={0.01} className="input" required value={form.weight} onChange={(e) => setForm({ ...form, weight: e.target.value })} /></Field>
            </div>
            {user.role !== 'student' && (
              <Field label="Student ID (instructors, optional)"><input type="number" className="input" value={form.student_id} onChange={(e) => setForm({ ...form, student_id: e.target.value })} /></Field>
            )}
            <ErrorBox message={error} />
            <button className="btn-primary w-full">Save grade</button>
          </form>
        </Card>

        <div className="space-y-6 lg:col-span-2">
          <div className="grid gap-6 md:grid-cols-2">
            <Card title="Average by course" subtitle="Weighted %">
              {byCourse.length ? <BarSeries data={byCourse} x="course" y="average" unit="%" color="#a78bfa" domain={[0, 100]} /> : <Empty title="No data yet" />}
            </Card>
            <Card title="Score timeline" subtitle="70% reference line">
              {list.data?.length ? <LineSeries data={list.data.map((g) => ({ ...g, label: `${g.title} (${g.course_name})` }))} x="graded_on" y="percentage" labelKey="label" refY={70} color="#22d3ee" /> : <Empty title="No data yet" />}
            </Card>
          </div>
          <Card title="All grades" icon={GraduationCap}
            action={<div className="w-48"><CourseSelect courses={courses.data} value={courseFilter} onChange={setCourseFilter} allowAll /></div>}>
            {list.loading && !list.data ? <Spinner /> : list.error ? <ErrorBox message={list.error} onRetry={list.reload} /> :
              list.data.length === 0 ? <Empty icon={GraduationCap} title="No grades yet" /> : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead><tr><th className="table-head">Date</th><th className="table-head">Course</th><th className="table-head">Assessment</th><th className="table-head">Score</th><th className="table-head">%</th><th className="table-head" /></tr></thead>
                    <tbody>
                      {[...list.data].reverse().map((g) => (
                        <tr key={g.grade_id}>
                          <td className="table-cell whitespace-nowrap text-ink-2">{fmtDate(g.graded_on)}</td>
                          <td className="table-cell">{g.course_name}</td>
                          <td className="table-cell"><span className="text-white">{g.title}</span> <span className="text-xs text-ink-3">{g.assessment_type}</span></td>
                          <td className="table-cell">{g.score}/{g.max_score}</td>
                          <td className={`table-cell font-semibold ${g.percentage >= 70 ? 'text-emerald-300' : g.percentage >= 50 ? 'text-amber-300' : 'text-rose-300'}`}>{g.percentage}%</td>
                          <td className="table-cell text-right"><button className="rounded-lg p-2 text-rose-400 hover:bg-rose-500/10" onClick={() => remove(g)} aria-label="Delete"><Trash2 className="h-4 w-4" /></button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
          </Card>
        </div>
      </div>
    </div>
  )
}
