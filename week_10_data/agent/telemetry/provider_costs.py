from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROVIDER_COSTS_PATH = Path("eval/runs/outbound/provider_costs.jsonl")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def append_provider_cost(event: dict[str, Any], *, path: Path = PROVIDER_COSTS_PATH) -> None:
    """Append a single provider/rig cost event as JSONL.

    This is production telemetry (not a PDF-time simulation):
    - Called inline from workflows when the underlying action occurs.
    - Writes JSONL to keep the log append-only and grep-friendly.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(event)
    payload.setdefault("recorded_at", _now_iso())
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True) + "\n")


@dataclass(frozen=True)
class CostEvent:
    kind: str  # "rig_usage" | "third_party_apis"
    amount_usd: float
    label: str
    source: str
    thread_id: str = ""
    resend_thread_key: str = ""
    source_event_id: str = ""
    provider: str = ""
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "amount_usd": float(self.amount_usd),
            "label": self.label,
            "source": self.source,
            "thread_id": self.thread_id,
            "resend_thread_key": self.resend_thread_key,
            "source_event_id": self.source_event_id,
            "provider": self.provider,
            "metadata": self.metadata or {},
        }


def log_sms_credit_cost(
    *,
    thread_id: str | None,
    to_phone: str,
    amount_usd: float = 0.05,
    provider: str = "africastalking",
) -> None:
    append_provider_cost(
        CostEvent(
            kind="third_party_apis",
            amount_usd=amount_usd,
            label="Africa's Talking SMS credits (fixed per send_warm_lead_sms call)",
            source="send_warm_lead_sms",
            thread_id=thread_id or "",
            provider=provider,
            metadata={"to_phone_suffix": to_phone[-6:] if to_phone else ""},
        ).to_dict()
    )


def log_rig_usage_cost(
    *,
    tool: str,
    amount_usd: float = 0.01,
    provider: str = "rig",
    company_name: str = "",
) -> None:
    append_provider_cost(
        CostEvent(
            kind="rig_usage",
            amount_usd=amount_usd,
            label=f"Rig usage (fixed per research tool call): {tool}",
            source=tool,
            provider=provider,
            metadata={"company_name": company_name[:255]},
        ).to_dict()
    )
