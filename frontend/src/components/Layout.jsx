import {
  BarChart3, BookOpen, Bot, CalendarDays, ClipboardCheck, GraduationCap, Home, LogOut, Menu,
  NotebookPen, Shield, Sparkles, UserCheck, X,
} from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import ChatWidget from './ChatWidget'

export const NAV = [
  { to: '/', label: 'Home', icon: Home },
  { to: '/courses', label: 'Courses', icon: BookOpen },
  { to: '/assignments', label: 'Assignments', icon: ClipboardCheck },
  { to: '/grades', label: 'Grades', icon: GraduationCap },
  { to: '/attendance', label: 'Attendance', icon: UserCheck },
  { to: '/calendar', label: 'Calendar', icon: CalendarDays },
  { to: '/planner', label: 'Study Planner', icon: NotebookPen },
  { to: '/insights', label: 'AI Insights', icon: BarChart3 },
  { to: '/assistant', label: 'AI Assistant', icon: Bot },
]

function Logo() {
  return (
    <div className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 shadow-lg shadow-blue-500/30">
      <Sparkles className="h-6 w-6 text-white" />
    </div>
  )
}

function NavItems({ onNavigate, expanded, isAdmin }) {
  const items = isAdmin ? [...NAV, { to: '/admin', label: 'Admin', icon: Shield }] : NAV
  return items.map(({ to, label, icon: Icon }) => (
    <NavLink
      key={to}
      to={to}
      end={to === '/'}
      onClick={onNavigate}
      title={label}
      className={({ isActive }) =>
        `group flex items-center gap-3 rounded-xl p-3 transition ${
          isActive ? 'bg-white/10 text-white shadow-inner' : 'text-ink-2 hover:bg-white/5 hover:text-white'
        }`
      }
    >
      <Icon className="h-5 w-5 shrink-0" />
      {expanded && <span className="text-sm font-medium">{label}</span>}
    </NavLink>
  ))
}

export default function Layout() {
  const { user, logout } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)
  const { pathname } = useLocation()
  const current = [...NAV, { to: '/admin', label: 'Admin' }].find((n) => (n.to === '/' ? pathname === '/' : pathname.startsWith(n.to)))
  const initials = user?.name?.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()

  return (
    <div className="flex min-h-full">
      {/* Desktop icon rail */}
      <aside className="sticky top-0 hidden h-screen w-[88px] shrink-0 flex-col items-center gap-2 border-r border-white/5 bg-[#060b22]/70 py-5 backdrop-blur md:flex">
        <Logo />
        <nav className="mt-6 flex flex-1 flex-col gap-1.5">
          <NavItems isAdmin={user?.role === 'admin'} />
        </nav>
        <button onClick={logout} title="Log out" className="rounded-xl p-3 text-ink-2 hover:bg-white/5 hover:text-white">
          <LogOut className="h-5 w-5" />
        </button>
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 bg-black/60 md:hidden" onClick={() => setMobileOpen(false)}>
          <aside className="h-full w-64 bg-[#081030] p-4" onClick={(e) => e.stopPropagation()}>
            <div className="mb-6 flex items-center justify-between">
              <Logo />
              <button onClick={() => setMobileOpen(false)} aria-label="Close menu"><X className="h-6 w-6" /></button>
            </div>
            <nav className="flex flex-col gap-1">
              <NavItems expanded isAdmin={user?.role === 'admin'} onNavigate={() => setMobileOpen(false)} />
            </nav>
            <button onClick={logout} className="mt-4 flex items-center gap-3 p-3 text-ink-2"><LogOut className="h-5 w-5" /> Log out</button>
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-white/5 bg-[#070d26]/60 px-4 py-4 backdrop-blur md:px-10">
          <div className="flex items-center gap-3">
            <button className="md:hidden" onClick={() => setMobileOpen(true)} aria-label="Open menu"><Menu className="h-6 w-6" /></button>
            <div>
              <p className="text-xl font-bold leading-tight text-white">EduPilot AI</p>
              <p className="text-xs text-ink-2">{current?.label || ''}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium text-white">{user?.name}</p>
              <p className="text-xs capitalize text-ink-3">{user?.role}</p>
            </div>
            <div className="grid h-11 w-11 place-items-center rounded-full bg-gradient-to-br from-pink-500 to-purple-600 font-bold text-white">
              {initials}
            </div>
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 md:px-10">
          <Outlet />
        </main>
      </div>
      <ChatWidget />
    </div>
  )
}
