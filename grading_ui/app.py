import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LABELS_DIR = REPO_ROOT / "human_labels"
DEFAULT_PASS1_PATH = DEFAULT_LABELS_DIR / "pass1_labels.json"


@dataclass(frozen=True)
class LoadedTask:
    task_id: str
    task_type: str
    thread_stage: str
    checks: list[str]
    signal_line: str
    signal_confidence: str
    bench_summary: dict | None
    subject: str
    body: str
    raw_task: dict


def _safe_read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def _safe_write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True))
    os.replace(tmp, path)


def _load_eval_examples() -> dict[str, LoadedTask]:
    out: dict[str, LoadedTask] = {}
    examples_dir = REPO_ROOT / "eval_examples"
    if not examples_dir.exists():
        return out

    for p in sorted(examples_dir.glob("tbv*.json")):
        obj = _safe_read_json(p)
        if not obj or "task" not in obj:
            continue
        task = obj["task"]
        inp = task.get("input", {})
        sb = inp.get("signal_brief", {}) or {}
        cand = task.get("candidate_output", {}) or {}
        rubric = task.get("rubric", {}) or {}
        checks = list(rubric.get("deterministic_checks", []) or [])

        loaded = LoadedTask(
            task_id=task.get("task_id", p.stem),
            task_type=task.get("task_type", "unknown"),
            thread_stage=inp.get("thread_stage", "unknown"),
            checks=checks,
            signal_line=sb.get("signal_line", ""),
            signal_confidence=sb.get("signal_confidence_tier", ""),
            bench_summary=inp.get("bench_summary"),
            subject=cand.get("subject", ""),
            body=cand.get("body", ""),
            raw_task=task,
        )
        out[loaded.task_id] = loaded

    return out


def _load_partition_tasks(path: Path) -> dict[str, LoadedTask]:
    out: dict[str, LoadedTask] = {}
    if not path.exists():
        return out

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            task = json.loads(line)
        except json.JSONDecodeError:
            continue

        inp = task.get("input", {}) or {}
        sb = inp.get("signal_brief", {}) or {}
        cand = task.get("candidate_output", {}) or {}
        rubric = task.get("rubric", {}) or {}
        checks = list(rubric.get("deterministic_checks", []) or [])

        loaded = LoadedTask(
            task_id=task.get("task_id", ""),
            task_type=task.get("task_type", "unknown"),
            thread_stage=inp.get("thread_stage", "unknown"),
            checks=checks,
            signal_line=sb.get("signal_line", ""),
            signal_confidence=sb.get("signal_confidence_tier", ""),
            bench_summary=inp.get("bench_summary"),
            subject=cand.get("subject", ""),
            body=cand.get("body", ""),
            raw_task=task,
        )
        if loaded.task_id:
            out[loaded.task_id] = loaded
    return out


def _load_tasks(source: str) -> dict[str, LoadedTask]:
    if source == "eval_examples":
        return _load_eval_examples()

    base = REPO_ROOT / "tenacious_bench_v0.1"
    if source == "train":
        return _load_partition_tasks(base / "train" / "tasks.jsonl")
    if source == "dev":
        return _load_partition_tasks(base / "dev" / "tasks.jsonl")
    if source == "held_out":
        return _load_partition_tasks(base / "held_out" / "tasks.jsonl")

    return {}


def _load_labels(path: Path) -> dict:
    existing = _safe_read_json(path)
    if isinstance(existing, dict):
        return existing
    return {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "labels": {},
        "notes": {},
    }


def _upsert_label(labels_obj: dict, task_id: str, check_name: str, verdict: str) -> None:
    labels_obj.setdefault("labels", {})
    labels_obj["labels"].setdefault(task_id, {})
    labels_obj["labels"][task_id][check_name] = {
        "verdict": verdict,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def _task_completion(labels_obj: dict, task: LoadedTask) -> tuple[int, int]:
    labels = labels_obj.get("labels", {}) or {}
    tlabels = labels.get(task.task_id, {}) or {}
    done = 0
    for c in task.checks:
        v = tlabels.get(c, {}).get("verdict")
        if v in {"PASS", "FAIL"}:
            done += 1
    return done, len(task.checks)


st.set_page_config(page_title="Tenacious Bench — Human Grader", layout="wide")
st.title("Tenacious Bench — Human Pass Grader")

with st.sidebar:
    st.header("Load tasks")
    source = st.selectbox(
        "Source",
        options=["eval_examples", "train", "dev", "held_out"],
        help="Start with eval_examples for the 10-task subset.",
    )
    tasks = _load_tasks(source)
    if not tasks:
        st.error("No tasks found for this source.")
        st.stop()

    labels_path_str = st.text_input("Autosave file", value=str(DEFAULT_PASS1_PATH))
    labels_path = Path(labels_path_str)
    labels_obj = _load_labels(labels_path)

    task_ids = sorted(tasks.keys())
    default_task_id = task_ids[0]
    selected_task_id = st.selectbox("Task", options=task_ids, index=task_ids.index(default_task_id))
    selected = tasks[selected_task_id]

    done, total = _task_completion(labels_obj, selected)
    st.caption(f"Task progress: {done}/{total} checks labeled")

    st.divider()
    st.subheader("Overall progress")
    completed = 0
    for t in tasks.values():
        d, tot = _task_completion(labels_obj, t)
        if tot > 0 and d == tot:
            completed += 1
    st.write(f"Completed tasks: **{completed} / {len(tasks)}**")

left, right = st.columns([1, 1])
with left:
    st.subheader("Context")
    st.write(f"**Task ID:** `{selected.task_id}`")
    st.write(f"**Type:** `{selected.task_type}`")
    st.write(f"**Stage:** `{selected.thread_stage}`")
    st.write(f"**Checks:** `{', '.join(selected.checks)}`")
    st.write(f"**Signal:** {selected.signal_line}")
    if selected.signal_confidence:
        st.write(f"**Signal confidence:** `{selected.signal_confidence}`")
    if selected.bench_summary is not None:
        with st.expander("Bench summary"):
            st.json(selected.bench_summary)

with right:
    st.subheader("Candidate email (grade this)")
    st.text_input("Subject", value=selected.subject, disabled=True)
    st.text_area("Body", value=selected.body, height=240, disabled=True)

st.subheader("Your labels")
st.caption("Pick PASS/FAIL for each check. Autosaves after every change.")

for check_name in selected.checks:
    key = f"label::{labels_path}::{selected.task_id}::{check_name}"
    existing_verdict = labels_obj.get("labels", {}).get(selected.task_id, {}).get(check_name, {}).get("verdict")
    default = 0 if existing_verdict == "PASS" else 1 if existing_verdict == "FAIL" else 2

    verdict = st.radio(
        check_name,
        options=["PASS", "FAIL", "—"],
        index=default,
        horizontal=True,
        key=key,
    )
    if verdict in {"PASS", "FAIL"}:
        _upsert_label(labels_obj, selected.task_id, check_name, verdict)

_safe_write_json(labels_path, labels_obj)
st.success(f"Saved: `{labels_path}`")

with st.expander("Download labels JSON"):
    st.download_button(
        "Download",
        data=json.dumps(labels_obj, indent=2, sort_keys=True).encode("utf-8"),
        file_name=Path(labels_path).name,
        mime="application/json",
    )
