"""
DashboardService — Personal Knowledge Mirror.

Answers the core question: "What is happening with me?" rather than
merely reporting "What did I do?"

Calculates:
1. current_focus & focus_shift: Windowed comparison (recent 14 days vs prior 14 days)
   of Evidence activity share to surface genuine behavioral shifts.
2. rising_concepts: Concepts whose confidence has advanced notably compared to their
   prior KnowledgeStateSnapshot.
3. stagnant_or_struggling_concepts: Concepts with repeated evidence events (attempts)
   whose confidence remains low (differentiating from not-yet-started concepts).
4. active_preferences: High-confidence inferred learning styles.
5. goals_needing_attention: Goals with near deadlines or stalled progress.
6. reflections: Transparent rule-based natural language reflection statements.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.evidence import Evidence, SubjectType
from app.models.knowledge_concept import KnowledgeConcept
from app.models.knowledge_state_snapshot import KnowledgeStateSnapshot
from app.models.learning_preference import LearningPreference
from app.models.goal import Goal, GoalStatus
from app.models.task import Task, TaskStatus


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def get_dashboard(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Construct the full personalized reflection view for the authenticated user.
    Guaranteed to handle empty/new accounts gracefully without errors.
    """
    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=14)
    prior_cutoff = now - timedelta(days=28)

    # -------------------------------------------------------------
    # 1. Focus Shift (Recent 14d vs Earlier 14d)
    # -------------------------------------------------------------
    all_user_evidence = (
        db.query(Evidence)
        .filter(Evidence.user_id == user_id)
        .all()
    )

    all_recent_evidence = [e for e in all_user_evidence if _as_utc(e.created_at) >= prior_cutoff]
    recent_window_evs = [e for e in all_recent_evidence if _as_utc(e.created_at) >= recent_cutoff]
    earlier_window_evs = [e for e in all_recent_evidence if prior_cutoff <= _as_utc(e.created_at) < recent_cutoff]

    # Map subject_id to concept names
    user_concepts = {c.id: c for c in db.query(KnowledgeConcept).filter(KnowledgeConcept.user_id == user_id).all()}

    def count_by_concept(ev_list):
        counts: Dict[str, int] = {}
        for e in ev_list:
            if e.subject_type == SubjectType.KNOWLEDGE_CONCEPT and e.subject_id in user_concepts:
                name = user_concepts[e.subject_id].name
                counts[name] = counts.get(name, 0) + 1
        return counts

    recent_counts = count_by_concept(recent_window_evs)
    earlier_counts = count_by_concept(earlier_window_evs)

    total_recent = sum(recent_counts.values())
    total_earlier = sum(earlier_counts.values())

    focus_shifts = []
    for cname, count in recent_counts.items():
        recent_share = count / total_recent if total_recent > 0 else 0.0
        earlier_count = earlier_counts.get(cname, 0)
        earlier_share = earlier_count / total_earlier if total_earlier > 0 else 0.0
        share_diff = recent_share - earlier_share
        focus_shifts.append({
            "concept_name": cname,
            "recent_count": count,
            "earlier_count": earlier_count,
            "recent_share": round(recent_share, 3),
            "earlier_share": round(earlier_share, 3),
            "share_change": round(share_diff, 3),
        })

    # Sort by positive share gain
    focus_shifts.sort(key=lambda x: x["share_change"], reverse=True)
    top_focus_shift = focus_shifts[0] if focus_shifts and focus_shifts[0]["share_change"] > 0 else None

    # -------------------------------------------------------------
    # 2. Rising Concepts (confidence improved notably vs snapshot)
    # -------------------------------------------------------------
    rising_concepts = []
    for cid, concept in user_concepts.items():
        # Get latest snapshot prior to current state
        snapshots = (
            db.query(KnowledgeStateSnapshot)
            .filter(KnowledgeStateSnapshot.concept_id == cid)
            .order_by(KnowledgeStateSnapshot.created_at.desc())
            .all()
        )
        if snapshots:
            latest_snap = snapshots[0]
            gain = concept.confidence - latest_snap.confidence
            if gain >= 0.08:
                rising_concepts.append({
                    "id": concept.id,
                    "name": concept.name,
                    "current_confidence": concept.confidence,
                    "previous_confidence": latest_snap.confidence,
                    "confidence_gain": round(gain, 3),
                })
        else:
            # If no snapshots exist yet, but concept confidence has meaningfully grown with evidence
            if concept.confidence >= 0.35 and concept.evidence_count >= 2:
                rising_concepts.append({
                    "id": concept.id,
                    "name": concept.name,
                    "current_confidence": concept.confidence,
                    "previous_confidence": 0.1,
                    "confidence_gain": round(concept.confidence - 0.1, 3),
                })

    rising_concepts.sort(key=lambda x: x["confidence_gain"], reverse=True)

    # -------------------------------------------------------------
    # 3. Stagnant or Struggling Concepts
    # -------------------------------------------------------------
    stagnant_concepts = []
    for cid, concept in user_concepts.items():
        # Differentiating criteria: repeated attempts (evidence_count >= 3)
        # but confidence remains low (< 0.35)
        if concept.evidence_count >= 3 and concept.confidence < 0.35:
            stagnant_concepts.append({
                "id": concept.id,
                "name": concept.name,
                "confidence": concept.confidence,
                "evidence_count": concept.evidence_count,
            })
    stagnant_concepts.sort(key=lambda x: x["evidence_count"], reverse=True)

    # -------------------------------------------------------------
    # 4. Active Learning Preferences
    # -------------------------------------------------------------
    preferences = (
        db.query(LearningPreference)
        .filter(LearningPreference.user_id == user_id, LearningPreference.confidence >= 0.35)
        .order_by(LearningPreference.confidence.desc())
        .all()
    )
    active_prefs = [
        {
            "id": p.id,
            "preference_type": p.preference_type,
            "confidence": p.confidence,
            "evidence_count": p.evidence_count,
        }
        for p in preferences
    ]

    # -------------------------------------------------------------
    # 5. Goals Needing Attention
    # -------------------------------------------------------------
    active_goals = (
        db.query(Goal)
        .filter(
            Goal.user_id == user_id,
            Goal.status.in_([GoalStatus.IN_PROGRESS, GoalStatus.NOT_STARTED]),
        )
        .all()
    )

    goals_needing_attention = []
    for g in active_goals:
        needs_attention = False
        reasons = []

        # Near or overdue deadline
        if g.deadline:
            days_left = (_as_utc(g.deadline) - now).days
            if days_left < 0:
                needs_attention = True
                reasons.append("Deadline has passed")
            elif days_left <= 7:
                needs_attention = True
                reasons.append(f"Deadline in {days_left} day(s)")

        # Low progress
        if g.progress < 0.25:
            needs_attention = True
            reasons.append("Progress below 25%")

        if needs_attention:
            goals_needing_attention.append({
                "id": g.id,
                "title": g.title,
                "deadline": g.deadline.isoformat() if g.deadline else None,
                "progress": g.progress,
                "reasons": reasons,
            })

    # -------------------------------------------------------------
    # 6. Natural Language Reflection Statements
    # -------------------------------------------------------------
    reflections = []

    # Focus shift statement
    if top_focus_shift and top_focus_shift["recent_count"] >= 2:
        cname = top_focus_shift["concept_name"]
        pct = int(top_focus_shift["recent_share"] * 100)
        reflections.append(
            f"Your recent activity has visibly shifted toward {cname} (accounting for {pct}% of recent focus)."
        )
    elif total_recent > 0:
        top_c = max(recent_counts.items(), key=lambda x: x[1])[0]
        reflections.append(f"You have been actively engaging with {top_c} over the past two weeks.")

    # Rising concept statement
    if rising_concepts:
        top_rising = rising_concepts[0]
        reflections.append(
            f"Your confidence in {top_rising['name']} has grown noticeably from {top_rising['previous_confidence']:.2f} to {top_rising['current_confidence']:.2f}."
        )

    # Struggling concept statement
    if stagnant_concepts:
        struggle = stagnant_concepts[0]
        reflections.append(
            f"{struggle['name']} has seen repeated practice ({struggle['evidence_count']} attempts) and remains an active growth area."
        )

    # Preference statement
    if active_prefs:
        pref = active_prefs[0]["preference_type"].replace("_", " ")
        reflections.append(
            f"You consistently learn best when explanations provide {pref}."
        )

    # Goal statement
    if goals_needing_attention:
        g = goals_needing_attention[0]
        reflections.append(
            f"Goal '{g['title']}' requires your attention ({', '.join(g['reasons'])})."
        )

    # Onboarding fallback for fresh users
    if not reflections:
        reflections.append(
            "Welcome to MindVault. As you complete tasks, study materials, and interact with the assistant, your evolving knowledge reflection will appear here."
        )

    return {
        "current_focus": {
            "recent_window_days": 14,
            "earlier_window_days": 14,
            "total_recent_signals": total_recent,
            "total_earlier_signals": total_earlier,
            "shifts": focus_shifts[:5],
        },
        "rising_concepts": rising_concepts[:5],
        "stagnant_or_struggling_concepts": stagnant_concepts[:5],
        "active_preferences": active_prefs[:5],
        "goals_needing_attention": goals_needing_attention[:5],
        "reflections": reflections,
    }
