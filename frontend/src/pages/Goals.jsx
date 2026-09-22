import React, { useEffect, useState } from 'react'
import api from '../services/api'
import { useAuth } from '../services/auth'

function TaskItem({ task, onUpdate, token, onToast }) {
  const [busy, setBusy] = useState(false)

  const handleComplete = async () => {
    setBusy(true)
    try {
      const updated = await api.patch(`/tasks/${task.id}`, { status: 'completed' }, token)
      onUpdate(updated)
      onToast(`✓ Completed "${task.title}" — evidence recorded toward your knowledge state!`)
    } catch (ex) {
      alert('Failed to complete task: ' + ex.message)
    } finally {
      setBusy(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm('Delete task?')) return
    try {
      await api.del(`/tasks/${task.id}`, token)
      onUpdate({ ...task, _deleted: true })
    } catch (ex) {
      alert('Failed to delete task: ' + ex.message)
    }
  }

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '10px 14px',
      background: task.status === 'completed' ? 'rgba(16, 185, 129, 0.08)' : 'rgba(18, 14, 42, 0.65)',
      border: '1px solid ' + (task.status === 'completed' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(139, 92, 246, 0.2)'),
      borderRadius: 10,
      marginBottom: 8,
      fontSize: '0.9em',
      boxShadow: '0 4px 14px rgba(0, 0, 0, 0.2)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <input
          type="checkbox"
          checked={task.status === 'completed'}
          disabled={task.status === 'completed' || busy}
          onChange={handleComplete}
          style={{ accentColor: 'var(--coral)', width: 16, height: 16, cursor: 'pointer' }}
        />
        <span style={{
          textDecoration: task.status === 'completed' ? 'line-through' : 'none',
          color: task.status === 'completed' ? 'var(--muted)' : '#ffffff',
          fontWeight: 500
        }}>
          {task.title}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {task.status === 'completed' && (
          <span style={{
            fontSize: '0.74em',
            background: 'rgba(16, 185, 129, 0.2)',
            color: '#34d399',
            border: '1px solid rgba(16, 185, 129, 0.35)',
            padding: '2px 8px',
            borderRadius: 9999,
            fontWeight: 700,
            letterSpacing: '0.04em'
          }}>
            Evidence Emitted
          </span>
        )}
        <button
          onClick={handleDelete}
          style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '0.85em', padding: 0, boxShadow: 'none' }}
          title="Delete task"
        >
          ✕
        </button>
      </div>
    </div>
  )
}

function TaskCreator({ goalId, onCreated, token, concepts }) {
  const [title, setTitle] = useState('')
  const [selectedConcept, setSelectedConcept] = useState('')
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!title.trim() || saving) return
    setSaving(true)
    try {
      const payload = {
        title: title.trim(),
        goal_id: goalId,
        related_concept_ids: selectedConcept ? [Number(selectedConcept)] : []
      }
      const created = await api.post('/tasks/', payload, token)
      setTitle('')
      setSelectedConcept('')
      onCreated(created)
    } catch (ex) {
      alert('Failed to create task: ' + ex.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 8, marginTop: 10 }}>
      <input
        type="text"
        placeholder="Add actionable task..."
        value={title}
        onChange={e => setTitle(e.target.value)}
        style={{ flex: 1, padding: '8px 12px', fontSize: '0.88em', border: '1px solid rgba(139, 92, 246, 0.28)', borderRadius: 8, background: 'rgba(15, 12, 33, 0.7)', color: '#ffffff' }}
      />
      {concepts.length > 0 && (
        <select
          value={selectedConcept}
          onChange={e => setSelectedConcept(e.target.value)}
          style={{ padding: '8px 10px', fontSize: '0.82em', border: '1px solid rgba(139, 92, 246, 0.28)', borderRadius: 8, background: '#151131', color: '#ffffff' }}
        >
          <option value="">Link concept...</option>
          {concepts.map(c => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      )}
      <button type="submit" disabled={!title.trim() || saving} style={{ padding: '8px 16px', fontSize: '0.85em' }}>
        Add
      </button>
    </form>
  )
}

