import {
  Award, BookOpen, CalendarClock, CheckCircle2, Circle, Clock, FileText, GraduationCap, Play, Sparkles, TrendingUp, Upload,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { BarSeries, LineSeries } from '../components/charts'
import { Badge, Card, Empty, ErrorBox, RiskBadge, Spinner, StatCard, useToast } from '../components/ui'
import api, { errorMessage } from '../lib/api'
import { fmtDate, useApi } from '../lib/hooks'

const QUIPS = [
  "Ah, we meet again. That syllabus isn't going to read itself, apparently.",
  'Small steps every day beat cramming the night before.',
  "Future you is already grateful for today's study session.",
  'Consistency is a superpower. Let us keep the streak alive.',
]

function greeting() {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'
}

export default function Dashboard() {
  const navigate = useNavigate()
  const toast = useToast()
  const { data, loading, error, reload } = useApi('/dashboard')

  if (loading && !data) return <Spinner />
  if (error) return <ErrorBox message={error} onRetry={reload} />

  const { stats, courses, upcoming_assignments: upcoming, weekly_study_hours: weekly, grade_trend: trend, today_plan: plan, user } = data
  const level = stats.overall_average == null ? 'Getting started' : stats.overall_average >= 85 ? 'Advanced' : stats.overall_average >= 65 ? 'Intermediate' : 'Building up'

  const toggleTask = async (task) => {
    try {
      await api.patch(`/ai/study-plan/${plan.plan_id}/tasks/${task.id}`, { done: !task.done })
      reload()
    } catch (err) {
      toast(errorMessage(err), 'error')
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-white md:text-5xl">
            {greeting()}, {user.name.split(' ')[0]}! <span className="inline-block">👋</span>
          </h1>
          <p className="mt-3 text-lg text-ink-2">{QUIPS[new Date().getDate() % QUIPS.length]}</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-ink-2">Current Level</p>
          <p className="bg-gradient-to-r from-cyan-300 to-blue-400 bg-clip-text text-3xl font-bold text-transparent">{level}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Courses Enrolled" value={stats.course_count} icon={Award} tone="pink" hint={`${stats.pending_assignments} pending assignments`} />
        <StatCard label="Study Streak" value={`${stats.study_streak} day${stats.study_streak === 1 ? '' : 's'}`} icon={TrendingUp} tone="cyan" />
        <StatCard label="Study Time (this week)" value={`${stats.study_hours_this_week}h`} icon={Clock} tone="purple" hint={`${stats.total_study_hours}h total`} />
        <StatCard label="Average Score" value={stats.overall_average == null ? '-' : `${stats.overall_average}%`} icon={FileText} tone="green"
          hint={stats.attendance_rate == null ? 'No attendance yet' : `Attendance ${stats.attendance_rate}%`} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card title="Your Courses" icon={GraduationCap} subtitle={`Showing ${courses.length} course${courses.length === 1 ? '' : 's'}`} className="lg:col-span-2">
          {courses.length === 0 ? (
            <Empty icon={BookOpen} title="No courses yet">
              <button className="btn-primary mt-3" onClick={() => navigate('/courses')}>Add your first course</button>
            </Empty>
          ) : (
            <div className="space-y-3">
              {courses.map((c) => (
                <div key={c.course_id} className="flex flex-wrap items-center gap-4 rounded-xl border border-white/5 bg-white/[0.03] p-4">
                  <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-pink-500 to-purple-600">
                    <GraduationCap className="h-6 w-6 text-white" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-lg font-bold text-white">{c.course_name}</p>
                    <p className="text-sm text-ink-2">
                      {c.course_code || 'No code'} · Avg {c.average == null ? '-' : `${c.average}%`}
                      {c.predicted_score != null && <> · Est. {c.predicted_score}%</>}
                    </p>
                  </div>
                  <RiskBadge level={c.risk_level} />
                  <div className="flex gap-2">
                    <button className="btn-green btn-sm" onClick={() => navigate('/planner')}><Play className="h-3.5 w-3.5" /> Study</button>
                    <button className="btn-primary btn-sm" onClick={() => navigate('/assistant')}><Sparkles className="h-3.5 w-3.5" /> Ask AI</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Quick Actions" subtitle="Jump into your studies">
          <div className="space-y-3">
            <button className="btn-pink w-full justify-start py-4" onClick={() => navigate('/planner')}><Play className="h-5 w-5" /> Start Study Session</button>
            <button className="btn-primary w-full justify-start py-4" onClick={() => navigate('/insights')}><TrendingUp className="h-5 w-5" /> View Predictions</button>
            <button className="btn-purple w-full justify-start py-4" onClick={() => navigate('/assistant')}><Upload className="h-5 w-5" /> Upload Materials</button>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Study hours per week" subtitle="Last 8 weeks">
          <BarSeries data={weekly} x="week" y="hours" unit=" h" />
        </Card>
        <Card title="Grade trend" subtitle="Your last 20 assessments (%)">
          {trend.length ? <LineSeries data={trend} x="date" y="percentage" labelKey="title" refY={70} />
            : <Empty icon={GraduationCap} title="No grades yet">Add grades to see your trend.</Empty>}
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Upcoming deadlines" icon={CalendarClock} action={<button className="btn-ghost btn-sm" onClick={() => navigate('/assignments')}>All</button>}>
          {upcoming.length === 0 ? <Empty title="Nothing due">You're all caught up.</Empty> : (
            <ul className="divide-y divide-white/5">
              {upcoming.map((a) => (
                <li key={a.assignment_id} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-white">{a.title}</p>
                    <p className="text-xs text-ink-2">{a.course_name}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {a.is_overdue ? <Badge kind="overdue">Overdue</Badge> : <Badge kind={a.priority}>{a.priority}</Badge>}
                    <span className="text-sm text-ink-2">{fmtDate(a.due_date)}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Today's study plan" icon={Sparkles} action={<button className="btn-ghost btn-sm" onClick={() => navigate('/planner')}>Planner</button>}>
          {!plan || plan.tasks.length === 0 ? (
            <Empty title="No plan for today">
              <button className="btn-purple mt-3" onClick={() => navigate('/planner')}>Generate a weekly plan</button>
            </Empty>
          ) : (
            <ul className="space-y-2">
              {plan.tasks.map((t) => (
                <li key={t.id}>
                  <button onClick={() => toggleTask(t)} className="flex w-full items-start gap-3 rounded-xl bg-white/[0.03] p-3 text-left hover:bg-white/[0.06]">
                    {t.done ? <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-400" /> : <Circle className="mt-0.5 h-5 w-5 text-ink-3" />}
                    <div>
                      <p className={`text-sm font-medium ${t.done ? 'text-ink-3 line-through' : 'text-white'}`}>{t.title}</p>
                      <p className="text-xs text-ink-2">{t.course_name} · {t.minutes} min</p>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}
