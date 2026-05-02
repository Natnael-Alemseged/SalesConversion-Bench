"""Check which OpenRouter API keys in the environment are usable.

Uses GET https://openrouter.ai/api/v1/key (no chat completion; no model spend).

Loads ``.env`` from the repo root when ``python-dotenv`` is available.

Usage::

  cd SalesConversion-Bench
  python3 generation_scripts/verify_openrouter_keys.py

Exit code 0 if every binding returns HTTP 200; 1 otherwise (or no keys found).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    load_dotenv = None

from generation_scripts.openrouter_env import gather_openrouter_key_bindings  # noqa: E402

KEY_ENDPOINT = "https://openrouter.ai/api/v1/key"


def _mask(secret: str, *, keep: int = 8) -> str:
    if len(secret) <= keep:
        return "***"
    return f"...{secret[-keep:]}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify OpenRouter keys via GET /api/v1/key")
    parser.add_argument(
        "--no-dotenv",
        action="store_true",
        help="Do not load .env from repo root",
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON only")
    args = parser.parse_args()

    if load_dotenv and not args.no_dotenv:
        env_path = ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)

    try:
        import httpx
    except ImportError:
        print("Install httpx: pip install httpx", file=sys.stderr)
        return 2

    bindings = gather_openrouter_key_bindings()
    if not bindings:
        print(
            "No keys found. Set OPENROUTER_API_KEY, OPENROUTER_API_KEYS, OPENROUTER_API_KEY_1..N, or OPEN_ROUTER_KEY_1..N",
            file=sys.stderr,
        )
        return 1

    rows: list[dict] = []
    bad = 0

    for label, key in bindings:
        headers = {"Authorization": f"Bearer {key}"}
        row_base = {"env": label, "key_suffix": _mask(key)}
        try:
            r = httpx.get(KEY_ENDPOINT, headers=headers, timeout=30.0)
            status = r.status_code
            body = None
            try:
                body = r.json()
            except json.JSONDecodeError:
                pass

            data = body.get("data") if isinstance(body, dict) else None
            limit_rem = data.get("limit_remaining") if isinstance(data, dict) else None
            key_label = data.get("label") if isinstance(data, dict) else None

            ok = status == 200
            if not ok:
                bad += 1

            rows.append(
                {
                    **row_base,
                    "http_status": status,
                    "ok": ok,
                    "provider_key_label": key_label,
                    "limit_remaining": limit_rem,
                }
            )
        except Exception as exc:
            bad += 1
            rows.append({**row_base, "http_status": None, "ok": False, "error": str(exc)})

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(f"{KEY_ENDPOINT}\n")
        print(f"{'ENV VAR':<28} {'SUFFIX':<14} {'HTTP':<6} OK   LIMIT_REM   LABEL")
        print("-" * 90)
        for row in rows:
            env = row["env"]
            suf = row["key_suffix"]
            st = row.get("http_status")
            ok = row.get("ok")
            lr = row.get("limit_remaining")
            lbl = row.get("provider_key_label") or ""
            err = row.get("error")
            st_s = str(st) if st is not None else "ERR"
            ok_s = "yes" if ok else "no"
            lr_s = "" if lr is None else str(lr)
            if err:
                print(f"{env:<28} {suf:<14} {'---':<6} no   {err[:40]}")
            else:
                print(f"{env:<28} {suf:<14} {st_s:<6} {ok_s:<4} {lr_s:<11} {lbl}")

        print()
        if bad:
            print(f"Problems: {bad} / {len(rows)} (401 = bad token, 402 = often account/credits).")
        else:
            print(f"All {len(rows)} key slot(s) returned HTTP 200.")

    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
