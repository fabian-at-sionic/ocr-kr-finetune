#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path

import fitz
import torch
from PIL import Image
from docling_core.types.doc import DoclingDocument
from docling_core.types.doc.document import DocTagsDocument
from tqdm import tqdm
from transformers import AutoModelForVision2Seq, AutoProcessor


PROMPT_TEXT = "Convert this page to docling."


def render_first_page(pdf_path: Path, dpi: int) -> Image.Image:
    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0), alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    finally:
        doc.close()


EOS_TEXT = "<|end_of_text|>"


def strip_generation_eos(doctags: str) -> str:
    doctags = doctags.rstrip()
    if doctags.endswith(EOS_TEXT):
        return doctags[: -len(EOS_TEXT)]
    return doctags


def doctags_to_markdown(doctags: str, image: Image.Image, document_name: str) -> str:
    doctags_doc = DocTagsDocument.from_doctags_and_image_pairs([strip_generation_eos(doctags)], [image])
    doc = DoclingDocument.load_from_doctags(doctags_doc, document_name=document_name)
    return doc.export_to_markdown()



def build_prompt(processor) -> str:
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": PROMPT_TEXT},
            ],
        },
    ]
    return processor.apply_chat_template(messages, add_generation_prompt=True)


def first_eos_length(ids: torch.Tensor, eos_token_id: int | None, max_new_tokens: int) -> tuple[int, bool, bool]:
    if eos_token_id is not None:
        eos_positions = torch.nonzero(ids == eos_token_id, as_tuple=False).flatten()
        if int(eos_positions.numel()) > 0:
            length = int(eos_positions[0].item()) + 1
            return length, True, False
    length = int(ids.numel())
    return length, False, length >= max_new_tokens


def run_batch(processor, model, prompt: str, pdf_paths: list[Path], dpi: int, max_new_tokens: int, device: str):
    images = [render_first_page(pdf_path, dpi=dpi) for pdf_path in pdf_paths]
    inputs = processor(text=[prompt] * len(images), images=images, return_tensors="pt", padding=True).to(device)
    with torch.inference_mode():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            use_cache=True,
        )
    prompt_length = inputs.input_ids.shape[1]
    trimmed_ids = generated_ids[:, prompt_length:]
    eos_token_id = processor.tokenizer.eos_token_id
    results = []
    for pdf_path, image, ids in zip(pdf_paths, images, trimmed_ids):
        generated_tokens, terminated, hit_cap = first_eos_length(ids, eos_token_id, max_new_tokens)
        effective_ids = ids[:generated_tokens]
        doctags = processor.decode(effective_ids.tolist(), skip_special_tokens=False).lstrip()
        parse_valid = True
        parse_exception = None
        markdown = None
        try:
            markdown = doctags_to_markdown(doctags, image, document_name=pdf_path.stem)
        except Exception as exc:
            parse_valid = False
            parse_exception = repr(exc)
        results.append(
            {
                "doctags": doctags,
                "markdown": markdown,
                "generated_tokens": generated_tokens,
                "terminated": terminated,
                "hit_cap": hit_cap,
                "parse_valid": parse_valid,
                "parse_exception": parse_exception,
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", default="dataset/KDoc-OCRBench-V2")
    parser.add_argument("--model-dir", default="model/ibm-granite/granite-docling-258M")
    parser.add_argument("--candidate", default="granite_docling_258m")
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--max-new-tokens", type=int, default=8192)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--adapter-dir", default=None)
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    pdf_dir = dataset_dir / "pdfs"
    out_dir = dataset_dir / args.candidate
    raw_dir = out_dir / "doctags"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if args.limit is not None:
        pdfs = pdfs[: args.limit]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" else torch.float32
    processor = AutoProcessor.from_pretrained(args.model_dir)
    processor.tokenizer.padding_side = "left"
    model = AutoModelForVision2Seq.from_pretrained(
        args.model_dir,
        torch_dtype=dtype,
        _attn_implementation="sdpa",
    ).to(device)
    model.config.use_cache = True
    if hasattr(model.config, "text_config"):
        model.config.text_config.use_cache = True
    if args.adapter_dir is not None:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, args.adapter_dir).to(device)
    model.config.use_cache = True
    if hasattr(model.config, "text_config"):
        model.config.text_config.use_cache = True
    model.generation_config.use_cache = True
    model.eval()
    prompt = build_prompt(processor)

    progress_path = out_dir / "run_progress.jsonl"
    errors_path = out_dir / "errors.jsonl"

    pending = []
    for pdf_path in pdfs:
        md_path = out_dir / f"{pdf_path.stem}_pg1_repeat1.md"
        if not md_path.exists() or args.force:
            pending.append(pdf_path)

    for offset in tqdm(range(0, len(pending), args.batch_size), desc="Granite OCR"):
        batch_paths = pending[offset : offset + args.batch_size]
        start = time.time()
        try:
            batch_results = run_batch(
                processor=processor,
                model=model,
                prompt=prompt,
                pdf_paths=batch_paths,
                dpi=args.dpi,
                max_new_tokens=args.max_new_tokens,
                device=device,
            )
            elapsed = time.time() - start
            for pdf_path, result in zip(batch_paths, batch_results):
                md_path = out_dir / f"{pdf_path.stem}_pg1_repeat1.md"
                raw_path = raw_dir / f"{pdf_path.stem}_pg1_repeat1.doctags"
                doctags = result["doctags"]
                markdown = result["markdown"]
                raw_path.write_text(doctags, encoding="utf-8")
                if markdown is not None:
                    md_path.write_text(markdown, encoding="utf-8")
                record = {
                    "pdf": pdf_path.name,
                    "batch_size": len(batch_paths),
                    "batch_seconds": round(elapsed, 3),
                    "seconds_per_pdf": round(elapsed / len(batch_paths), 3),
                    "markdown_chars": len(markdown) if markdown is not None else 0,
                    "doctags_chars": len(doctags),
                    "generated_tokens": result["generated_tokens"],
                    "terminated": result["terminated"],
                    "hit_cap": result["hit_cap"],
                    "parse_valid": result["parse_valid"],
                    "parse_exception": result["parse_exception"],
                    "adapter_dir": args.adapter_dir,
                }
                with progress_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                if not result["parse_valid"]:
                    with errors_path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:
            for pdf_path in batch_paths:
                record = {
                    "pdf": pdf_path.name,
                    "batch_size": len(batch_paths),
                    "batch_seconds": round(time.time() - start, 3),
                    "error": repr(exc),
                }
                with errors_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            raise


if __name__ == "__main__":
    main()
