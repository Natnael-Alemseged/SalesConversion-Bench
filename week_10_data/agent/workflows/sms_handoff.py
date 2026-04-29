from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.storage.conversations import ConversationStore
from agent.storage.suppression import SmsSuppressionStore
from agent.workflows.lead_orchestrator import LeadOrchestrator


@dataclass(frozen=True)
class WarmLeadGate:
    email_replied: bool
    sms_opted_out: bool
    suppressed: bool


def _warm_lead_gate(
    *,
    conversations: ConversationStore,
    suppression: SmsSuppressionStore,
    thread_id: str,
    to_phone: str,
) -> WarmLeadGate:
    state = conversations.fetch_state(thread_id=thread_id) if conversations.enabled else None
    email_replied = bool((state or {}).get("email_replied"))
    # Robustness: if state wasn't recomputed/upserted due to a transient DB failure
    # during inbound email handling, fall back to the raw message log.
    if not email_replied and conversations.enabled:
        try:
            msgs = conversations.fetch_recent_messages(thread_id=thread_id, limit=50)
            email_replied = any(
                (
                    str(m.get("direction") or "") == "inbound"
                    and str(m.get("channel") or "") == "email"
                )
                for m in (msgs or [])
            )
        except Exception:
            # If the DB is unhealthy, keep the conservative default (False).
            email_replied = email_replied
    sms_opted_out = bool((state or {}).get("sms_opted_out"))
    suppressed = suppression.is_suppressed(to_phone)
    return WarmLeadGate(
        email_replied=email_replied, sms_opted_out=sms_opted_out, suppressed=suppressed
    )


def send_warm_lead_sms_handoff(
    *,
    orchestrator: LeadOrchestrator,
    conversations: ConversationStore,
    suppression: SmsSuppressionStore,
    thread_id: str,
    to_phone: str,
    company_name: str,
    outbound_variant: str,
    message_override: str | None = None,
) -> dict[str, Any]:
    if conversations.enabled:
        # If the caller passes a stale/deleted thread_id (common after DB resets or
        # thread merges), fail with a precise error instead of misreporting
        # email_replied=false.
        existing = conversations.fetch_thread(thread_id=thread_id)
        if not existing:
            raise ValueError(
                "Unknown thread_id (no conversation_threads row). "
                "Use the thread_id from a successful inbound email webhook run."
            )
    gate = _warm_lead_gate(
        conversations=conversations,
        suppression=suppression,
        thread_id=thread_id,
        to_phone=to_phone,
    )
    if gate.suppressed:
        raise ValueError("SMS number is suppressed (STOP/UNSUB).")
    if gate.sms_opted_out:
        raise ValueError("SMS number is opted out (sms_opted_out=true).")
    if not gate.email_replied:
        raise ValueError("Warm-lead gate failed: no prior email engagement (email_replied=false).")

    # Scheduling-only: keep content short and coordination-oriented.
    scheduling_hint = "If you'd like, reply with a couple times that work for you this week."
    return orchestrator.send_warm_lead_sms(
        to_phone=to_phone,
        company_name=company_name,
        scheduling_hint=scheduling_hint,
        prior_email_replied=True,
        message_override=message_override,
        thread_id=thread_id,
    )
