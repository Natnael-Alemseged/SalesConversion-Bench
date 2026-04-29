from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Agreement:
    matches: int
    total: int

    @property
    def ratio(self) -> float:
        return (self.matches / self.total) if self.total else 0.0


def _load_labels(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_verdicts(labels_obj: dict) -> Iterable[tuple[str, str, str]]:
    """
    Yields (task_id, check_name, verdict) where verdict is PASS/FAIL.
    """
    labels = labels_obj.get("labels", {}) or {}
    for task_id, checks in labels.items():
        if not isinstance(checks, dict):
            continue
        for check_name, payload in checks.items():
            verdict = (payload or {}).get("verdict")
            if verdict in {"PASS", "FAIL"}:
                yield task_id, check_name, verdict


def _as_map(labels_obj: dict) -> dict[tuple[str, str], str]:
    return {(tid, chk): v for tid, chk, v in _iter_verdicts(labels_obj)}


def _agreement(pass1: dict[tuple[str, str], str], pass2: dict[tuple[str, str], str]) -> tuple[Agreement, list[tuple[str, str]]]:
    keys = sorted(set(pass1.keys()) | set(pass2.keys()))
    missing = [k for k in keys if k not in pass1 or k not in pass2]
    comparable = [k for k in keys if k in pass1 and k in pass2]
    matches = sum(1 for k in comparable if pass1[k] == pass2[k])
    return Agreement(matches=matches, total=len(comparable)), missing


def _by_dimension(pass1: dict[tuple[str, str], str], pass2: dict[tuple[str, str], str]) -> dict[str, Agreement]:
    dims: dict[str, list[tuple[str, str]]] = {}
    for tid, chk in set(pass1.keys()) | set(pass2.keys()):
        dims.setdefault(chk, []).append((tid, chk))

    out: dict[str, Agreement] = {}
    for chk, keys in dims.items():
        comparable = [k for k in keys if k in pass1 and k in pass2]
        matches = sum(1 for k in comparable if pass1[k] == pass2[k])
        out[chk] = Agreement(matches=matches, total=len(comparable))
    return dict(sorted(out.items(), key=lambda kv: kv[0]))


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare human Pass 1 vs Pass 2 labels.")
    parser.add_argument("--pass1", required=True, help="Path to pass1_labels.json")
    parser.add_argument("--pass2", required=True, help="Path to pass2_labels.json")
    args = parser.parse_args()

    p1 = _as_map(_load_labels(Path(args.pass1)))
    p2 = _as_map(_load_labels(Path(args.pass2)))

    overall, missing = _agreement(p1, p2)
    per_dim = _by_dimension(p1, p2)

    report = {
        "overall": {"matches": overall.matches, "total": overall.total, "agreement": round(overall.ratio, 4)},
        "per_dimension": {dim: {"matches": a.matches, "total": a.total, "agreement": round(a.ratio, 4)} for dim, a in per_dim.items()},
        "missing_pairs": [{"task_id": tid, "check": chk} for (tid, chk) in missing],
    }

    print(json.dumps(report, indent=2, sort_keys=True))
    # non-zero if incomplete comparison due to missing labels
    return 2 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
