"""Complaint API Routes — full PS coverage"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

from app.models.complaint import (
    RawComplaintIn, Complaint, ComplaintResponse,
    AgentAction, EscalationAction, ReplyMessage,
    ComplaintStatus, EscalationLevel, EscalationRecord,
    HistoryMessage, MessageAuthor, DashboardStats, RegulatoryReport,
    Channel, Severity, Category
)
from app.services.pii_scrubber import mask_pii
from app.services.triage import get_triage_service
from app.services.clustering import get_clustering_service
from app.services.store import get_store

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post("/ingest", response_model=ComplaintResponse)
async def ingest_complaint(payload: RawComplaintIn):
    store = get_store()
    masked_text, _ = mask_pii(payload.raw_text)
    triage_result   = get_triage_service().triage(masked_text)
    complaint = Complaint(
        channel=payload.channel, raw_text=payload.raw_text,
        masked_text=masked_text, customer_id=payload.customer_id,
        source_ref=payload.source_ref,
        received_at=payload.received_at or datetime.utcnow(),
        triage=triage_result,
    )
    complaint.communication_history.append(HistoryMessage(
        author=MessageAuthor.CUSTOMER, author_name="Customer",
        content=payload.raw_text,
    ))
    complaint.communication_history.append(HistoryMessage(
        author=MessageAuthor.SYSTEM, author_name="System",
        content=f"Auto-triaged: {triage_result.category.value} | {triage_result.severity.value} | {triage_result.sentiment.value}",
    ))
    complaint.communication_history.append(HistoryMessage(
        author=MessageAuthor.AGENT, author_name="AI Assistant",
        content=triage_result.suggested_response, is_ai_draft=True,
    ))
    complaint.cluster = get_clustering_service().check_and_register(complaint.id, masked_text)
    store.save(complaint)
    return ComplaintResponse(complaint=complaint, message="Complaint ingested and triaged successfully.")


@router.get("/stats", response_model=DashboardStats)
async def get_stats():
    return get_store().get_stats()


@router.get("/regulatory-report", response_model=RegulatoryReport)
async def regulatory_report():
    return get_store().get_regulatory_report()


@router.get("/alerts")
async def get_alerts():
    alerts = [c for c in get_store().all() if c.cluster and c.cluster.systemic_alert]
    return {"alerts": alerts, "count": len(alerts)}


@router.get("", response_model=list[Complaint])
async def list_complaints(
    status:   Optional[ComplaintStatus] = Query(None),
    channel:  Optional[Channel]         = Query(None),
    severity: Optional[Severity]        = Query(None),
    category: Optional[Category]        = Query(None),
    limit: int = Query(100, le=500),
):
    complaints = get_store().all()
    if status:   complaints = [c for c in complaints if c.status == status]
    if channel:  complaints = [c for c in complaints if c.channel == channel]
    if severity: complaints = [c for c in complaints if c.triage and c.triage.severity == severity]
    if category: complaints = [c for c in complaints if c.triage and c.triage.category == category]
    complaints.sort(key=lambda c: c.received_at, reverse=True)
    return complaints[:limit]


@router.get("/{complaint_id}", response_model=Complaint)
async def get_complaint(complaint_id: str):
    c = get_store().get(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return c


@router.post("/{complaint_id}/action")
async def agent_action(complaint_id: str, action: AgentAction):
    store = get_store()
    c = store.get(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    status_map = {
        "approve":  ComplaintStatus.RESOLVED,
        "escalate": ComplaintStatus.ESCALATED,
        "reject":   ComplaintStatus.IN_REVIEW,
    }
    new_status = status_map.get(action.action)
    if not new_status:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action.action}")
    response_text = action.custom_response or (c.triage.suggested_response if c.triage else "")
    updated = store.update_status(complaint_id, new_status, agent_note=response_text)
    return {"complaint_id": complaint_id, "new_status": new_status, "complaint": updated}


@router.post("/{complaint_id}/escalate")
async def escalate_complaint(complaint_id: str, action: EscalationAction):
    store = get_store()
    c = store.get(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    record = EscalationRecord(
        from_level=c.escalation_level, to_level=action.to_level,
        reason=action.reason, escalated_by=action.agent_id, note=action.note,
    )
    updated = store.escalate(complaint_id, record, action.to_level)
    return {"complaint_id": complaint_id, "escalated_to": action.to_level, "complaint": updated}


@router.post("/{complaint_id}/reply")
async def add_reply(complaint_id: str, msg: ReplyMessage):
    store = get_store()
    c = store.get(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    new_msg = HistoryMessage(
        author=msg.author, author_name=msg.author_name,
        content=msg.content, is_ai_draft=msg.is_ai_draft,
    )
    updated = store.add_message(complaint_id, new_msg)
    return {"complaint_id": complaint_id, "message": new_msg, "complaint": updated}
