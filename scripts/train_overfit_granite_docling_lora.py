#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
import time
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from peft import LoraConfig, get_peft_model
from torch.utils.data import DataLoader
from transformers import AutoModelForVision2Seq, AutoProcessor

from scripts.granite_docling_lora_data import GraniteDoclingDataCollator, GraniteDoclingJsonlDataset, assert_all_lengths_fit


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def move_batch(batch, device):
    out = {}
    for k, v in batch.items():
        out[k] = v.to(device) if torch.is_tensor(v) else v
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-jsonl", type=Path, default=Path("data/train_26.jsonl"))
    ap.add_argument("--model-dir", type=Path, default=Path("model/ibm-granite/granite-docling-258M"))
    ap.add_argument("--output-dir", type=Path, default=Path("runs/overfit_26"))
    ap.add_argument("--expected-count", type=int, default=26)
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--max-length", type=int, default=8192)
    ap.add_argument("--log-every", type=int, default=1)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--num-workers", type=int, default=0)
    args = ap.parse_args()

    if args.output_dir.exists():
        raise SystemExit(f"fresh output dir required, already exists: {args.output_dir}")
    lines = [l for l in args.data_jsonl.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(lines) != args.expected_count:
        raise SystemExit(f"expected {args.expected_count} records in {args.data_jsonl}, found {len(lines)}")

    set_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" else torch.float32
    processor = AutoProcessor.from_pretrained(args.model_dir)
    processor.tokenizer.padding_side = "left"
    dataset = GraniteDoclingJsonlDataset(args.data_jsonl, processor, max_length=args.max_length)
    length_report = assert_all_lengths_fit(dataset, args.max_length)
    collator = GraniteDoclingDataCollator(processor)
    generator = torch.Generator()
    generator.manual_seed(args.seed)
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=collator,
        num_workers=args.num_workers,
        generator=generator,
        persistent_workers=args.num_workers > 0,
    )

    model = AutoModelForVision2Seq.from_pretrained(
        args.model_dir,
        dtype=dtype,
        _attn_implementation="sdpa",
    )
    # Keep cache off during supervised training.
    model.config.use_cache = False
    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        modules_to_save=None,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    model.to(device)
    model.train()

    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.lr, weight_decay=0.0)
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "length_report.json").write_text(json.dumps(length_report, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {
        "data_jsonl": str(args.data_jsonl),
        "model_dir": str(args.model_dir),
        "records": len(dataset),
        "epochs": args.epochs,
        "lr": args.lr,
        "seed": args.seed,
        "max_length": args.max_length,
        "batch_size": args.batch_size,
        "num_workers": args.num_workers,
        "lora": lora_config.to_dict(),
    }
    with (args.output_dir / "run_config.json").open("w", encoding="utf-8") as f:
        json.dump(
            meta,
            f,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=lambda o: sorted(o) if isinstance(o, set) else str(o),
        )

    csv_path = args.output_dir / "loss.csv"
    losses = []
    step = 0
    started = time.time()
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["step", "epoch", "batch", "image_ids", "batch_size", "loss", "elapsed_seconds"],
        )
        writer.writeheader()
        for epoch in range(args.epochs):
            for batch_idx, batch in enumerate(loader):
                step += 1
                image_ids = batch["image_ids"]
                batch = move_batch(batch, device)
                optimizer.zero_grad(set_to_none=True)
                outputs = model(
                    input_ids=batch["input_ids"],
                    attention_mask=batch["attention_mask"],
                    pixel_values=batch.get("pixel_values"),
                    pixel_attention_mask=batch.get("pixel_attention_mask"),
                    labels=batch["labels"],
                )
                loss = outputs.loss
                if not torch.isfinite(loss):
                    raise RuntimeError(f"non-finite loss at step {step}: {loss}")
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                loss_value = float(loss.detach().cpu().item())
                losses.append(loss_value)
                row = {
                    "step": step,
                    "epoch": epoch + 1,
                    "batch": batch_idx,
                    "image_ids": ",".join(image_ids),
                    "batch_size": len(image_ids),
                    "loss": loss_value,
                    "elapsed_seconds": round(time.time() - started, 3),
                }
                writer.writerow(row)
                f.flush()
                if step % args.log_every == 0:
                    print(json.dumps(row, ensure_ascii=False), flush=True)

    model.save_pretrained(args.output_dir / "adapter")
    processor.save_pretrained(args.output_dir / "processor")
    plt.figure(figsize=(10, 5))
    plt.plot(range(1, len(losses) + 1), losses, linewidth=1)
    plt.xlabel("step")
    plt.ylabel("loss")
    plt.title("Granite Docling LoRA overfit loss")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(args.output_dir / "loss_curve.png", dpi=160)
    summary = {
        "steps": step,
        "final_loss": losses[-1] if losses else None,
        "min_loss": min(losses) if losses else None,
        "loss_csv": str(csv_path),
        "loss_curve": str(args.output_dir / "loss_curve.png"),
        "adapter": str(args.output_dir / "adapter"),
    }
    (args.output_dir / "train_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print("TRAIN_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
