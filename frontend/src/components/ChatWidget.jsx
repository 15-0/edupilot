import { MessageCircle, X } from 'lucide-react'
import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import ChatPanel from './ChatPanel'

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()
  if (pathname.startsWith('/assistant')) return null

  return (
    <>
      {open && (
        <div className="card fixed bottom-24 right-4 z-40 w-[calc(100vw-2rem)] max-w-md bg-[#0d1640]/95 p-4 md:right-8">
          <p className="mb-3 font-bold text-white">Ask your notes</p>
          <ChatPanel compact />
        </div>
      )}
      <button
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-6 right-4 z-40 grid h-16 w-16 place-items-center rounded-full bg-gradient-to-br from-pink-500 to-purple-600 text-white shadow-xl shadow-purple-900/50 transition hover:scale-105 md:right-8"
        aria-label={open ? 'Close assistant' : 'Open assistant'}
      >
        {open ? <X className="h-7 w-7" /> : <MessageCircle className="h-7 w-7" />}
      </button>
    </>
  )
}
