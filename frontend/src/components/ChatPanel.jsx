import { Bot, FileText, Loader2, Send } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import api, { errorMessage } from '../lib/api'

/** Chat with uploaded notes (RAG). `scope` limits retrieval to documents/course. */
export default function ChatPanel({ scope = {}, compact = false }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Hi! Ask me anything about the lecture notes you've uploaded and I'll answer with citations." },
  ])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy])

  const send = async (e) => {
    e.preventDefault()
    const question = input.trim()
    if (!question || busy) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: question }])
    setBusy(true)
    try {
      const { data } = await api.post('/documents/chat', { question, ...scope })
      setMessages((m) => [...m, { role: 'assistant', content: data.answer, sources: data.sources, mode: data.mode }])
    } catch (err) {
      setMessages((m) => [...m, { role: 'assistant', content: `Sorry - ${errorMessage(err)}`, error: true }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className={`flex flex-col ${compact ? 'h-[460px]' : 'h-[600px]'}`}>
      <div className="flex-1 space-y-4 overflow-y-auto pr-1">
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : ''}`}>
            {m.role === 'assistant' && (
              <div className="mt-1 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-gradient-to-br from-pink-500 to-purple-600">
                <Bot className="h-4 w-4 text-white" />
              </div>
            )}
            <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
              m.role === 'user' ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white'
                : m.error ? 'bg-rose-500/15 text-rose-200' : 'bg-white/[0.07] text-ink'
            }`}>
              <div className="markdown"><ReactMarkdown>{m.content}</ReactMarkdown></div>
              {m.sources?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5 border-t border-white/10 pt-2">
                  {m.sources.map((s) => (
                    <span key={s.ref} title={s.snippet} className="inline-flex items-center gap-1 rounded-md bg-white/10 px-1.5 py-0.5 text-[11px] text-ink-2">
                      <FileText className="h-3 w-3" /> [{s.ref}] {s.filename}{s.page_number ? ` p.${s.page_number}` : ''}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && <div className="flex items-center gap-2 text-sm text-ink-2"><Loader2 className="h-4 w-4 animate-spin" /> Reading your notes...</div>}
        <div ref={endRef} />
      </div>
      <form onSubmit={send} className="mt-3 flex gap-2">
        <input className="input" placeholder="e.g. Explain the phases of mitosis" value={input} onChange={(e) => setInput(e.target.value)} maxLength={2000} />
        <button className="btn-purple" disabled={busy || !input.trim()} aria-label="Send"><Send className="h-4 w-4" /></button>
      </form>
    </div>
  )
}
