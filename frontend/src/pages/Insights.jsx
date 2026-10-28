import { BarChart3, Info, Loader2, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { Card, Empty, ErrorBox, PageHeader, RiskBadge, Spinner, useToast } from '../components/ui'
import api, { errorMessage } from '../lib/api'
import { useApi } from '../lib/hooks'

function RangeBar({ low, high, value }) {
  return (
    <div className="relative mt-3 h-2.5 rounded-full bg-white/[0.07]" aria-label={`Estimated ${value}%, likely between ${low}% and ${high}%`}>
      <div className="absolute inset-y-0 rounded-full bg-gradient-to-r from-cyan-500/50 to-purple-500/50" style={{ left: `${low}%`, width: `${Math.max(high - low, 1)}%` }} />
      <div className="absolute -top-1 h-4.5 w-1 rounded bg-white" style={{ left: `calc(${value}% - 2px)` }} />
      <div className="absolute top-0 h-full w-px bg-white/30" style={{ left: '70%' }} />
      <div className="mt-4 flex justify-between text-[10px] text-ink-3"><span>0</span><span>70</span><span>100</span></div>
    </div>
  )
}

export default function Insights() {
  const toast = useToast()
  const preds = useApi('/ai/predictions')
  const info = useApi('/ai/model-info')
  const [busy, setBusy] = useState(false)

  const refresh = async () => {
    setBusy(true)
    try { preds.setData((await api.post('/ai/predict')).data); toast('Predictions refreshed') }
    catch (err) { toast(errorMessage(err), 'error') } finally { setBusy(false) }
  }

  return (
    <div>
      <PageHeader title="AI Performance Insights" subtitle="Machine-learning estimates of your final course scores">
        <button className="btn-primary" onClick={refresh} disabled={busy}>{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />} Recalculate</button>
      </PageHeader>

      <div className="mb-6 flex items-start gap-3 rounded-xl border border-amber-400/30 bg-amber-500/10 p-4 text-sm text-amber-100">
        <Info className="mt-0.5 h-5 w-5 shrink-0" />
        <p>These are <strong>estimates, not guarantees</strong>. They are based on your grades so far, attendance, logged study time and assignment completion, and the range shows the model's typical error. Your effort from here changes the outcome.</p>
      </div>

      {preds.loading && !preds.data ? <Spinner /> : preds.error ? <ErrorBox message={preds.error} onRetry={preds.reload} /> :
        !preds.data.length ? (
          <Card><Empty icon={BarChart3} title="No predictions yet">Add a grade or press Recalculate once you are enrolled in courses.</Empty></Card>
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {preds.data.map((p) => (
              <Card key={p.prediction_id}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-lg font-bold text-white">{p.course_name}</p>
                    <p className="text-sm text-ink-2">Estimated final score</p>
                  </div>
                  <RiskBadge level={p.risk_level} />
                </div>
                <p className="mt-3 text-4xl font-bold text-white">{p.predicted_score}%</p>
                <p className="text-sm text-ink-2">likely between {p.lower_bound}% and {p.upper_bound}%</p>
                <RangeBar low={p.lower_bound} high={p.upper_bound} value={p.predicted_score} />
                <div className="mt-5 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
                  {[
                    ['Average', p.features.has_grades ? `${p.features.avg_score}%` : '-'],
                    ['Attendance', p.features.has_attendance ? `${Math.round(p.features.attendance_rate * 100)}%` : '-'],
                    ['Study/wk', `${p.features.study_hours_per_week}h`],
                    ['Completion', `${Math.round(p.features.completion_rate * 100)}%`],
                  ].map(([k, v]) => (
                    <div key={k} className="rounded-lg bg-white/[0.04] p-2"><p className="text-ink-3">{k}</p><p className="font-semibold text-white">{v}</p></div>
                  ))}
                </div>
                {p.drivers.length > 0 && (
                  <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-ink-2">
                    {p.drivers.map((d) => <li key={d}>{d}</li>)}
                  </ul>
                )}
              </Card>
            ))}
          </div>
        )}

      {info.data && (
        <Card title="About the model" className="mt-6">
          <div className="grid gap-4 text-sm sm:grid-cols-4">
            <div><p className="text-ink-3">Model</p><p className="font-semibold text-white">{info.data.model_version}</p></div>
            <div><p className="text-ink-3">Mean abs. error</p><p className="font-semibold text-white">±{info.data.mae} pts</p></div>
            <div><p className="text-ink-3">R²</p><p className="font-semibold text-white">{info.data.r2}</p></div>
            <div><p className="text-ink-3">Naive baseline error</p><p className="font-semibold text-white">±{info.data.baseline_mae} pts</p></div>
          </div>
          <p className="mt-3 text-xs text-ink-3">Gradient-boosted regression trained on a {info.data.dataset} dataset of {info.data.rows} students. Retrain with real data via <code>python -m app.ml.train</code>.</p>
        </Card>
      )}
    </div>
  )
}
