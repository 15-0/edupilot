import { Bot, FileText, Loader2, Trash2, UploadCloud } from 'lucide-react'
import { useRef, useState } from 'react'
import ChatPanel from '../components/ChatPanel'
import { Card, CourseSelect, Empty, ErrorBox, PageHeader, Spinner, useToast } from '../components/ui'
import api, { errorMessage } from '../lib/api'
import { fmtDate, useApi } from '../lib/hooks'

const MAX_MB = 10

export default function Assistant() {
  const toast = useToast()
  const docs = useApi('/documents')
  const courses = useApi('/courses')
  const status = useApi('/ai/status')
  const [courseId, setCourseId] = useState(null)
  const [scopeDoc, setScopeDoc] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [drag, setDrag] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

  const upload = async (file) => {
    if (!file) return
    setError('')
    if (!/\.(pdf|txt|md)$/i.test(file.name)) return setError('Only PDF, TXT and MD files are supported')
    if (file.size > MAX_MB * 1024 * 1024) return setError(`File is larger than ${MAX_MB} MB`)
    const body = new FormData()
    body.append('file', file)
    if (courseId) body.append('course_id', String(courseId))
    setUploading(true)
    try {
      const { data } = await api.post('/documents', body)
      toast(`Indexed ${data.filename} (${data.chunk_count} passages)`)
      docs.reload()
    } catch (err) { setError(errorMessage(err)) } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const remove = async (d) => {
    if (!window.confirm(`Delete ${d.filename}?`)) return
    try { await api.delete(`/documents/${d.document_id}`); if (scopeDoc === d.document_id) setScopeDoc(null); docs.reload() }
    catch (err) { toast(errorMessage(err), 'error') }
  }

  return (
    <div>
      <PageHeader title="AI Study Assistant" subtitle="Upload lecture notes and ask questions - answers cite your material" />
      {status.data && !status.data.llm_enabled && (
        <div className="mb-6 rounded-xl border border-cyan-400/30 bg-cyan-500/10 p-3 text-sm text-cyan-100">
          AI answers are off on the server (no ANTHROPIC_API_KEY), so the assistant will show the most relevant passages instead.
        </div>
      )}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6">
          <Card title="Upload material" icon={UploadCloud}>
            <div className="mb-3"><CourseSelect courses={courses.data} value={courseId} onChange={setCourseId} allowAll allLabel="No specific course" /></div>
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files?.[0]) }}
              className={`flex w-full flex-col items-center rounded-xl border-2 border-dashed px-4 py-8 text-center transition ${drag ? 'border-cyan-400 bg-cyan-500/10' : 'border-white/15 hover:bg-white/[0.04]'}`}
              disabled={uploading}
            >
              {uploading ? <Loader2 className="mb-2 h-8 w-8 animate-spin text-cyan-300" /> : <FileText className="mb-2 h-8 w-8 text-ink-2" />}
              <span className="font-medium text-white">{uploading ? 'Processing...' : 'Drag & drop a PDF here, or click to select'}</span>
              <span className="mt-1 text-xs text-ink-3">PDF, TXT or MD · max {MAX_MB} MB</span>
            </button>
            <input ref={inputRef} type="file" accept=".pdf,.txt,.md" className="hidden" onChange={(e) => upload(e.target.files?.[0])} />
            <div className="mt-3"><ErrorBox message={error} /></div>
          </Card>
          <Card title="Your documents">
            {docs.loading && !docs.data ? <Spinner /> : !docs.data?.length ? <Empty icon={FileText} title="No documents yet" /> : (
              <ul className="space-y-2">
                {docs.data.map((d) => (
                  <li key={d.document_id} className={`flex items-center gap-2 rounded-lg p-2 ${scopeDoc === d.document_id ? 'bg-purple-500/15 ring-1 ring-purple-400/40' : 'bg-white/[0.03]'}`}>
                    <button className="min-w-0 flex-1 text-left" onClick={() => setScopeDoc(scopeDoc === d.document_id ? null : d.document_id)} title="Ask only about this document">
                      <p className="truncate text-sm font-medium text-white">{d.filename}</p>
                      <p className="text-xs text-ink-3">{d.page_count} page{d.page_count === 1 ? '' : 's'} · {d.chunk_count} passages · {fmtDate(d.upload_date?.slice(0, 10))}</p>
                    </button>
                    <button className="rounded p-1.5 text-rose-400 hover:bg-rose-500/10" onClick={() => remove(d)} aria-label="Delete"><Trash2 className="h-4 w-4" /></button>
                  </li>
                ))}
              </ul>
            )}
            {docs.data?.length > 0 && <p className="mt-2 text-xs text-ink-3">Tip: click a document to ask questions about it only.</p>}
          </Card>
        </div>
        <Card title="Chat" icon={Bot} className="lg:col-span-2"
          subtitle={scopeDoc ? `Searching: ${docs.data?.find((d) => d.document_id === scopeDoc)?.filename}` : courseId ? 'Searching documents for the selected course' : 'Searching all your documents'}>
          <ChatPanel key={`${scopeDoc}-${courseId}`} scope={scopeDoc ? { document_ids: [scopeDoc] } : courseId ? { course_id: courseId } : {}} />
        </Card>
      </div>
    </div>
  )
}