function GoalForm({ initial = {}, onSave, onCancel, token }) {
  const [title, setTitle] = useState(initial.title || '')
  const [description, setDescription] = useState(initial.description || '')
  const [priority, setPriority] = useState(initial.priority || 'medium')
  const [progress, setProgress] = useState(initial.progress ?? 0)
  const [status, setStatus] = useState(initial.status || 'not_started')
  const [err, setErr] = useState(null)

  const submit = async (e) => {
    e && e.preventDefault()
    setErr(null)
    try {
      const body = initial.id
        ? { title, description, priority, progress, status }
        : { title, description, priority, progress }
      if (initial.id) {
        const updated = await api.patch(`/goals/${initial.id}`, body, token)
        onSave(updated)
      } else {
        const created = await api.post('/goals/', body, token)
        setTitle('')
        setDescription('')
        setPriority('medium')
        setProgress(0)
        onSave(created)
      }
    } catch (ex) { setErr(ex.message) }
  }

  return (
    <form className="editor-form" onSubmit={submit} style={{ border: '1px solid rgba(139, 92, 246, 0.25)', borderRadius: 16, padding: 18, marginBottom: 20, background: 'rgba(24, 19, 53, 0.7)', backdropFilter: 'blur(16px)', boxShadow: '0 20px 45px -15px rgba(5, 4, 15, 0.7)' }}>
      <div style={{ marginBottom: 8, width: '100%' }}>
        <input placeholder="Goal Title (e.g. Master Algorithms)" value={title} onChange={e => setTitle(e.target.value)} style={{ width: '100%', padding: '10px 14px' }} />
      </div>
      <div style={{ marginBottom: 8, width: '100%' }}>
        <input placeholder="Description or target criteria" value={description} onChange={e => setDescription(e.target.value)} style={{ width: '100%', padding: '10px 14px' }} />
      </div>
      <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' }}>
        <div>
          <label style={{ marginRight: 6 }}>Priority:</label>
          <select value={priority} onChange={e => setPriority(e.target.value)}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
        <div>
          <label style={{ marginRight: 6 }}>Progress:</label>
          <input type="range" min={0} max={1} step={0.05} value={progress} onChange={e => setProgress(Number(e.target.value))} />
          <span style={{ marginLeft: 8, fontWeight: 700, color: 'var(--coral)', fontFamily: "'Space Grotesk', sans-serif" }}>{Math.round(progress * 100)}%</span>
        </div>
        {initial.id && (
          <div>
            <label style={{ marginRight: 6 }}>Status:</label>
            <select value={status} onChange={e => setStatus(e.target.value)}>
              <option value="not_started">Not Started</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="abandoned">Abandoned</option>
            </select>
          </div>
        )}
      </div>
      <div>
        <button type="submit">{initial.id ? 'Save Changes' : 'Create Goal'}</button>
        {initial.id && onCancel && <button type="button" onClick={onCancel} style={{ marginLeft: 10, background: 'rgba(255, 255, 255, 0.08)', border: '1px solid rgba(139, 92, 246, 0.25)', color: '#e2e8f0', boxShadow: 'none' }}>Cancel</button>}
      </div>
      {err && <div style={{ color: '#fca5a5', marginTop: 8 }}>{err}</div>}
    </form>
  )
}

