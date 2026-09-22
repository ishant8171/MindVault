import React, { useEffect, useState } from 'react'
import api from '../services/api'
import { useAuth } from '../services/auth'
import GraphView from '../components/GraphView'

export default function Dashboard() {
  const { token } = useAuth()
  const [dashboard, setDashboard] = useState(null)
  const [nodes, setNodes] = useState([])
  const [rels, setRels] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadData = () => {
    if (!token) return
    setLoading(true)
    setError(null)

    Promise.all([
      api.get('/dashboard/', token),
      api.get('/knowledge-graph/nodes', token).catch(() => []),
      api.get('/knowledge-graph/relationships', token).catch(() => []),
    ])
      .then(([dashData, nodeData, relData]) => {
        setDashboard(dashData)
        setNodes(nodeData || [])
        setRels(relData || [])
      })
      .catch(err => {
        setError(err.message)
      })
      .finally(() => {
        setLoading(false)
      })
  }

  useEffect(loadData, [token])

  if (loading) {
    return (
      <main className="page-shell dashboard-page" style={{ padding: 24 }}>
        <div className="empty-state">Assembling your knowledge reflection...</div>
      </main>
    )
  }

  if (error) {
    return (
      <main className="page-shell dashboard-page" style={{ padding: 24 }}>
        <div className="error-banner">Could not load reflection: {error}</div>
        <button onClick={loadData} style={{ marginTop: 12 }}>Try Again</button>
      </main>
    )
  }

  const reflections = dashboard?.reflections || []
  const currentFocus = dashboard?.current_focus
  const risingConcepts = dashboard?.rising_concepts || []
  const strugglingConcepts = dashboard?.stagnant_or_struggling_concepts || []
  const activePrefs = dashboard?.active_preferences || []
  const goalsNeedingAttention = dashboard?.goals_needing_attention || []

  return (
    <main className="page-shell dashboard-page" style={{ padding: 24 }}>
      <div className="page-heading">
        <div>
          <div className="eyebrow">Virtual Brain Reflection</div>
          <h2>Personal Knowledge Mirror</h2>
          <p className="muted">
            An evolving model of what you know, how you learn, and where your focus is shifting.
          </p>
        </div>
        <div>
          <button className="quiet-button" onClick={loadData}>Refresh Reflection</button>
        </div>
      </div>

      {/* Hero: Natural Language Reflection Statements */}
      <section className="dashboard-card hero-reflection-card" style={{
        background: 'rgba(26, 20, 58, 0.7)',
        border: '1px solid rgba(168, 85, 247, 0.3)',
        borderRadius: 18,
        padding: 24,
        marginBottom: 24,
        backdropFilter: 'blur(16px)',
        boxShadow: '0 20px 45px -15px rgba(5, 4, 15, 0.7), 0 0 30px -5px rgba(124, 58, 237, 0.18)'
      }}>
        <h3 style={{ marginTop: 0, color: '#ffffff', display: 'flex', alignItems: 'center', gap: 10 }}>
          <span>🧠</span> What MindVault Sees In You
        </h3>
        <ul style={{ listStyleType: 'none', paddingLeft: 0, margin: '14px 0 0 0' }}>
          {reflections.map((statement, idx) => (
            <li key={idx} style={{
              padding: '12px 18px',
              backgroundColor: 'rgba(16, 12, 38, 0.65)',
              borderRadius: 12,
              border: '1px solid rgba(139, 92, 246, 0.22)',
              borderLeft: '4px solid var(--coral)',
              marginBottom: 10,
              fontSize: '1.02em',
              lineHeight: 1.6,
              color: '#e2e8f0',
              boxShadow: '0 4px 16px rgba(0,0,0,0.25)'
            }}>
              "{statement}"
            </li>
          ))}
        </ul>
      </section>

      {/* Grid of Virtual Brain Insights */}
      <div className="dashboard-grid" style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: 20
      }}>

        {/* 1. Behavioral Focus Shifts */}
        <section className="dashboard-card" style={{
          background: 'rgba(22, 18, 48, 0.65)',
          border: '1px solid rgba(139, 92, 246, 0.22)',
          borderRadius: 18,
          padding: 22,
          backdropFilter: 'blur(16px)',
          boxShadow: '0 20px 45px -15px rgba(5, 4, 15, 0.7)'
        }}>
          <h3 style={{ marginTop: 0, fontSize: '1.1em', color: '#ffffff' }}>
            📊 Recent Focus Shift (14-Day Window)
          </h3>
          <p className="muted" style={{ fontSize: '0.85em', marginTop: -4 }}>
            Shifts in evidence volume comparing the last 14 days against the prior 14 days.
          </p>
          {(!currentFocus?.shifts || currentFocus.shifts.length === 0) ? (
            <div className="empty-state" style={{ padding: '16px 0', fontSize: '0.9em' }}>
              No focus shifts detected yet. Engage with tasks, questions, or notes to reveal patterns.
            </div>
          ) : (
            <div style={{ marginTop: 12 }}>
              {currentFocus.shifts.map((shift, idx) => (
                <div key={idx} style={{
                  padding: '12px 14px',
                  background: shift.share_change > 0 ? 'rgba(16, 185, 129, 0.08)' : 'rgba(18, 14, 42, 0.6)',
                  border: '1px solid ' + (shift.share_change > 0 ? 'rgba(16, 185, 129, 0.3)' : 'rgba(139, 92, 246, 0.2)'),
                  borderRadius: 12,
                  marginBottom: 10,
                  fontSize: '0.9em',
                  boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontWeight: 600 }}>
                    <span style={{ color: '#ffffff', fontSize: '0.95em' }}>{shift.concept_name}</span>
                    <span style={{
                      background: shift.share_change > 0 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.08)',
                      color: shift.share_change > 0 ? '#34d399' : 'var(--muted)',
                      border: '1px solid ' + (shift.share_change > 0 ? 'rgba(16, 185, 129, 0.4)' : 'rgba(255, 255, 255, 0.1)'),
                      padding: '3px 10px',
                      borderRadius: 9999,
                      fontSize: '0.8em',
                      fontWeight: 700,
                      letterSpacing: '0.02em',
                      boxShadow: shift.share_change > 0 ? '0 0 12px rgba(16, 185, 129, 0.25)' : 'none'
                    }}>
                      {shift.share_change > 0 ? `+${Math.round(shift.share_change * 100)}% share` : 'Equal share'}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.82em', color: 'var(--muted)', marginTop: 6, borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: 6 }}>
                    Recent signals: {shift.recent_count} ({Math.round(shift.recent_share * 100)}%) vs Earlier: {shift.earlier_count} ({Math.round(shift.earlier_share * 100)}%)
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 2. Rising Concepts */}
        <section className="dashboard-card" style={{
          background: 'rgba(22, 18, 48, 0.65)',
          border: '1px solid rgba(139, 92, 246, 0.22)',
          borderRadius: 18,
          padding: 22,
          backdropFilter: 'blur(16px)',
          boxShadow: '0 20px 45px -15px rgba(5, 4, 15, 0.7)'
        }}>
          <h3 style={{ marginTop: 0, fontSize: '1.1em', color: '#ffffff' }}>
            🚀 Rising Concepts (Growing Confidence)
          </h3>
          <p className="muted" style={{ fontSize: '0.85em', marginTop: -4 }}>
            Topics where your confidence has measurably climbed from accumulated evidence.
          </p>
          {risingConcepts.length === 0 ? (
            <div className="empty-state" style={{ padding: '16px 0', fontSize: '0.9em' }}>
              No rising concepts flagged yet. Complete tasks or chat with the assistant to build confidence.
            </div>
          ) : (
            <div style={{ marginTop: 12 }}>
              {risingConcepts.map(c => (
                <div key={c.id} style={{
                  padding: '14px 16px',
                  background: 'rgba(18, 14, 42, 0.65)',
                  border: '1px solid rgba(139, 92, 246, 0.25)',
                  borderRadius: 14,
                  marginBottom: 12,
                  boxShadow: '0 6px 20px rgba(0, 0, 0, 0.25)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong style={{ fontSize: '1.02em', color: '#ffffff', fontFamily: "'Space Grotesk', sans-serif" }}>{c.name}</strong>
                    <span style={{
                      background: 'rgba(255, 107, 74, 0.18)',
                      color: 'var(--coral)',
                      border: '1px solid rgba(255, 107, 74, 0.4)',
                      padding: '3px 10px',
                      borderRadius: 9999,
                      fontSize: '0.78em',
                      fontWeight: 700,
                      letterSpacing: '0.02em',
                      boxShadow: '0 0 12px var(--coral-glow)'
                    }}>
                      +{Math.round(c.confidence_gain * 100)}% gain
                    </span>
                  </div>
                  <div style={{ marginTop: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
                      <span style={{ fontSize: '0.74em', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--muted)', fontWeight: 600 }}>Confidence</span>
                      <span style={{ fontSize: '1.45rem', fontWeight: 800, fontFamily: "'Space Grotesk', sans-serif", color: '#ffffff', lineHeight: 1 }}>
                        {Math.round(c.current_confidence * 100)}<span style={{ fontSize: '0.9rem', color: 'var(--coral)' }}>%</span>
                      </span>
                    </div>
                    <div style={{ background: 'rgba(15, 12, 33, 0.8)', borderRadius: 9999, height: 7, overflow: 'hidden', border: '1px solid rgba(139, 92, 246, 0.2)' }}>
                      <div style={{ background: 'linear-gradient(90deg, #8b5cf6 0%, var(--coral) 100%)', width: `${Math.min(100, Math.round(c.current_confidence * 100))}%`, height: '100%', borderRadius: 9999, boxShadow: '0 0 10px var(--coral-glow)' }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 3. Stagnant / Struggling Concepts */}
        <section className="dashboard-card" style={{
          background: 'rgba(22, 18, 48, 0.65)',
          border: '1px solid rgba(245, 158, 11, 0.25)',
          borderRadius: 18,
          padding: 22,
          backdropFilter: 'blur(16px)',
          boxShadow: '0 20px 45px -15px rgba(5, 4, 15, 0.7)'
        }}>
          <h3 style={{ marginTop: 0, fontSize: '1.1em', color: '#ffffff' }}>
            ⚠️ Active Difficulty Areas
          </h3>
          <p className="muted" style={{ fontSize: '0.85em', marginTop: -4 }}>
            Topics with repeated practice attempts whose confidence hasn't consolidated yet.
          </p>
          {strugglingConcepts.length === 0 ? (
            <div className="empty-state" style={{ padding: '16px 0', fontSize: '0.9em', color: '#34d399' }}>
              ✓ No persistent struggle areas detected.
            </div>
          ) : (
            <div style={{ marginTop: 12 }}>
              {strugglingConcepts.map(c => (
                <div key={c.id} style={{
                  padding: '12px 14px',
                  background: 'rgba(245, 158, 11, 0.08)',
                  border: '1px solid rgba(245, 158, 11, 0.28)',
                  borderRadius: 12,
                  marginBottom: 10,
                  boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontWeight: 600 }}>
                    <span style={{ color: '#fef3c7', fontSize: '0.95em' }}>{c.name}</span>
                    <span style={{
                      background: 'rgba(245, 158, 11, 0.2)',
                      color: '#fbbf24',
                      border: '1px solid rgba(245, 158, 11, 0.4)',
                      padding: '3px 10px',
                      borderRadius: 9999,
                      fontSize: '0.78em',
                      fontWeight: 700
                    }}>
                      {c.evidence_count} attempts
                    </span>
                  </div>
                  <div style={{ fontSize: '0.82em', color: '#fde68a', marginTop: 6, lineHeight: 1.5 }}>
                    Confidence currently <strong style={{ color: '#ffffff' }}>{Math.round(c.confidence * 100)}%</strong> — assistant will adapt explanations for this gap.
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 4. Active Inferred Learning Preferences */}
        <section className="dashboard-card" style={{
          background: 'rgba(22, 18, 48, 0.65)',
          border: '1px solid rgba(139, 92, 246, 0.22)',
          borderRadius: 18,
          padding: 22,
          backdropFilter: 'blur(16px)',
          boxShadow: '0 20px 45px -15px rgba(5, 4, 15, 0.7)'
        }}>
          <h3 style={{ marginTop: 0, fontSize: '1.1em', color: '#ffffff' }}>
            🎯 Calibrated Learning Styles
          </h3>
          <p className="muted" style={{ fontSize: '0.85em', marginTop: -4 }}>
            How MindVault customizes tone and explanations for you.
          </p>
          {activePrefs.length === 0 ? (
            <div className="empty-state" style={{ padding: '16px 0', fontSize: '0.9em' }}>
              No preferences calibrated yet. Tell the assistant how you learn best or add preferences.
            </div>
          ) : (
            <div style={{ marginTop: 14, display: 'flex', flexWrap: 'wrap', gap: 10 }}>
              {activePrefs.map(p => (
                <div key={p.id} style={{
                  padding: '8px 14px',
                  background: 'rgba(30, 24, 66, 0.7)',
                  border: '1px solid rgba(168, 85, 247, 0.35)',
                  borderRadius: 9999,
                  fontSize: '0.85em',
                  color: '#ffffff',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  boxShadow: '0 4px 15px rgba(0, 0, 0, 0.3)'
                }}>
                  <span>💡</span>
                  <span style={{ fontWeight: 600 }}>{p.preference_type.replace(/_/g, ' ')}</span>
                  <span style={{ fontSize: '0.78em', color: 'var(--coral)', fontWeight: 700 }}>
                    ({Math.round(p.confidence * 100)}% match)
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 5. Goals Needing Attention */}
        <section className="dashboard-card" style={{
          background: 'rgba(22, 18, 48, 0.65)',
          border: '1px solid rgba(239, 68, 68, 0.25)',
          borderRadius: 18,
          padding: 22,
          backdropFilter: 'blur(16px)',
          boxShadow: '0 20px 45px -15px rgba(5, 4, 15, 0.7)'
        }}>
          <h3 style={{ marginTop: 0, fontSize: '1.1em', color: '#ffffff' }}>
            ⏳ Goals Needing Attention
          </h3>
          <p className="muted" style={{ fontSize: '0.85em', marginTop: -4 }}>
            Goals with upcoming deadlines or low progress requiring focus.
          </p>
          {goalsNeedingAttention.length === 0 ? (
            <div className="empty-state" style={{ padding: '16px 0', fontSize: '0.9em', color: '#34d399' }}>
              ✓ All active goals are on schedule.
            </div>
          ) : (
            <div style={{ marginTop: 12 }}>
              {goalsNeedingAttention.map(g => (
                <div key={g.id} style={{
                  padding: '12px 14px',
                  background: 'rgba(239, 68, 68, 0.08)',
                  border: '1px solid rgba(239, 68, 68, 0.28)',
                  borderRadius: 12,
                  marginBottom: 10,
                  boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontWeight: 600 }}>
                    <span style={{ color: '#fecaca', fontSize: '0.95em' }}>{g.title}</span>
                    <span style={{
                      background: 'rgba(239, 68, 68, 0.2)',
                      color: '#fca5a5',
                      border: '1px solid rgba(239, 68, 68, 0.4)',
                      padding: '3px 10px',
                      borderRadius: 9999,
                      fontSize: '0.8em',
                      fontWeight: 700
                    }}>
                      {Math.round((g.progress || 0) * 100)}%
                    </span>
                  </div>
                  <div style={{ fontSize: '0.82em', color: '#fca5a5', marginTop: 6 }}>
                    {g.reasons.join(' · ')}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

      </div>

      {/* Knowledge Graph View */}
      <section className="dashboard-card graph-card" style={{
        marginTop: 24,
        background: 'rgba(22, 18, 48, 0.65)',
        border: '1px solid rgba(139, 92, 246, 0.22)',
        borderRadius: 18,
        padding: 24,
        backdropFilter: 'blur(16px)',
        boxShadow: '0 20px 45px -15px rgba(5, 4, 15, 0.7)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.15em', color: '#ffffff' }}>Personal Knowledge Graph</h3>
            <p className="muted" style={{ fontSize: '0.85em', margin: '4px 0 0 0' }}>
              Nodes ({nodes.length}) and edges ({rels.length}) linking concepts, subjects, goals, and documents.
            </p>
          </div>
        </div>
        <div className="graph-container" style={{ height: 380, marginTop: 14 }}>
          <GraphView nodes={nodes} relationships={rels} />
        </div>
      </section>
    </main>
  )
}
