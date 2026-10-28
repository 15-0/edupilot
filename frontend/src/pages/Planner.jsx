import { CheckCircle2, Circle, Lightbulb, Loader2, NotebookPen, Wand2 } from 'lucide-react'
import { useState } from 'react'
import { Badge, Card, Empty, ErrorBox, Field, PageHeader, Spinner, useToast } from '../components/ui'
import api, { errorMessage } from '../lib/api'
import { fmtDate, todayISO, useApi } from '../lib/hooks'

export default function Planner() {
  const toast = useToast()
  const plan = useApi('/ai/study-plan', { start: todayISO() })
  const recs = useApi('/ai/recommendations')
  const [opts, setOpts] = useState({ hours_per_day: 2, rest_day: 6, start_date: todayISO() })
  const [busy, setBusy] = useState(false)
  const [analysing, setAnalysing] = useState(false)
  const [error, setError] = useState('')

  const generate = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const { data } = await api.post('/ai/study-plan', {
        hours_per_day: Number(opts.hours_per_day),
        rest_day: opts.rest_day === '' ? null : Number(opts.rest_day),
        start_date: opts.start_date,
      })
      plan.setData(data)
      toast('Weekly plan generated')
    } catch (err) { setError(errorMessage(err)) } finally { setBusy(false) }
  }

  const analyse = async () => {
    setAnalysing(true)
    try { recs.setData((await api.post('/ai/weak-subjects')).data); toast('Analysis updated') }
    catch (err) { toast(errorMessage(err), 'error') } finally { setAnalysing(false) }
  }

  const toggle = async (p, t) => {
    try {
      const { data } = await api.patch(`/ai/study-plan/${p.plan_id}/tasks/${t.id}`, { done: !t.done })
      plan.setData(plan.data.map((x) => (x.plan_id === data.plan_id ? data : x)))
    } catch (err) { toast(errorMessage(err), 'error') }
  }

  const allTasks = (plan.data || []).flatMap((p) => p.tasks)
  const done = allTasks.filter((t) => t.done).length

  return (
    <div>
      <PageHeader title="AI Study Planner" subtitle="A personalised week built from your grades, predictions and deadlines" />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Generate plan" icon={Wand2}>
          <form onSubmit={generate} className="space-y-4">
            <Field label="Start date"><input type="date" className="input" value={opts.start_date} onChange={(e) => setOpts({ ...opts, start_date: e.target.value })} /></Field>
            <Field label={`Hours per day: ${opts.hours_per_day}`}>
              <input type="range" min={0.5} max={8} step={0.5} className="w-full accent-cyan-400" value={opts.hours_per_day} onChange={(e) => setOpts({ ...opts, hours_per_day: e.target.value })} />
            </Field>
            <Field label="Lighter day">
              <select className="input" value={opts.rest_day} onChange={(e) => setOpts({ ...opts, rest_day: e.target.value })}>
                <option value="">None</option>
                {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map((d, i) => <option key={d} value={i}>{d}</option>)}
              </select>
            </Field>
            <ErrorBox message={error} />
            <button className="btn-purple w-full" disabled={busy}>{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />} Generate weekly plan</button>
            {allTasks.length > 0 && <p className="text-center text-sm text-ink-2">{done}/{allTasks.length} tasks done</p>}
          </form>
        </Card>

        <Card title="Weak subjects & revision topics" icon={Lightbulb} className="lg:col-span-2"
          action={<button className="btn-ghost btn-sm" onClick={analyse} disabled={analysing}>{analysing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null} Analyse now</button>}>
          {recs.loading && !recs.data ? <Spinner /> : !recs.data?.length ? (
            <Empty title="No weak subjects flagged">Click "Analyse now" after adding grades - courses below ~70% are flagged here.</Empty>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {recs.data.map((r) => (
                <div key={r.recommendation_id} className="rounded-xl border border-white/5 bg-white/[0.03] p-4">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-bold text-white">{r.course_name}</p>
                    <Badge kind={r.priority}>{r.priority} priority</Badge>
                  </div>
                  <p className="mt-1 text-xs text-ink-2">{r.reason}</p>
                  <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm text-ink">
                    {r.topics.map((t) => <li key={t}>{t}</li>)}
                  </ul>
                  <p className="mt-2 text-[11px] text-ink-3">Source: {r.source === 'llm' ? 'AI-generated' : 'rule-based analysis'}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card title="This week" icon={NotebookPen} className="mt-6">
        {plan.loading && !plan.data ? <Spinner /> : plan.error ? <ErrorBox message={plan.error} onRetry={plan.reload} /> :
          !plan.data?.length ? <Empty icon={NotebookPen} title="No plan yet">Generate one to get daily study blocks.</Empty> : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {plan.data.slice(0, 7).map((p) => (
                <div key={p.plan_id} className={`rounded-xl border p-3 ${p.planned_date === todayISO() ? 'border-cyan-400/50 bg-cyan-500/[0.06]' : 'border-white/5 bg-white/[0.03]'}`}>
                  <p className="mb-2 font-semibold text-white">{fmtDate(p.planned_date, { weekday: 'long', day: 'numeric', month: 'short' })}</p>
                  {p.tasks.length === 0 ? <p className="text-xs text-ink-3">Rest</p> : (
                    <ul className="space-y-1.5">
                      {p.tasks.map((t) => (
                        <li key={t.id}>
                          <button onClick={() => toggle(p, t)} className="flex w-full items-start gap-2 rounded-lg p-1.5 text-left hover:bg-white/5">
                            {t.done ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" /> : <Circle className="mt-0.5 h-4 w-4 shrink-0 text-ink-3" />}
                            <span>
                              <span className={`block text-sm ${t.done ? 'text-ink-3 line-through' : 'text-white'}`}>{t.title}</span>
                              <span className="text-xs text-ink-2">{t.course_name} · {t.minutes} min</span>
                            </span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          )}
      </Card>
    </div>
  )
}
