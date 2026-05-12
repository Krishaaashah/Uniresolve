"""Complaint Store — in-memory for hackathon demo."""

from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict

from app.models.complaint import (
    Complaint, ComplaintStatus, DashboardStats,
    SLAStatus, EscalationLevel, EscalationRecord,
    HistoryMessage, MessageAuthor, compute_sla,
    RegulatoryReport, Channel, Category, Severity,
    TriageResult, Sentiment, DuplicateCluster
)


class ComplaintStore:
    def __init__(self):
        self._store: dict[str, Complaint] = {}

    def save(self, complaint: Complaint) -> Complaint:
        self._store[complaint.id] = complaint
        return complaint

    def get(self, complaint_id: str) -> Optional[Complaint]:
        c = self._store.get(complaint_id)
        if c and c.triage and c.status != ComplaintStatus.RESOLVED:
            c.sla = compute_sla(c.received_at, c.triage.severity.value)
        return c

    def all(self) -> list[Complaint]:
        out = []
        for c in self._store.values():
            if c.triage and c.status != ComplaintStatus.RESOLVED:
                c.sla = compute_sla(c.received_at, c.triage.severity.value)
            out.append(c)
        return out

    def update_status(self, complaint_id: str, status: ComplaintStatus,
                      agent_note: Optional[str] = None) -> Optional[Complaint]:
        c = self._store.get(complaint_id)
        if not c:
            return None
        c.status = status
        if agent_note:
            c.agent_note = agent_note
            c.communication_history.append(HistoryMessage(
                author=MessageAuthor.AGENT, author_name="Agent",
                content=agent_note,
            ))
        if status == ComplaintStatus.RESOLVED:
            c.resolved_at = datetime.utcnow()
            c.communication_history.append(HistoryMessage(
                author=MessageAuthor.SYSTEM, author_name="System",
                content="Complaint marked as resolved.",
            ))
        return c

    def add_message(self, complaint_id: str, msg: HistoryMessage) -> Optional[Complaint]:
        c = self._store.get(complaint_id)
        if not c:
            return None
        c.communication_history.append(msg)
        return c

    def escalate(self, complaint_id: str, record: EscalationRecord,
                 to_level: EscalationLevel) -> Optional[Complaint]:
        c = self._store.get(complaint_id)
        if not c:
            return None
        c.escalation_history.append(record)
        c.escalation_level = to_level
        c.status = ComplaintStatus.ESCALATED
        c.communication_history.append(HistoryMessage(
            author=MessageAuthor.SYSTEM, author_name="System",
            content=f"Escalated to {to_level.value} - {record.reason}",
        ))
        return c

    def get_stats(self) -> DashboardStats:
        complaints = self.all()
        total = len(complaints)
        pending   = sum(1 for c in complaints if c.status == ComplaintStatus.PENDING)
        resolved  = sum(1 for c in complaints if c.status == ComplaintStatus.RESOLVED)
        escalated = sum(1 for c in complaints if c.status == ComplaintStatus.ESCALATED)
        systemic_alerts = sum(1 for c in complaints if c.cluster and c.cluster.systemic_alert)
        sla_breached = sum(1 for c in complaints if c.sla and c.sla.breached)
        sla_at_risk  = sum(1 for c in complaints if c.sla and c.sla.status == SLAStatus.AT_RISK)

        by_category: dict = defaultdict(int)
        by_severity: dict = defaultdict(int)
        by_channel:  dict = defaultdict(int)
        resolution_times: list[float] = []

        for c in complaints:
            if c.triage:
                by_category[c.triage.category.value] += 1
                by_severity[c.triage.severity.value]  += 1
            by_channel[c.channel.value] += 1
            if c.resolved_at:
                resolution_times.append((c.resolved_at - c.received_at).total_seconds() / 60)

        avg_res = sum(resolution_times) / len(resolution_times) if resolution_times else 0.0

        daily_trend = []
        for i in range(6, -1, -1):
            day = datetime.utcnow() - timedelta(days=i)
            cnt = sum(1 for c in complaints if c.received_at.date() == day.date())
            daily_trend.append({"date": day.strftime("%b %d"), "count": cnt})

        return DashboardStats(
            total=total, pending=pending, resolved=resolved,
            escalated=escalated, systemic_alerts=systemic_alerts,
            sla_breached=sla_breached, sla_at_risk=sla_at_risk,
            by_category=dict(by_category), by_severity=dict(by_severity),
            by_channel=dict(by_channel), daily_trend=daily_trend,
            avg_resolution_minutes=round(avg_res, 2),
        )

    def get_regulatory_report(self) -> RegulatoryReport:
        complaints = self.all()
        total = len(complaints)
        resolved_list  = [c for c in complaints if c.status == ComplaintStatus.RESOLVED]
        pending_list   = [c for c in complaints if c.status == ComplaintStatus.PENDING]
        escalated_list = [c for c in complaints if c.status == ComplaintStatus.ESCALATED]
        breached       = [c for c in complaints if c.sla and c.sla.breached]
        reg_escalated  = [c for c in complaints if c.escalation_level == EscalationLevel.L4_REGULATORY]

        res_hours = [
            (c.resolved_at - c.received_at).total_seconds() / 3600
            for c in resolved_list if c.resolved_at
        ]
        avg_res_h = sum(res_hours) / len(res_hours) if res_hours else 0

        by_cat = defaultdict(int); by_ch = defaultdict(int); by_sev = defaultdict(int)
        for c in complaints:
            if c.triage:
                by_cat[c.triage.category.value] += 1
                by_sev[c.triage.severity.value]  += 1
            by_ch[c.channel.value] += 1

        critical_unresolved = sum(
            1 for c in complaints
            if c.triage and c.triage.severity.value == "critical"
            and c.status != ComplaintStatus.RESOLVED
        )

        return RegulatoryReport(
            generated_at=datetime.utcnow(), period="Last 30 Days",
            total_complaints=total, resolved=len(resolved_list),
            pending=len(pending_list), escalated=len(escalated_list),
            resolution_rate_pct=round(len(resolved_list)/total*100 if total else 0, 1),
            sla_breach_count=len(breached),
            sla_compliance_pct=round((total-len(breached))/total*100 if total else 100, 1),
            avg_resolution_hours=round(avg_res_h, 2),
            by_category=dict(by_cat), by_channel=dict(by_ch), by_severity=dict(by_sev),
            critical_unresolved=critical_unresolved,
            escalated_to_regulatory=len(reg_escalated),
        )

    def seed_demo_data(self):
        import uuid

        DEMOS = [
            dict(
                raw="My UPI payment of Rs 5000 to Zomato failed but money was deducted from my account!",
                channel=Channel.APP, cat=Category.UPI, sev=Severity.HIGH,
                sent=Sentiment.FRUSTRATED, key="UPI payment failed but amount debited",
                cluster_size=3, systemic=False, hrs=2,
                status=ComplaintStatus.PENDING, lvl=EscalationLevel.L1_AGENT,
                history=[
                    ("customer","Customer","My UPI payment of Rs 5000 to Zomato failed but money was deducted!",False),
                    ("system","System","Complaint received and auto-triaged by UniResolve AI.",False),
                ],
            ),
            dict(
                raw="Unable to login to net banking since morning. OTP not received on registered mobile.",
                channel=Channel.EMAIL, cat=Category.NETBANKING, sev=Severity.HIGH,
                sent=Sentiment.FRUSTRATED, key="Net banking login failure, OTP not received",
                cluster_size=1, systemic=False, hrs=5,
                status=ComplaintStatus.IN_REVIEW, lvl=EscalationLevel.L1_AGENT,
                history=[
                    ("customer","Customer","Unable to login to net banking. OTP not received.",False),
                    ("system","System","Complaint auto-triaged. Assigned to L1 Agent.",False),
                    ("agent","Agent Krisha","We have acknowledged your complaint. Our technical team is investigating the OTP delivery issue. We will update you within 2 hours.",False),
                    ("customer","Customer","It has been 2 hours and still not working. Please resolve urgently!",False),
                ],
            ),
            dict(
                raw="Fraud transaction of Rs 12,000 detected on my debit card. I did not authorize this!",
                channel=Channel.CALL, cat=Category.FRAUD, sev=Severity.CRITICAL,
                sent=Sentiment.ANGRY, key="Unauthorized debit card transaction of Rs 12,000",
                cluster_size=1, systemic=False, hrs=26,
                status=ComplaintStatus.ESCALATED, lvl=EscalationLevel.L3_MANAGER,
                history=[
                    ("customer","Customer","Fraud transaction of Rs 12,000 on my debit card. Not authorized!",False),
                    ("system","System","CRITICAL complaint. Card blocked automatically. Escalating to L2 Supervisor.",False),
                    ("agent","Agent Janhavi","We have blocked your card immediately and initiated fraud investigation.",False),
                    ("system","System","Escalated to L3 Manager - fraud amount exceeds Rs 10,000 threshold.",False),
                    ("agent","Manager Rao","Fraud team notified. Provisional credit of Rs 12,000 will be issued within 24 hours pending investigation.",False),
                ],
                escalations=[
                    ("L1 Agent","L2 Supervisor","CRITICAL fraud complaint auto-escalated","System"),
                    ("L2 Supervisor","L3 Manager","Fraud amount > Rs 10,000 requires manager approval","Agent Janhavi"),
                ],
            ),
            dict(
                raw="UPI transfer failing again! Third time this week. Money debited but not credited to recipient.",
                channel=Channel.SOCIAL, cat=Category.UPI, sev=Severity.CRITICAL,
                sent=Sentiment.ANGRY, key="Repeated UPI failure - systemic outage detected",
                cluster_size=7, systemic=True, hrs=0.5,
                status=ComplaintStatus.PENDING, lvl=EscalationLevel.L2_SUPERVISOR,
                history=[
                    ("customer","Customer","UPI transfer failing AGAIN! Third time this week!",False),
                    ("system","System","SYSTEMIC ALERT: 7 similar UPI complaints in cluster. Supervisor notified.",False),
                ],
                escalations=[
                    ("L1 Agent","L2 Supervisor","Systemic UPI failure affecting multiple customers","System"),
                ],
            ),
            dict(
                raw="EMI for my home loan was auto-debited twice this month. Please refund immediately.",
                channel=Channel.EMAIL, cat=Category.LOANS, sev=Severity.HIGH,
                sent=Sentiment.ANGRY, key="Double EMI deduction for home loan",
                cluster_size=1, systemic=False, hrs=30,
                status=ComplaintStatus.RESOLVED, lvl=EscalationLevel.L1_AGENT,
                history=[
                    ("customer","Customer","EMI debited twice this month. Refund immediately please.",False),
                    ("system","System","Complaint received and triaged.",False),
                    ("agent","Agent Disha","We sincerely apologise. Duplicate deduction confirmed. Refund of Rs 18,450 has been initiated - will reflect within 24 hours.",False),
                    ("customer","Customer","Thank you, I can see the credit now. Issue resolved.",False),
                    ("system","System","Complaint resolved by Agent Disha. Resolution time: 4h 22m.",False),
                ],
            ),
            dict(
                raw="ATM card blocked after 3 wrong PIN attempts. Please unblock or issue new card.",
                channel=Channel.BRANCH, cat=Category.ATM, sev=Severity.MEDIUM,
                sent=Sentiment.NEUTRAL, key="ATM card blocked due to wrong PIN attempts",
                cluster_size=1, systemic=False, hrs=15,
                status=ComplaintStatus.RESOLVED, lvl=EscalationLevel.L1_AGENT,
                history=[
                    ("customer","Customer","ATM card blocked after wrong PIN. Need unblock or new card.",False),
                    ("system","System","Complaint received via Branch channel.",False),
                    ("agent","Agent Jhotika","Card unblock processed. New card dispatched to registered address - arrives in 5-7 working days.",False),
                    ("system","System","Complaint resolved.",False),
                ],
            ),
            dict(
                raw="KYC update pending for 3 weeks. Documents submitted but still showing incomplete.",
                channel=Channel.APP, cat=Category.KYC, sev=Severity.MEDIUM,
                sent=Sentiment.FRUSTRATED, key="KYC documents submitted but not processed for 3 weeks",
                cluster_size=1, systemic=False, hrs=72,
                status=ComplaintStatus.PENDING, lvl=EscalationLevel.L1_AGENT,
                history=[
                    ("customer","Customer","KYC pending for 3 weeks. Documents submitted but showing incomplete.",False),
                    ("system","System","Complaint auto-triaged. Assigned to KYC verification team.",False),
                ],
            ),
        ]

        LEVEL_MAP = {
            "L1 Agent": EscalationLevel.L1_AGENT,
            "L2 Supervisor": EscalationLevel.L2_SUPERVISOR,
            "L3 Manager": EscalationLevel.L3_MANAGER,
            "L4 Regulatory": EscalationLevel.L4_REGULATORY,
        }

        for d in DEMOS:
            cid = str(uuid.uuid4())
            received = datetime.utcnow() - timedelta(hours=d["hrs"])

            history_msgs = [
                HistoryMessage(
                    author=MessageAuthor(h[0]), author_name=h[1],
                    content=h[2], is_ai_draft=h[3],
                    timestamp=received + timedelta(minutes=20*i),
                )
                for i, h in enumerate(d["history"])
            ]

            esc_records = []
            for e in d.get("escalations", []):
                esc_records.append(EscalationRecord(
                    from_level=LEVEL_MAP[e[0]], to_level=LEVEL_MAP[e[1]],
                    reason=e[2], escalated_by=e[3],
                    escalated_at=received + timedelta(minutes=30),
                ))

            complaint = Complaint(
                id=cid,
                channel=d["channel"],
                raw_text=d["raw"],
                masked_text=d["raw"],
                received_at=received,
                triage=TriageResult(
                    category=d["cat"], severity=d["sev"], sentiment=d["sent"],
                    key_issue=d["key"],
                    suggested_response=(
                        f"Dear Customer, we have noted your concern regarding '{d['key']}'. "
                        "Our team is reviewing this on priority and will respond within the SLA timeline."
                    ),
                    confidence=0.91,
                ),
                cluster=DuplicateCluster(
                    cluster_id=str(uuid.uuid4()),
                    is_duplicate=d["cluster_size"] > 1,
                    cluster_size=d["cluster_size"],
                    systemic_alert=d["systemic"],
                ),
                status=d["status"],
                escalation_level=d["lvl"],
                escalation_history=esc_records,
                communication_history=history_msgs,
                resolved_at=datetime.utcnow() - timedelta(hours=1) if d["status"] == ComplaintStatus.RESOLVED else None,
            )
            self.save(complaint)


_store: Optional[ComplaintStore] = None

def get_store() -> ComplaintStore:
    global _store
    if _store is None:
        _store = ComplaintStore()
        _store.seed_demo_data()
    return _store
