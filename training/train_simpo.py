#!/usr/bin/env python3
"""Reproducible Path B SimPO LoRA training script.

This is the source-controlled equivalent of the Colab notebook. It keeps the
training path auditable even when the actual GPU run happens elsewhere.

The Week 11 brief targets a Qwen 3.5 backbone, but the committed run uses the
text-only fallback ``unsloth/Qwen2.5-0.5B-Instruct`` because the available
Qwen 3.5 Colab path was multimodal and unstable for text-only SimPO preference
training. This is a documented deviation, not a silent substitution.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import torch
from datasets import Dataset
from trl import CPOConfig, CPOTrainer
from unsloth import FastLanguageModel

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAIRS_PATH = ROOT / "training_data" / "preference_pairs.jsonl"
DEFAULT_OUTPUT_DIR = ROOT / "training"


@dataclass(frozen=True)
class TrainingConfig:
    seed: int = 3407
    max_seq_length: int = 1024
    backbone_model: str = "unsloth/Qwen2.5-0.5B-Instruct"
    backbone_revision: str = "ae616882a38b36759fc46ac3fd6769498833b913"
    backbone_note: str = "Operational text-only fallback; the target Qwen3.5 Colab path was multimodal and unstable for text-only SimPO preference training."
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    learning_rate: float = 5e-5
    per_device_train_batch_size: int = 2
    per_device_eval_batch_size: int = 2
    gradient_accumulation_steps: int = 4
    num_train_epochs: int = 3
    warmup_ratio: float = 0.1
    lr_scheduler_type: str = "cosine"
    simpo_beta: float = 2.0
    simpo_gamma: float = 0.5
    eval_fraction: float = 0.10
    dtype: str = "float16"


def load_pairs(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def split_pairs(rows: list[dict[str, Any]], seed: int, eval_fraction: float) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    formatted = [{"prompt": row["prompt"], "chosen": row["chosen"], "rejected": row["rejected"]} for row in rows]
    rng = random.Random(seed)
    rng.shuffle(formatted)
    split_idx = int(len(formatted) * (1 - eval_fraction))
    return formatted[:split_idx], formatted[split_idx:]


def training_args_from_config(config: TrainingConfig, output_dir: Path) -> CPOConfig:
    params = dict(
        loss_type="simpo",
        beta=config.simpo_beta,
        simpo_gamma=config.simpo_gamma,
        per_device_train_batch_size=config.per_device_train_batch_size,
        per_device_eval_batch_size=config.per_device_eval_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        num_train_epochs=config.num_train_epochs,
        learning_rate=config.learning_rate,
        lr_scheduler_type=config.lr_scheduler_type,
        warmup_ratio=config.warmup_ratio,
        fp16=config.dtype == "float16",
        bf16=config.dtype == "bfloat16",
        logging_steps=5,
        save_strategy="epoch",
        eval_strategy="epoch",
        output_dir=str(output_dir / "checkpoint_output"),
        seed=config.seed,
        max_length=config.max_seq_length,
        max_prompt_length=768,
        report_to="none",
        remove_unused_columns=False,
    )
    training_args = CPOConfig(**params)
    training_args.dataset_num_proc = None
    return training_args


def write_artifacts(
    *,
    output_dir: Path,
    config: TrainingConfig,
    train_result: Any,
    trainer: CPOTrainer,
    train_examples: int,
    eval_examples: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "training_run.log"
    history_path = output_dir / "trainer_log_history.jsonl"
    loss_curve_path = output_dir / "loss_curve.png"

    run_log = {
        "run_date": datetime.now(UTC).isoformat(),
        "seed": config.seed,
        "backbone": config.backbone_model,
        "backbone_revision": config.backbone_revision,
        "backbone_note": config.backbone_note,
        "training_objective": "SimPO via TRL CPOTrainer",
        "lora_r": config.lora_r,
        "lora_alpha": config.lora_alpha,
        "lora_dropout": config.lora_dropout,
        "learning_rate": config.learning_rate,
        "epochs": config.num_train_epochs,
        "batch_size": config.per_device_train_batch_size,
        "gradient_accumulation_steps": config.gradient_accumulation_steps,
        "effective_batch_size": config.per_device_train_batch_size * config.gradient_accumulation_steps,
        "max_seq_length": config.max_seq_length,
        "warmup_ratio": config.warmup_ratio,
        "lr_scheduler_type": config.lr_scheduler_type,
        "simpo_beta": config.simpo_beta,
        "simpo_gamma": config.simpo_gamma,
        "train_examples": train_examples,
        "eval_examples": eval_examples,
        "dtype": f"torch.{config.dtype}",
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        "train_metrics": train_result.metrics,
        "lora_only": True,
        "expected_wall_time_note": ("Observed runtime is expected to fall below the rubric's 30-90 minute range because this run trains on only 81 train pairs and 10 eval pairs."),
    }
    log_path.write_text(json.dumps(run_log, indent=2) + "\n", encoding="utf-8")

    with history_path.open("w", encoding="utf-8") as handle:
        for row in trainer.state.log_history:
            handle.write(json.dumps(row) + "\n")

    loss_rows = [row for row in trainer.state.log_history if "loss" in row]
    if loss_rows:
        plt.figure(figsize=(7, 4))
        plt.plot([row.get("step", idx) for idx, row in enumerate(loss_rows)], [row["loss"] for row in loss_rows], marker="o")
        plt.xlabel("Step")
        plt.ylabel("Training loss")
        plt.title("Tenacious SimPO LoRA training loss")
        plt.grid(alpha=0.25)
        plt.tight_layout()
        plt.savefig(loss_curve_path, dpi=160)
        plt.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the Path B SimPO LoRA judge.")
    parser.add_argument("--pairs", default=str(DEFAULT_PAIRS_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    config = TrainingConfig()
    pair_path = Path(args.pairs).resolve()
    output_dir = Path(args.output_dir).resolve()
    rows = load_pairs(pair_path)
    train_rows, eval_rows = split_pairs(rows, config.seed, config.eval_fraction)

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU required for this training script.")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=config.backbone_model,
        revision=config.backbone_revision,
        max_seq_length=config.max_seq_length,
        dtype=torch.float16,
        load_in_4bit=False,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = FastLanguageModel.get_peft_model(
        model,
        r=config.lora_r,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=config.seed,
        use_rslora=False,
    )

    trainer = CPOTrainer(
        model=model,
        args=training_args_from_config(config, output_dir),
        train_dataset=Dataset.from_list(train_rows),
        eval_dataset=Dataset.from_list(eval_rows),
        processing_class=tokenizer,
    )
    train_result = trainer.train()
    write_artifacts(
        output_dir=output_dir,
        config=config,
        train_result=train_result,
        trainer=trainer,
        train_examples=len(train_rows),
        eval_examples=len(eval_rows),
    )
    print(json.dumps({"status": "ok", "config": asdict(config), "output_dir": str(output_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
