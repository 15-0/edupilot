import { Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ErrorBox, Field } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { errorMessage } from '../lib/api'

export default function AuthPage({ mode }) {
  const isLogin = mode === 'login'
  const { login, register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'student' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (isLogin) await login(form.email, form.password)
      else await register(form)
      navigate('/')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-screen place-items-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 shadow-lg shadow-blue-500/30">
            <Sparkles className="h-7 w-7 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">EduPilot AI</h1>
          <p className="mt-1 text-ink-2">Your intelligent academic co-pilot</p>
        </div>
        <form onSubmit={submit} className="card space-y-4">
          <h2 className="text-xl font-bold text-white">{isLogin ? 'Welcome back' : 'Create your account'}</h2>
          {!isLogin && (
            <Field label="Full name"><input className="input" value={form.name} onChange={set('name')} required maxLength={120} /></Field>
          )}
          <Field label="Email"><input className="input" type="email" value={form.email} onChange={set('email')} required autoComplete="email" /></Field>
          <Field label="Password">
            <input className="input" type="password" value={form.password} onChange={set('password')} required minLength={isLogin ? 1 : 8}
              autoComplete={isLogin ? 'current-password' : 'new-password'} placeholder={isLogin ? '' : 'At least 8 characters'} />
          </Field>
          {!isLogin && (
            <Field label="I am a">
              <select className="input" value={form.role} onChange={set('role')}>
                <option value="student">Student</option>
                <option value="instructor">Instructor</option>
              </select>
            </Field>
          )}
          <ErrorBox message={error} />
          <button className="btn-primary w-full" disabled={busy}>{busy ? 'Please wait...' : isLogin ? 'Log in' : 'Sign up'}</button>
          <p className="text-center text-sm text-ink-2">
            {isLogin ? "Don't have an account? " : 'Already registered? '}
            <Link className="font-medium text-cyan-300 hover:underline" to={isLogin ? '/register' : '/login'}>
              {isLogin ? 'Sign up' : 'Log in'}
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}
