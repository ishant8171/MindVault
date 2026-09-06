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
        background: '#f8fafc',
        border: '1px solid #e2e8f0',
        borderRadius: 12,
        padding: 20,
        marginBottom: 20,
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
      }}>
        <h3 style={{ marginTop: 0, color: '#1e293b', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>🧠</span> What MindVault Sees In You
        </h3>
        <ul style={{ listStyleType: 'none', paddingLeft: 0, margin: '12px 0 0 0' }}>
          {reflections.map((statement, idx) => (
            <li key={idx} style={{
              padding: '10px 14px',
              backgroundColor: '#ffffff',
              borderRadius: 8,
              border: '1px solid #edf2f7',
              marginBottom: 8,
              fontSize: '1.02em',
              lineHeight: 1.5,
              color: '#334155'
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
          background: '#fff',
          border: '1px solid #e2e8f0',
          borderRadius: 10,
          padding: 16
        }}>
          <h3 style={{ marginTop: 0, fontSize: '1.1em', color: '#1e293b' }}>
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
            <div style={{ marginTop: 10 }}>
              {currentFocus.shifts.map((shift, idx) => (
                <div key={idx} style={{
                  padding: '8px 10px',
                  background: shift.share_change > 0 ? '#f0fdf4' : '#f8fafc',
                  border: '1px solid ' + (shift.share_change > 0 ? '#bbf7d0' : '#e2e8f0'),
                  borderRadius: 6,
                  marginBottom: 8,
                  fontSize: '0.9em'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600 }}>
                    <span>{shift.concept_name}</span>
                    <span style={{ color: shift.share_change > 0 ? '#16a34a' : '#64748b' }}>
                      {shift.share_change > 0 ? `+${Math.round(shift.share_change * 100)}% share` : 'Equal share'}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.82em', color: '#64748b', marginTop: 4 }}>
                    Recent signals: {shift.recent_count} ({Math.round(shift.recent_share * 100)}%) vs Earlier: {shift.earlier_count} ({Math.round(shift.earlier_share * 100)}%)
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 2. Rising Concepts */}
        <section className="dashboard-card" style={{
          background: '#fff',
          border: '1px solid #e2e8f0',
          borderRadius: 10,
          padding: 16
        }}>
          <h3 style={{ marginTop: 0, fontSize: '1.1em', color: '#1e293b' }}>
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
            <div style={{ marginTop: 10 }}>
              {risingConcepts.map(c => (
                <div key={c.id} style={{
                  padding: '8px 12px',
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: 6,
                  marginBottom: 8
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong style={{ fontSize: '0.95em' }}>{c.name}</strong>
                    <span style={{
                      background: '#dcfce7',
                      color: '#15803d',
                      padding: '2px 8px',
                      borderRadius: 12,
                      fontSize: '0.78em',
                      fontWeight: 600
                    }}>
                      +{Math.round(c.confidence_gain * 100)}% gain
                    </span>
                  </div>
                  <div style={{ marginTop: 6 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78em', color: '#64748b', marginBottom: 2 }}>
                      <span>Confidence</span>
                      <span>{Math.round(c.current_confidence * 100)}%</span>
                    </div>
                    <div style={{ background: '#e2e8f0', borderRadius: 4, height: 6, overflow: 'hidden' }}>
                      <div style={{ background: '#22c55e', width: `${Math.min(100, Math.round(c.current_confidence * 100))}%`, height: '100%' }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 3. Stagnant / Struggling Concepts */}
        <section className="dashboard-card" style={{
          background: '#fff',
          border: '1px solid #e2e8f0',
          borderRadius: 10,
          padding: 16
        }}>
          <h3 style={{ marginTop: 0, fontSize: '1.1em', color: '#1e293b' }}>
            ⚠️ Active Difficulty Areas
          </h3>
          <p className="muted" style={{ fontSize: '0.85em', marginTop: -4 }}>
            Topics with repeated practice attempts whose confidence hasn't consolidated yet.
          </p>
          {strugglingConcepts.length === 0 ? (
            <div className="empty-state" style={{ padding: '16px 0', fontSize: '0.9em', color: '#16a34a' }}>
              ✓ No persistent struggle areas detected.
            </div>
          ) : (
            <div style={{ marginTop: 10 }}>
              {strugglingConcepts.map(c => (
                <div key={c.id} style={{
                  padding: '8px 12px',
                  background: '#fff7ed',
                  border: '1px solid #fed7aa',
                  borderRadius: 6,
                  marginBottom: 8
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600, color: '#c2410c' }}>
                    <span>{c.name}</span>
                    <span style={{ fontSize: '0.82em' }}>{c.evidence_count} attempts</span>
                  </div>
                  <div style={{ fontSize: '0.82em', color: '#7c2d12', marginTop: 4 }}>
                    Confidence currently {Math.round(c.confidence * 100)}% — assistant will adapt explanations for this gap.
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 4. Active Inferred Learning Preferences */}
        <section className="dashboard-card" style={{
          background: '#fff',
          border: '1px solid #e2e8f0',
          borderRadius: 10,
          padding: 16
        }}>
          <h3 style={{ marginTop: 0, fontSize: '1.1em', color: '#1e293b' }}>
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
            <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {activePrefs.map(p => (
                <div key={p.id} style={{
                  padding: '6px 12px',
                  background: '#f1f5f9',
                  border: '1px solid #cbd5e1',
                  borderRadius: 20,
                  fontSize: '0.85em',
                  color: '#1e293b',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6
                }}>
                  <span>💡</span>
                  <span>{p.preference_type.replace(/_/g, ' ')}</span>
                  <span style={{ fontSize: '0.75em', color: '#64748b', fontWeight: 600 }}>
                    ({Math.round(p.confidence * 100)}% match)
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 5. Goals Needing Attention */}
        <section className="dashboard-card" style={{
          background: '#fff',
          border: '1px solid #e2e8f0',
          borderRadius: 10,
          padding: 16
        }}>
          <h3 style={{ marginTop: 0, fontSize: '1.1em', color: '#1e293b' }}>
            ⏳ Goals Needing Attention
          </h3>
          <p className="muted" style={{ fontSize: '0.85em', marginTop: -4 }}>
            Goals with upcoming deadlines or low progress requiring focus.
          </p>
          {goalsNeedingAttention.length === 0 ? (
            <div className="empty-state" style={{ padding: '16px 0', fontSize: '0.9em', color: '#16a34a' }}>
              ✓ All active goals are on schedule.
            </div>
          ) : (
            <div style={{ marginTop: 10 }}>
              {goalsNeedingAttention.map(g => (
                <div key={g.id} style={{
                  padding: '8px 12px',
                  background: '#fef2f2',
                  border: '1px solid #fecaca',
                  borderRadius: 6,
                  marginBottom: 8
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600, color: '#991b1b' }}>
                    <span>{g.title}</span>
                    <span style={{ fontSize: '0.82em' }}>{Math.round((g.progress || 0) * 100)}%</span>
                  </div>
                  <div style={{ fontSize: '0.8em', color: '#b91c1c', marginTop: 4 }}>
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
        background: '#fff',
        border: '1px solid #e2e8f0',
        borderRadius: 10,
        padding: 16
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.1em' }}>Personal Knowledge Graph</h3>
            <p className="muted" style={{ fontSize: '0.85em', margin: 0 }}>
              Nodes ({nodes.length}) and edges ({rels.length}) linking concepts, subjects, goals, and documents.
            </p>
          </div>
        </div>
        <div className="graph-container" style={{ height: 350, marginTop: 12 }}>
          <GraphView nodes={nodes} relationships={rels} />
        </div>
      </section>
    </main>
  )
}
