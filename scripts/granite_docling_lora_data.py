"""Dataset and collator for Granite Docling LoRA fine-tuning targets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from torch.utils.data import Dataset

from scripts.granite_docling_prompt import build_prompt

EOS_TEXT = "<|end_of_text|>"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def target_with_single_eos(target: str) -> str:
    stripped = target.rstrip()
    if stripped.endswith(EOS_TEXT):
        return stripped
    return stripped + EOS_TEXT


class GraniteDoclingJsonlDataset(Dataset):
    def __init__(self, jsonl_path: Path, processor, max_length: int | None = None, limit: int | None = None):
        self.jsonl_path = Path(jsonl_path)
        self.processor = processor
        self.prompt = build_prompt(processor)
        self.max_length = max_length
        self.records = sorted(load_jsonl(self.jsonl_path), key=lambda r: r["image_id"])
        if limit is not None:
            self.records = self.records[:limit]
        if not self.records:
            raise ValueError(f"no records loaded from {self.jsonl_path}")

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        rec = self.records[idx]
        target = target_with_single_eos(rec["doctags_target"])
        image = Image.open(rec["image_path"]).convert("RGB")
        prompt_inputs = self.processor(text=[self.prompt], images=[image], return_tensors="pt", padding=False)
        full_inputs = self.processor(text=[self.prompt + target], images=[image], return_tensors="pt", padding=False)

        prompt_ids = prompt_inputs["input_ids"][0]
        input_ids = full_inputs["input_ids"][0]
        prompt_len = int(prompt_ids.numel())
        seq_len = int(input_ids.numel())
        if not torch.equal(input_ids[:prompt_len], prompt_ids):
            raise AssertionError(f"prompt token prefix mismatch for {rec['image_id']}")
        if self.max_length is not None and seq_len > self.max_length:
            raise AssertionError(f"tokenized length {seq_len} exceeds max_length {self.max_length} for {rec['image_id']}")

        attention_mask = full_inputs["attention_mask"][0]
        labels = input_ids.clone()
        labels[:prompt_len] = -100

        item: dict[str, Any] = {
            "image_id": rec["image_id"],
            "category": rec.get("category"),
            "image_path": rec["image_path"],
            "target_text": target,
            "prompt_text": self.prompt,
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
            "prompt_length": prompt_len,
            "sequence_length": seq_len,
            "supervised_length": int((labels != -100).sum().item()),
        }
        for key, value in full_inputs.items():
            if key in {"input_ids", "attention_mask"}:
                continue
            item[key] = value[0]
        return item

    def length_report(self) -> list[dict[str, Any]]:
        report = []
        for i in range(len(self)):
            item = self[i]
            report.append(
                {
                    "image_id": item["image_id"],
                    "prompt_length": item["prompt_length"],
                    "target_supervised_tokens": item["supervised_length"],
                    "sequence_length": item["sequence_length"],
                }
            )
        return report


@dataclass
class GraniteDoclingDataCollator:
    processor: Any
    label_pad_id: int = -100

    def __post_init__(self) -> None:
        tokenizer = self.processor.tokenizer
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        self.pad_token_id = int(tokenizer.pad_token_id)
        self.padding_side = getattr(tokenizer, "padding_side", "right")

    def _pad_1d(self, tensors: list[torch.Tensor], pad_value: int) -> torch.Tensor:
        max_len = max(int(t.numel()) for t in tensors)
        out = torch.full((len(tensors), max_len), pad_value, dtype=tensors[0].dtype)
        for i, tensor in enumerate(tensors):
            length = int(tensor.numel())
            if self.padding_side == "left":
                out[i, max_len - length :] = tensor
            else:
                out[i, :length] = tensor
        return out

    def _pad_image_tiles(self, tensors: list[torch.Tensor], pad_value: float | int = 0) -> torch.Tensor:
        max_tiles = max(int(t.shape[0]) for t in tensors)
        shape = (len(tensors), max_tiles, *tensors[0].shape[1:])
        out = torch.full(shape, pad_value, dtype=tensors[0].dtype)
        for i, tensor in enumerate(tensors):
            out[i, : tensor.shape[0]] = tensor
        return out

    def __call__(self, features: list[dict[str, Any]]) -> dict[str, Any]:
        batch: dict[str, Any] = {
            "input_ids": self._pad_1d([f["input_ids"] for f in features], self.pad_token_id),
            "attention_mask": self._pad_1d([f["attention_mask"] for f in features], 0),
            "labels": self._pad_1d([f["labels"] for f in features], self.label_pad_id),
            "image_ids": [f["image_id"] for f in features],
            "target_texts": [f["target_text"] for f in features],
            "prompt_lengths": torch.tensor([f["prompt_length"] for f in features], dtype=torch.long),
            "sequence_lengths": torch.tensor([f["sequence_length"] for f in features], dtype=torch.long),
        }
        for key in ("pixel_values", "pixel_attention_mask"):
            if key in features[0]:
                batch[key] = self._pad_image_tiles([f[key] for f in features], 0)
        return batch


def assert_all_lengths_fit(dataset: GraniteDoclingJsonlDataset, max_length: int) -> list[dict[str, Any]]:
    report = dataset.length_report()
    too_long = [row for row in report if row["sequence_length"] > max_length]
    if too_long:
        raise AssertionError(f"samples exceed max_length={max_length}: {too_long}")
    return report
