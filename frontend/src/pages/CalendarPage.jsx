import { ChevronLeft, ChevronRight, Clock, Trash2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Card, CourseSelect, ErrorBox, Field, PageHeader, Spinner, useToast } from '../components/ui'
import api, { errorMessage } from '../lib/api'
import { fmtDate, todayISO, useApi } from '../lib/hooks'

const iso = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
const COLORS = {
  assignment: 'bg-pink-500/20 text-pink-200',
  session: 'bg-emerald-500/20 text-emerald-200',
  plan: 'bg-cyan-500/15 text-cyan-200',
}

export default function CalendarPage() {
  const toast = useToast()
  const [month, setMonth] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1) })
  const gridStart = useMemo(() => { const d = new Date(month); d.setDate(1 - ((d.getDay() + 6) % 7)); return d }, [month])
  const days = useMemo(() => Array.from({ length: 42 }, (_, i) => { const d = new Date(gridStart); d.setDate(d.getDate() + i); return d }), [gridStart])
  const events = useApi('/calendar', { start: iso(days[0]), end: iso(days[41]) })
  const courses = useApi('/courses')
  const sessions = useApi('/study-sessions')
  const [selected, setSelected] = useState(todayISO())
  const [form, setForm] = useState({ course_id: null, duration_minutes: 45, topic: '', session_date: todayISO() })
  const [error, setError] = useState('')

  const byDay = useMemo(() => {
    const m = {}
    for (const e of events.data || []) (m[e.date] ||= []).push(e)
    return m
  }, [events.data])

  const logSession = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.post('/study-sessions', { ...form, duration_minutes: Number(form.duration_minutes), topic: form.topic || null })
      toast('Study session logged')
      setForm({ ...form, topic: '' })
      events.reload(); sessions.reload()
    } catch (err) { setError(errorMessage(err)) }
  }

  const removeSession = async (s) => {
    try { await api.delete(`/study-sessions/${s.session_id}`); events.reload(); sessions.reload() } catch (err) { toast(errorMessage(err), 'error') }
  }

  const shift = (n) => setMonth(new Date(month.getFullYear(), month.getMonth() + n, 1))
  const today = todayISO()

  return (
    <div>
      <PageHeader title="Study Calendar" subtitle="Deadlines, planned study blocks and logged sessions">
        <button className="btn-ghost" onClick={() => shift(-1)} aria-label="Previous month"><ChevronLeft className="h-4 w-4" /></button>
        <span className="self-center px-2 font-semibold text-white">{month.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</span>
        <button className="btn-ghost" onClick={() => shift(1)} aria-label="Next month"><ChevronRight className="h-4 w-4" /></button>
      </PageHeader>
      <div className="grid gap-6 xl:grid-cols-4">
        <Card className="xl:col-span-3 p-4">
          <div className="mb-2 flex gap-4 text-xs text-ink-2">
            <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-pink-400" /> Deadline</span>
            <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-cyan-400" /> Planned</span>
            <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-emerald-400" /> Logged session</span>
          </div>
          {events.error && <ErrorBox message={events.error} />}
          <div className="grid grid-cols-7 gap-1 text-center text-xs text-ink-3">
            {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => <div key={d} className="py-1">{d}</div>)}
          </div>
          <div className="grid grid-cols-7 gap-1">
            {days.map((d) => {
              const key = iso(d)
              const evs = byDay[key] || []
              const inMonth = d.getMonth() === month.getMonth()
              return (
                <button key={key} onClick={() => setSelected(key)}
                  className={`min-h-[92px] rounded-lg border p-1.5 text-left align-top transition ${selected === key ? 'border-cyan-400/60 bg-white/[0.07]' : 'border-white/5 bg-white/[0.02] hover:bg-white/[0.05]'} ${inMonth ? '' : 'opacity-40'}`}>
                  <span className={`inline-grid h-6 w-6 place-items-center rounded-full text-xs ${key === today ? 'bg-cyan-500 font-bold text-white' : 'text-ink-2'}`}>{d.getDate()}</span>
                  <div className="mt-1 space-y-0.5">
                    {evs.slice(0, 3).map((e) => (
                      <div key={e.id} className={`truncate rounded px-1 py-0.5 text-[10px] ${COLORS[e.type]} ${e.done ? 'line-through opacity-60' : ''}`}>{e.title}</div>
                    ))}
                    {evs.length > 3 && <div className="text-[10px] text-ink-3">+{evs.length - 3} more</div>}
                  </div>
                </button>
              )
            })}
          </div>
          {events.loading && <Spinner />}
        </Card>

        <div className="space-y-6">
          <Card title={fmtDate(selected, { weekday: 'long', day: 'numeric', month: 'long' })}>
            {(byDay[selected] || []).length === 0 ? <p className="text-sm text-ink-2">Nothing scheduled.</p> : (
              <ul className="space-y-2">
                {byDay[selected].map((e) => (
                  <li key={e.id} className={`rounded-lg p-2 text-sm ${COLORS[e.type]}`}>
                    <p className="font-medium">{e.title}</p>
                    <p className="text-xs opacity-80">{[e.course_name, e.minutes && `${e.minutes} min`, e.status].filter(Boolean).join(' · ')}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title="Log study session" icon={Clock}>
            <form onSubmit={logSession} className="space-y-3">
              <Field label="Course"><CourseSelect courses={courses.data} value={form.course_id} onChange={(v) => setForm({ ...form, course_id: v })} allowAll allLabel="General / no course" /></Field>
              <div className="grid grid-cols-2 gap-2">
                <Field label="Minutes"><input type="number" min={1} max={1440} required className="input" value={form.duration_minutes} onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })} /></Field>
                <Field label="Date"><input type="date" className="input" value={form.session_date} onChange={(e) => setForm({ ...form, session_date: e.target.value })} /></Field>
              </div>
              <Field label="Topic"><input className="input" maxLength={200} value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} /></Field>
              <ErrorBox message={error} />
              <button className="btn-green w-full">Log session</button>
            </form>
            {sessions.data?.length > 0 && (
              <ul className="mt-4 max-h-56 divide-y divide-white/5 overflow-y-auto">
                {sessions.data.slice(0, 15).map((s) => (
                  <li key={s.session_id} className="flex items-center justify-between py-2 text-xs">
                    <span><span className="text-white">{s.topic || 'Study'}</span> <span className="text-ink-3">· {s.duration_minutes}m · {fmtDate(s.session_date)}</span></span>
                    <button className="text-rose-400" onClick={() => removeSession(s)} aria-label="Delete"><Trash2 className="h-3.5 w-3.5" /></button>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