export default function Goals() {
  const { token } = useAuth()
  const [goals, setGoals] = useState([])
  const [tasks, setTasks] = useState([])
  const [concepts, setConcepts] = useState([])
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState(null)
  const [toast, setToast] = useState(null)

  const showToast = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  const loadData = () => {
    if (!token) return
    setLoading(true)
    Promise.all([
      api.get('/goals/', token).catch(() => []),
      api.get('/tasks/', token).catch(() => []),
      api.get('/concepts/', token).catch(() => []),
    ])
      .then(([gList, tList, cList]) => {
        setGoals(gList || [])
        setTasks(tList || [])
        setConcepts(cList || [])
      })
      .finally(() => setLoading(false))
  }

  useEffect(loadData, [token])

  const handleSaveGoal = (savedGoal) => {
    setGoals(prev => {
      const idx = prev.findIndex(x => x.id === savedGoal.id)
      if (idx >= 0) { const copy = [...prev]; copy[idx] = savedGoal; return copy }
      return [savedGoal, ...prev]
    })
    setEditing(null)
  }

  const handleTaskUpdate = (updatedTask) => {
    setTasks(prev => {
      if (updatedTask._deleted) {
        return prev.filter(t => t.id !== updatedTask.id)
      }
      return prev.map(t => t.id === updatedTask.id ? updatedTask : t)
    })
  }

  const handleTaskCreated = (newTask) => {
    setTasks(prev => [newTask, ...prev])
  }

  return (
    <main className="page-shell" style={{ padding: 24 }}>
      <div className="page-heading">
        <div>
          <div className="eyebrow">Execution & Evidence</div>
          <h2>Goals & Tasks</h2>
          <p className="muted">
            Completing tasks automatically provides evidence to your Knowledge Concepts.
          </p>
        </div>
      </div>

      {toast && (
        <div style={{
          padding: '12px 18px',
          background: 'rgba(16, 185, 129, 0.18)',
          color: '#34d399',
          border: '1px solid rgba(16, 185, 129, 0.45)',
          borderRadius: 12,
          marginBottom: 20,
          fontWeight: 600,
          boxShadow: '0 8px 30px rgba(16, 185, 129, 0.25)'
        }}>
          {toast}
        </div>
      )}

      <GoalForm onSave={handleSaveGoal} token={token} />

      {loading && <div>Loading your momentum...</div>}
      {goals.length === 0 && !loading && (
        <div className="empty-state">No goals created yet. Create a goal and attach actionable tasks.</div>
      )}

      <div className="goal-list" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {goals.map(g => {
          const goalTasks = tasks.filter(t => t.goal_id === g.id)
          const completedCount = goalTasks.filter(t => t.status === 'completed').length

          return (
            <div key={g.id} style={{
              border: '1px solid rgba(139, 92, 246, 0.22)',
              borderRadius: 18,
              padding: 22,
              background: 'rgba(22, 18, 48, 0.65)',
              backdropFilter: 'blur(16px)',
              boxShadow: '0 20px 45px -15px rgba(5, 4, 15, 0.7)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.2em', color: '#ffffff' }}>
                    {g.title}
                  </h3>
                  {g.description && <p style={{ margin: '6px 0', fontSize: '0.92em', color: 'var(--muted)' }}>{g.description}</p>}
                  <div style={{ fontSize: '0.84em', color: 'var(--muted)', marginTop: 8, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                    <span style={{ background: 'rgba(139, 92, 246, 0.2)', color: '#c4b5fd', border: '1px solid rgba(139, 92, 246, 0.35)', padding: '2px 10px', borderRadius: 9999, fontWeight: 700, textTransform: 'capitalize' }}>{g.status.replace('_', ' ')}</span>
                    <span style={{ background: 'rgba(255, 107, 74, 0.15)', color: 'var(--coral)', border: '1px solid rgba(255, 107, 74, 0.35)', padding: '2px 10px', borderRadius: 9999, fontWeight: 700 }}>Priority: {g.priority}</span>
                    <span style={{ background: 'rgba(255, 255, 255, 0.06)', color: '#e2e8f0', border: '1px solid rgba(255, 255, 255, 0.1)', padding: '2px 10px', borderRadius: 9999, fontWeight: 600 }}>Tasks: {completedCount}/{goalTasks.length} done</span>
                  </div>
                </div>
                <div>
                  <button
                    className="quiet-button"
                    onClick={() => setEditing(editing && editing.id === g.id ? null : g)}
                    style={{ fontSize: '0.82em', padding: '6px 14px' }}
                  >
                    {editing && editing.id === g.id ? 'Close' : 'Edit Goal'}
                  </button>
                </div>
              </div>

              {editing && editing.id === g.id && (
                <div style={{ marginTop: 16 }}>
                  <GoalForm initial={editing} onSave={handleSaveGoal} onCancel={() => setEditing(null)} token={token} />
                </div>
              )}

              {/* Tasks section under this goal */}
              <div style={{ marginTop: 18, paddingTop: 14, borderTop: '1px solid rgba(148, 163, 184, 0.12)' }}>
                <h4 style={{ margin: '0 0 10px 0', fontSize: '0.85em', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Tasks & Evidence</h4>
                {goalTasks.length === 0 ? (
                  <div style={{ fontSize: '0.85em', color: 'var(--muted)', fontStyle: 'italic', marginBottom: 8 }}>
                    No tasks under this goal yet.
                  </div>
                ) : (
                  <div>
                    {goalTasks.map(t => (
                      <TaskItem
                        key={t.id}
                        task={t}
                        onUpdate={handleTaskUpdate}
                        token={token}
                        onToast={showToast}
                      />
                    ))}
                  </div>
                )}
                <TaskCreator
                  goalId={g.id}
                  onCreated={handleTaskCreated}
                  token={token}
                  concepts={concepts}
                />
              </div>
            </div>
          )
        })}
      </div>
    </main>
  )
}
