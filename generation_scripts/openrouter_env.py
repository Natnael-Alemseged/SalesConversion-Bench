"""Discover OpenRouter API keys from the environment.

Supports common layouts including numbered keys and the OPEN_ROUTER_KEY_* spelling."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable


def _split_multi(raw: str) -> list[str]:
    return [k.strip() for k in re.split(r"[,\s]+", raw) if k.strip()]


def gather_openrouter_key_bindings() -> list[tuple[str, str]]:
    """Return (variable_name, secret_value) for every non-empty key slot found.

    Order: explicit primary → OPENROUTER_API_KEYS → OPENROUTER_API_KEY_N → OPEN_ROUTER_KEY_N.
    Same secret may appear under multiple names (shown separately for audits).
    """
    bindings: list[tuple[str, str]] = []

    primary = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if primary:
        bindings.append(("OPENROUTER_API_KEY", primary))

    multi = os.environ.get("OPENROUTER_API_KEYS", "").strip()
    if multi:
        for idx, k in enumerate(_split_multi(multi)):
            bindings.append((f"OPENROUTER_API_KEYS[{idx}]", k))

    for i in range(1, 100):
        name = f"OPENROUTER_API_KEY_{i}"
        k = os.environ.get(name, "").strip()
        if k:
            bindings.append((name, k))

    for i in range(1, 100):
        name = f"OPEN_ROUTER_KEY_{i}"
        k = os.environ.get(name, "").strip()
        if k:
            bindings.append((name, k))

    return bindings


def unique_keys_ordered(bindings: Iterable[tuple[str, str]]) -> list[str]:
    """De-duplicate by secret value; preserve first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for _, k in bindings:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def omit_binding_labels(
    bindings: list[tuple[str, str]],
    omit_labels: Iterable[str],
) -> list[tuple[str, str]]:
    """Drop env slots whose label is in ``omit_labels`` (exact string match, stripped)."""
    omit = {x.strip() for x in omit_labels if x.strip()}
    if not omit:
        return bindings
    return [(lab, k) for lab, k in bindings if lab not in omit]


def parse_omit_labels_from_env() -> list[str]:
    """Comma-separated env ``OPENROUTER_OMIT_KEY_SLOTS`` (e.g. ``OPEN_ROUTER_KEY_4``)."""
    raw = os.environ.get("OPENROUTER_OMIT_KEY_SLOTS", "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]
