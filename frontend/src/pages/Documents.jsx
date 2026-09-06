import React, { useEffect, useState } from 'react'
import api from '../services/api'
import { useAuth } from '../services/auth'

export default function Documents(){
  const { token } = useAuth()
  const [documents, setDocuments] = useState([])
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)

  const load = () => {
    setLoading(true)
    api.get('/documents/', token).then(setDocuments).catch(err => setError(err.message)).finally(() => setLoading(false))
  }
  useEffect(load, [token])

  const upload = async (event) => {
    event.preventDefault()
    if (!file) return
    setUploading(true)
    setError(null)
    try {
      const document = await api.upload('/documents/upload', file, token)
      setDocuments(prev => [document, ...prev])
      setFile(null)
      event.target.reset()
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <main className="page-shell">
      <div className="page-heading"><div><div className="eyebrow">Reference library</div><h2>Documents</h2><p className="muted">Upload source material so the assistant can retrieve relevant context later.</p></div></div>
      <section className="upload-panel">
        <form className="upload-form" onSubmit={upload}>
          <label>Select a PDF, DOCX, or TXT file<input type="file" accept=".pdf,.docx,.txt" onChange={event => setFile(event.target.files[0] || null)} /></label>
          <button type="submit" disabled={!file || uploading}>{uploading ? 'Processing...' : 'Upload document'}</button>
        </form>
        {error && <div className="error-banner">{error}</div>}
      </section>
      <section className="document-list">
        <div className="section-heading"><h3>Your documents</h3><button className="quiet-button" onClick={load}>Refresh</button></div>
        {loading && <div className="empty-state">Loading documents...</div>}
        {!loading && documents.length === 0 && <div className="empty-state">No documents yet. Upload a study source to begin.</div>}
        {documents.map(document => <article className="document-row" key={document.id}><div><strong>{document.filename}</strong><span>{document.file_type.toUpperCase()} · {document.chunk_count || 0} chunks</span></div><span className={`status-pill status-${document.status}`}>{document.status}</span></article>)}
      </section>
    </main>
  )
}
