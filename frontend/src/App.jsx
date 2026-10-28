import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { Spinner, ToastProvider } from './components/ui'
import { AuthProvider, useAuth } from './context/AuthContext'
import Admin from './pages/Admin'
import Assignments from './pages/Assignments'
import Assistant from './pages/Assistant'
import Attendance from './pages/Attendance'
import AuthPage from './pages/AuthPage'
import CalendarPage from './pages/CalendarPage'
import Courses from './pages/Courses'
import Dashboard from './pages/Dashboard'
import Grades from './pages/Grades'
import Insights from './pages/Insights'
import Planner from './pages/Planner'

function Protected({ children, role }) {
  const { user, ready } = useAuth()
  if (!ready) return <div className="grid h-screen place-items-center"><Spinner /></div>
  if (!user) return <Navigate to="/login" replace />
  if (role && user.role !== role) return <Navigate to="/" replace />
  return children
}

function PublicOnly({ children }) {
  const { user, ready } = useAuth()
  if (!ready) return null
  return user ? <Navigate to="/" replace /> : children
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<PublicOnly><AuthPage mode="login" /></PublicOnly>} />
            <Route path="/register" element={<PublicOnly><AuthPage mode="register" /></PublicOnly>} />
            <Route element={<Protected><Layout /></Protected>}>
              <Route index element={<Dashboard />} />
              <Route path="courses" element={<Courses />} />
              <Route path="assignments" element={<Assignments />} />
              <Route path="grades" element={<Grades />} />
              <Route path="attendance" element={<Attendance />} />
              <Route path="calendar" element={<CalendarPage />} />
              <Route path="planner" element={<Planner />} />
              <Route path="insights" element={<Insights />} />
              <Route path="assistant" element={<Assistant />} />
              <Route path="admin" element={<Protected role="admin"><Admin /></Protected>} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  )
}
