#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import torch
from torch.utils.data import DataLoader
from transformers import AutoProcessor

from scripts.granite_docling_lora_data import (
    GraniteDoclingDataCollator,
    GraniteDoclingJsonlDataset,
    assert_all_lengths_fit,
)


def decode_ids(processor, ids: torch.Tensor) -> str:
    return processor.decode(ids.tolist(), skip_special_tokens=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, default=Path("model/ibm-granite/granite-docling-258M"))
    parser.add_argument("--data-jsonl", type=Path, default=Path("data/train_12.jsonl"))
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--max-length", type=int, default=8192)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    processor = AutoProcessor.from_pretrained(args.model_dir)
    processor.tokenizer.padding_side = "left"
    dataset = GraniteDoclingJsonlDataset(args.data_jsonl, processor, max_length=args.max_length, limit=args.limit)
    length_report = assert_all_lengths_fit(dataset, args.max_length)
    print("LENGTH_REPORT_JSON=" + json.dumps(length_report, ensure_ascii=False, sort_keys=True))

    collator = GraniteDoclingDataCollator(processor)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False, collate_fn=collator)
    batch = next(iter(loader))
    eos_id = processor.tokenizer.eos_token_id
    pad_id = processor.tokenizer.pad_token_id

    for i, image_id in enumerate(batch["image_ids"]):
        input_ids = batch["input_ids"][i]
        labels = batch["labels"][i]
        attention_mask = batch["attention_mask"][i]
        nonpad = attention_mask.bool()
        supervised_mask = labels != -100
        supervised_ids = input_ids[supervised_mask]
        supervised_text = decode_ids(processor, supervised_ids)
        expected_text = batch["target_texts"][i]
        eos_positions = torch.nonzero((input_ids == eos_id) & supervised_mask, as_tuple=False).flatten().tolist()
        pad_label_ok = bool(torch.all(labels[~nonpad] == -100).item()) if (~nonpad).any() else True
        prompt_mask_ok = bool(torch.all(labels[nonpad][: int(batch["prompt_lengths"][i])] == -100).item())
        print(f"\n=== SAMPLE {i} image_id={image_id} ===")
        print(f"sequence_length={int(batch['sequence_lengths'][i])}")
        print(f"collated_length={int(input_ids.numel())}")
        print(f"attention_mask_sum={int(attention_mask.sum().item())} vs sequence_length={int(batch['sequence_lengths'][i])}")
        print(f"supervised_tokens={int(supervised_mask.sum().item())}")
        print(f"eos_id={eos_id} pad_id={pad_id} supervised_eos_positions={eos_positions}")
        print(f"eos_position_supervised={bool(eos_positions)}")
        print(f"padding_labels_masked={pad_label_ok}")
        print(f"prompt_labels_masked={prompt_mask_ok}")
        print(f"supervised_text_exact_match_target={supervised_text == expected_text}")
        print("--- DECODED_FULL_INPUT_IDS_START ---")
        print(decode_ids(processor, input_ids[nonpad]))
        print("--- DECODED_FULL_INPUT_IDS_END ---")
        print("--- DECODED_SUPERVISED_ONLY_START ---")
        print(supervised_text)
        print("--- DECODED_SUPERVISED_ONLY_END ---")


if __name__ == "__main__":
    main()
