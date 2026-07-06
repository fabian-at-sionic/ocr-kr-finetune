#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import torch
from PIL import Image
from peft import PeftModel
from transformers import AutoModelForVision2Seq, AutoProcessor
from docling_core.types.doc import DoclingDocument
from docling_core.types.doc.document import DocTagsDocument

from scripts.granite_docling_lora_data import EOS_TEXT, load_jsonl, target_with_single_eos
from scripts.granite_docling_prompt import build_prompt


def strip_eos_text(text: str) -> str:
    text = text.rstrip()
    if text.endswith(EOS_TEXT):
        return text[: -len(EOS_TEXT)]
    return text


def parse_with_docling(doctags: str, image: Image.Image, document_name: str) -> tuple[bool, str | None, int | None]:
    try:
        doctags_doc = DocTagsDocument.from_doctags_and_image_pairs([strip_eos_text(doctags)], [image])
        doc = DoclingDocument.load_from_doctags(doctags_doc, document_name=document_name)
        markdown = doc.export_to_markdown()
        return True, None, len(markdown)
    except Exception as exc:
        return False, repr(exc), None


def summarize(values: list[int]) -> dict:
    values = sorted(values)
    return {
        "count": len(values),
        "min": min(values),
        "p25": statistics.quantiles(values, n=4, method="inclusive")[0],
        "median": statistics.median(values),
        "p75": statistics.quantiles(values, n=4, method="inclusive")[2],
        "p90": statistics.quantiles(values, n=10, method="inclusive")[8],
        "p95": statistics.quantiles(values, n=20, method="inclusive")[18],
        "max": max(values),
        "mean": statistics.mean(values),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-jsonl", type=Path, default=Path("data/train_26.jsonl"))
    ap.add_argument("--model-dir", type=Path, default=Path("model/ibm-granite/granite-docling-258M"))
    ap.add_argument("--adapter-dir", type=Path, default=Path("runs/overfit_26/adapter"))
    ap.add_argument("--output-json", type=Path, default=Path("runs/overfit_26/generation_lengths_6144.json"))
    ap.add_argument("--max-new-tokens", type=int, default=6144)
    ap.add_argument("--batch-size", type=int, default=4)
    args = ap.parse_args()

    records = sorted(load_jsonl(args.data_jsonl), key=lambda r: r["image_id"])
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" else torch.float32
    processor = AutoProcessor.from_pretrained(args.model_dir)
    processor.tokenizer.padding_side = "left"
    prompt = build_prompt(processor)
    base = AutoModelForVision2Seq.from_pretrained(
        args.model_dir, dtype=dtype, _attn_implementation="sdpa"
    ).to(device)
    base.config.use_cache = True
    if hasattr(base.config, "text_config"):
        base.config.text_config.use_cache = True
    model = PeftModel.from_pretrained(base, args.adapter_dir).to(device)
    model.config.use_cache = True
    if hasattr(model.config, "text_config"):
        model.config.text_config.use_cache = True
    model.generation_config.use_cache = True
    model.eval()

    rows = []
    started = time.time()
    eos_text = processor.tokenizer.eos_token or EOS_TEXT
    with torch.inference_mode():
        for offset in range(0, len(records), args.batch_size):
            batch = records[offset : offset + args.batch_size]
            images = [Image.open(rec["image_path"]).convert("RGB") for rec in batch]
            inputs = processor(text=[prompt] * len(batch), images=images, return_tensors="pt", padding=True).to(device)
            batch_start = time.time()
            out = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False, use_cache=True)
            prompt_len = inputs.input_ids.shape[1]
            gen_ids = out[:, prompt_len:]
            decoded = processor.batch_decode(gen_ids, skip_special_tokens=False)
            elapsed = time.time() - batch_start
            for rec, image, ids, generated in zip(batch, images, gen_ids, decoded):
                generated = generated.lstrip()
                generated_tokens = int(ids.numel())
                target = target_with_single_eos(rec["doctags_target"])
                target_tokens = len(processor.tokenizer(target, add_special_tokens=False).input_ids)
                terminated = eos_text in generated
                parse_valid, parse_exception, markdown_chars = parse_with_docling(generated, image, rec["image_id"])
                rows.append({
                    "image_id": rec["image_id"],
                    "target_tokens": target_tokens,
                    "generated_tokens": generated_tokens,
                    "hit_cap": generated_tokens >= args.max_new_tokens,
                    "terminated": terminated,
                    "parse_valid": parse_valid,
                    "parse_exception": parse_exception,
                    "markdown_chars": markdown_chars,
                    "batch_size": len(batch),
                    "batch_seconds": round(elapsed, 3),
                })
            done = min(offset + len(batch), len(records))
            rate = done / max(time.time() - started, 1e-9)
            eta = (len(records) - done) / rate if rate else None
            print(json.dumps({"done": done, "total": len(records), "percent": round(done*100/len(records), 2), "batch_seconds": round(elapsed, 3), "eta_seconds": round(eta, 1) if eta is not None else None}, ensure_ascii=False), flush=True)

    generated_values = [r["generated_tokens"] for r in rows]
    target_values = [r["target_tokens"] for r in rows]
    result = {
        "max_new_tokens": args.max_new_tokens,
        "target_summary": summarize(target_values),
        "generation_summary": summarize(generated_values),
        "hit_cap_count": sum(r["hit_cap"] for r in rows),
        "hit_cap_percent": 100 * sum(r["hit_cap"] for r in rows) / len(rows),
        "terminated_count": sum(r["terminated"] for r in rows),
        "valid_parse_count": sum(r["parse_valid"] for r in rows),
        "valid_parse_percent": 100 * sum(r["parse_valid"] for r in rows) / len(rows),
        "rows": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("GEN_LENGTH_SUMMARY=" + json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
