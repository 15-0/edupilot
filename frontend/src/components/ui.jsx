import { AlertCircle, Loader2, X } from 'lucide-react'
import { createContext, useCallback, useContext, useState } from 'react'

export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">{title}</h1>
        {subtitle && <p className="mt-1 text-ink-2">{subtitle}</p>}
      </div>
      {children && <div className="flex flex-wrap gap-2">{children}</div>}
    </div>
  )
}

export function Card({ title, subtitle, icon: Icon, action, className = '', children }) {
  return (
    <section className={`card ${className}`}>
      {(title || action) && (
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            {title && (
              <h2 className="flex items-center gap-2 text-lg font-bold text-white">
                {Icon && <Icon className="h-5 w-5 text-cyan-300" />} {title}
              </h2>
            )}
            {subtitle && <p className="mt-0.5 text-sm text-ink-2">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  )
}

const TONES = {
  pink: 'bg-pink-500/15 text-pink-300',
  cyan: 'bg-cyan-500/15 text-cyan-300',
  purple: 'bg-purple-500/15 text-purple-300',
  green: 'bg-emerald-500/15 text-emerald-300',
  amber: 'bg-amber-500/15 text-amber-300',
}

export function StatCard({ label, value, icon: Icon, tone = 'cyan', hint }) {
  return (
    <div className="card flex items-start justify-between p-5">
      <div className="min-w-0">
        <p className="text-sm text-ink-2">{label}</p>
        <p className="mt-1 truncate text-3xl font-bold text-white">{value}</p>
        {hint && <p className="mt-1 text-xs text-ink-3">{hint}</p>}
      </div>
      {Icon && (
        <div className={`grid h-12 w-12 shrink-0 place-items-center rounded-xl ${TONES[tone]}`}>
          <Icon className="h-6 w-6" />
        </div>
      )}
    </div>
  )
}

const BADGES = {
  high: 'bg-rose-500/15 text-rose-300 ring-rose-500/30',
  medium: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
  low: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
  completed: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
  in_progress: 'bg-cyan-500/15 text-cyan-300 ring-cyan-500/30',
  pending: 'bg-slate-500/20 text-slate-300 ring-slate-500/30',
  overdue: 'bg-rose-500/15 text-rose-300 ring-rose-500/30',
  present: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
  late: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
  absent: 'bg-rose-500/15 text-rose-300 ring-rose-500/30',
  excused: 'bg-slate-500/20 text-slate-300 ring-slate-500/30',
}

export function Badge({ kind, children }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${BADGES[kind] || BADGES.pending}`}>
      {children ?? String(kind).replace('_', ' ')}
    </span>
  )
}

export function RiskBadge({ level }) {
  if (!level) return null
  return <Badge kind={level}>{level === 'high' ? 'High risk' : level === 'medium' ? 'Watch' : 'On track'}</Badge>
}

export function Spinner({ label = 'Loading...' }) {
  return (
    <div className="flex items-center gap-2 py-6 text-ink-2">
      <Loader2 className="h-5 w-5 animate-spin" /> {label}
    </div>
  )
}

export function ErrorBox({ message, onRetry }) {
  if (!message) return null
  return (
    <div className="flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <span className="flex-1">{message}</span>
      {onRetry && <button className="underline" onClick={onRetry}>Retry</button>}
    </div>
  )
}

export function Empty({ icon: Icon, title, children }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 px-6 py-10 text-center">
      {Icon && <Icon className="mb-3 h-8 w-8 text-ink-3" />}
      <p className="font-medium text-white">{title}</p>
      {children && <div className="mt-1 text-sm text-ink-2">{children}</div>}
    </div>
  )
}

export function Field({ label, children }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
    </label>
  )
}

export function Modal({ open, title, onClose, children }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4 backdrop-blur-sm" onClick={onClose}>
      <div className="card w-full max-w-lg bg-[#0e1740]" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-bold text-white">{title}</h3>
          <button onClick={onClose} className="rounded-lg p-1 text-ink-2 hover:bg-white/10" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

/* ---------- toasts ---------- */
const ToastContext = createContext(() => {})

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const push = useCallback((message, type = 'success') => {
    const id = Math.random().toString(36).slice(2)
    setToasts((t) => [...t, { id, message, type }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3500)
  }, [])
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="fixed bottom-24 left-1/2 z-[60] flex -translate-x-1/2 flex-col gap-2">
        {toasts.map((t) => (
          <div key={t.id} className={`rounded-xl px-4 py-2.5 text-sm font-medium shadow-lg ${t.type === 'error' ? 'bg-rose-600 text-white' : 'bg-emerald-600 text-white'}`}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
export const useToast = () => useContext(ToastContext)

/** Shared course <select>. */
export function CourseSelect({ courses, value, onChange, allowAll = false, allLabel = 'All courses', required = false }) {
  return (
    <select className="input" value={value ?? ''} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)} required={required}>
      {allowAll ? <option value="">{allLabel}</option> : <option value="" disabled>Select a course</option>}
      {(courses || []).map((c) => (
        <option key={c.course_id} value={c.course_id}>
          {c.course_name}{c.course_code ? ` (${c.course_code})` : ''}
        </option>
      ))}
    </select>
  )
}
