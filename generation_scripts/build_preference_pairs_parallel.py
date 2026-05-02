"""Run build_preference_pairs across multiple OpenRouter API keys in parallel.

Splits the train split into N shards (default N = number of distinct keys) and runs
each shard in a thread with its own key. HTTP calls are I/O-bound; threads are enough.

Environment variables (first match wins per slot; all lists are de-duplicated):

  OPENROUTER_API_KEY                          primary key
  OPENROUTER_API_KEYS                         comma- or whitespace-separated keys
  OPENROUTER_API_KEY_1 .. OPENROUTER_API_KEY_99   numbered keys
  OPEN_ROUTER_KEY_1 .. OPEN_ROUTER_KEY_99       alternate spelling (see ``openrouter_env.py``)

Loads ``.env`` from the repo root (via python-dotenv) unless ``--no-dotenv``.

Omit broken duplicate slots (same secret listed twice under bad labels), e.g. key #4::

  export OPENROUTER_OMIT_KEY_SLOTS="OPEN_ROUTER_KEY_4,OPENROUTER_API_KEYS[4]"
  python3 generation_scripts/build_preference_pairs_parallel.py --workers 5

Optional ``--preflight-keys`` (default: on) calls ``GET /api/v1/key`` and drops keys whose
numeric ``limit_remaining`` is ``<= 0`` (null / unlimited is kept).

Example:

  export OPENROUTER_API_KEYS="sk-or-1,sk-or-2,sk-or-3,sk-or-4,sk-or-5"
  python3 generation_scripts/build_preference_pairs_parallel.py --workers 5

Note: Each shard maintains its own ``seen_chosen`` set for diversify logic; duplicate
``chosen`` strings across shards are slightly more likely than in a single serial run.
Personalized ground truth already reduces collision risk.

Outputs are merged in **shard order** (tasks appear in original train order within each
shard). Final files match the single-process script paths by default.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from generation_scripts.build_preference_pairs import (  # noqa: E402
    AUDIT_PATH,
    DEFAULT_GENERATOR,
    OUT_PATH,
    TRAIN_PATH,
    build_pairs,
)
from generation_scripts.openrouter_env import (  # noqa: E402
    gather_openrouter_key_bindings,
    omit_binding_labels,
    parse_omit_labels_from_env,
    unique_keys_ordered,
)

KEY_ENDPOINT = "https://openrouter.ai/api/v1/key"


def _mask(secret: str, *, keep: int = 8) -> str:
    if len(secret) <= keep:
        return "***"
    return f"...{secret[-keep:]}"


def _preflight_usable_keys(keys: list[str]) -> tuple[list[str], list[str]]:
    """Drop keys that fail GET /key or have numeric limit_remaining <= 0."""
    try:
        import httpx
    except ImportError:
        print("WARNING: httpx missing; skipping preflight.", file=sys.stderr)
        return keys, []

    usable: list[str] = []
    dropped: list[str] = []
    for k in keys:
        try:
            r = httpx.get(
                KEY_ENDPOINT,
                headers={"Authorization": f"Bearer {k}"},
                timeout=30.0,
            )
        except Exception as exc:
            dropped.append(f"{_mask(k)} (request error: {exc})")
            continue
        if r.status_code != 200:
            dropped.append(f"{_mask(k)} (HTTP {r.status_code})")
            continue
        try:
            payload = r.json()
        except json.JSONDecodeError:
            usable.append(k)
            continue
        data = payload.get("data") if isinstance(payload, dict) else None
        lr = data.get("limit_remaining") if isinstance(data, dict) else None
        if lr is not None and isinstance(lr, (int, float)) and lr <= 0:
            dropped.append(f"{_mask(k)} (limit_remaining={lr})")
            continue
        usable.append(k)

    return usable, dropped


def resolve_keys(*, omit_labels: list[str], preflight: bool) -> list[str]:
    bindings = gather_openrouter_key_bindings()
    bindings = omit_binding_labels(bindings, omit_labels)
    keys = unique_keys_ordered(bindings)
    if not preflight or not keys:
        return keys
    usable, dropped = _preflight_usable_keys(keys)
    if dropped:
        print("Preflight dropped keys:")
        for line in dropped:
            print(f"  - {line}")
    return usable


def chunk_tasks_even(tasks: list[dict], n_chunks: int) -> list[list[dict]]:
    """Split tasks into exactly ``n_chunks`` contiguous shards (sizes differ by at most 1)."""
    if not tasks:
        return []
    n_chunks = max(1, min(n_chunks, len(tasks)))
    base, extra = divmod(len(tasks), n_chunks)
    out: list[list[dict]] = []
    start = 0
    for i in range(n_chunks):
        sz = base + (1 if i < extra else 0)
        out.append(tasks[start : start + sz])
        start += sz
    return out


def _run_shard(
    shard_idx: int,
    shard: list[dict],
    api_key: str | None,
    generator_model: str,
    dry_run: bool,
    retry_delay: float,
) -> tuple[int, list[dict], list[dict]]:
    tail = f"...{api_key[-8:]}" if api_key and len(api_key) > 8 else (api_key or "none")
    print(f"[shard {shard_idx}] starting {len(shard)} tasks (key {tail})", flush=True)
    pairs, audit = build_pairs(
        shard,
        generator_model=generator_model,
        api_key=api_key,
        dry_run=dry_run,
        max_tasks=len(shard),
        retry_delay=retry_delay,
    )
    print(f"[shard {shard_idx}] done — accepted {sum(1 for a in audit if a['status'] == 'accepted')}", flush=True)
    return shard_idx, pairs, audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Parallel preference-pair build (multi OpenRouter keys)")
    parser.add_argument("--train-file", default=str(TRAIN_PATH))
    parser.add_argument("--out", default=str(OUT_PATH))
    parser.add_argument("--audit", default=str(AUDIT_PATH))
    parser.add_argument("--generator-model", default=DEFAULT_GENERATOR)
    parser.add_argument("--max-tasks", type=int, default=120)
    parser.add_argument("--retry-delay", type=float, default=0.5)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Parallel shards (default: number of API keys, or 1)",
    )
    parser.add_argument(
        "--no-dotenv",
        action="store_true",
        help="Do not load .env from repo root",
    )
    parser.add_argument(
        "--omit-key-slot",
        action="append",
        default=[],
        metavar="LABEL",
        help="Env label to skip, e.g. OPEN_ROUTER_KEY_4 (repeatable). Merged with OPENROUTER_OMIT_KEY_SLOTS.",
    )
    parser.add_argument(
        "--no-preflight-keys",
        action="store_true",
        help="Skip GET /api/v1/key balance filter before running",
    )
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv  # type: ignore
    except ImportError:
        load_dotenv = None  # type: ignore
    if load_dotenv and not args.no_dotenv:
        env_path = ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)

    omit_labels = parse_omit_labels_from_env() + list(args.omit_key_slot)
    keys = resolve_keys(
        omit_labels=omit_labels,
        preflight=(not args.no_preflight_keys) and not args.dry_run,
    )

    if omit_labels:
        print(f"Omitted slots    : {', '.join(omit_labels)}")
    if args.no_dotenv:
        print("Dotenv           : skipped (--no-dotenv)")
    elif load_dotenv is None:
        print("Dotenv           : python-dotenv not installed")
    elif (ROOT / ".env").exists():
        print(f"Dotenv           : loaded {ROOT / '.env'}")
    else:
        print(f"Dotenv           : no file at {ROOT / '.env'}")

    if not args.dry_run and not keys:
        print(
            "ERROR: No OpenRouter keys left after loading .env and omit/preflight filters.",
            file=sys.stderr,
        )
        print(
            "  Fix .env, adjust OPENROUTER_OMIT_KEY_SLOTS / --omit-key-slot, or --dry-run",
            file=sys.stderr,
        )
        return 2

    n_workers = args.workers or (len(keys) if keys else 1)
    if args.dry_run:
        n_workers = max(1, min(n_workers, 8))
    else:
        n_workers = max(1, min(n_workers, len(keys)))

    tasks = [json.loads(line) for line in Path(args.train_file).read_text().splitlines() if line.strip()]
    tasks = tasks[: args.max_tasks]

    shards = chunk_tasks_even(tasks, n_workers)
    # Assign key per shard; cycle if more shards than keys (unusual)
    key_per_shard: list[str | None] = []
    for i in range(len(shards)):
        if args.dry_run:
            key_per_shard.append(None)
        else:
            key_per_shard.append(keys[i % len(keys)])

    print(f"Loaded {len(tasks)} tasks → {len(shards)} shards, {n_workers} worker(s)")
    print(f"Keys in use     : {len(keys)} unique (dry-run={args.dry_run})")
    print()

    results: list[tuple[int, list[dict], list[dict]]] = []
    with ThreadPoolExecutor(max_workers=len(shards)) as pool:
        futs = []
        for i, shard in enumerate(shards):
            futs.append(
                pool.submit(
                    _run_shard,
                    i,
                    shard,
                    key_per_shard[i],
                    args.generator_model,
                    args.dry_run,
                    args.retry_delay,
                )
            )
        try:
            for fut in as_completed(futs):
                results.append(fut.result())
        except KeyboardInterrupt:
            print("\nInterrupted — cancelling pending shards...", file=sys.stderr)
            for f in futs:
                f.cancel()
            raise

    results.sort(key=lambda x: x[0])
    all_pairs: list[dict] = []
    all_audit: list[dict] = []
    for _, pairs, audit in results:
        all_pairs.extend(pairs)
        all_audit.extend(audit)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in all_pairs) + "\n")

    audit_path = Path(args.audit)
    audit_path.write_text("\n".join(json.dumps(a, ensure_ascii=False) for a in all_audit) + "\n")

    accepted = sum(1 for a in all_audit if a["status"] == "accepted")
    live = sum(1 for p in all_pairs if p["mode"] == "live")
    heuristic = sum(1 for p in all_pairs if p["mode"] == "heuristic")
    chosen_cnt = Counter(p.get("chosen", "") for p in all_pairs)
    uniq_chosen = len(chosen_cnt)
    max_rep = max(chosen_cnt.values(), default=0)

    print("\n--- Merged summary ---")
    print(f"Accepted pairs  : {accepted}")
    print(f"  live API      : {live}")
    print(f"  heuristic     : {heuristic}")
    print(f"Unique chosen   : {uniq_chosen} / {accepted} (max repeat {max_rep})")
    print(f"\nOutput : {out_path}")
    print(f"Audit  : {audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
