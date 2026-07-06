#!/usr/bin/env python3
import argparse
import html
import json
import os
import re
import time
from pathlib import Path

os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")

import fitz
from PIL import Image
try:
    from docling_core.types.doc import DoclingDocument
    from docling_core.types.doc.document import DocTagsDocument
except ModuleNotFoundError:
    DoclingDocument = None
    DocTagsDocument = None
from tqdm import tqdm
from transformers import AutoProcessor
from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest

PROMPT_TEXT = "Convert this page to docling."


def render_first_page(pdf_path: Path, dpi: int) -> Image.Image:
    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0), alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    finally:
        doc.close()


def doctags_to_markdown(doctags: str, image: Image.Image, document_name: str) -> str:
    if DoclingDocument is None or DocTagsDocument is None:
        raise RuntimeError("docling_core is not installed")
    doctags_doc = DocTagsDocument.from_doctags_and_image_pairs([doctags], [image])
    doc = DoclingDocument.load_from_doctags(doctags_doc, document_name=document_name)
    return doc.export_to_markdown()


def doctags_to_text_fallback(doctags: str) -> str:
    text = re.sub(r"<loc_\d+>", " ", doctags)
    text = re.sub(r"</(text|section_header_level_1|section_header_level_2|section_header_level_3|list_item|page_header|page_footer|otsl_cell)>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", default="dataset/KDoc-OCRBench-V2")
    parser.add_argument("--model-dir", default="model/ibm-granite/granite-docling-258M")
    parser.add_argument("--candidate", default="granite_docling_258m_vllm")
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.80)
    parser.add_argument("--adapter-dir", default=None)
    parser.add_argument("--lora-name", default="granite_docling_overfit26")
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

    pending = []
    for pdf_path in pdfs:
        md_path = out_dir / f"{pdf_path.stem}_pg1_repeat1.md"
        if not md_path.exists() or args.force:
            pending.append(pdf_path)

    processor = AutoProcessor.from_pretrained(args.model_dir)
    prompt = build_prompt(processor)
    llm = LLM(
        model=args.model_dir,
        limit_mm_per_prompt={"image": 1},
        gpu_memory_utilization=args.gpu_memory_utilization,
        tensor_parallel_size=1,
        trust_remote_code=False,
        enable_lora=args.adapter_dir is not None,
    )
    lora_request = (
        LoRARequest(args.lora_name, 1, args.adapter_dir)
        if args.adapter_dir is not None
        else None
    )
    sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=args.max_tokens,
        skip_special_tokens=False,
    )

    progress_path = out_dir / "run_progress.jsonl"
    errors_path = out_dir / "errors.jsonl"
    total = len(pdfs)
    started_at = time.time()
    completed_before = total - len(pending)

    with tqdm(total=len(pending), initial=0, desc="Granite vLLM OCR") as pbar:
        for offset in range(0, len(pending), args.batch_size):
            batch_paths = pending[offset : offset + args.batch_size]
            batch_start = time.time()
            try:
                images = [render_first_page(pdf_path, dpi=args.dpi) for pdf_path in batch_paths]
                requests = [
                    {"prompt": prompt, "multi_modal_data": {"image": image}}
                    for image in images
                ]
                outputs = llm.generate(requests, sampling_params, lora_request=lora_request)
                elapsed = time.time() - batch_start
                for pdf_path, image, output in zip(batch_paths, images, outputs):
                    doctags = output.outputs[0].text.lstrip()
                    conversion_error = None
                    try:
                        markdown = doctags_to_markdown(doctags, image, document_name=pdf_path.stem)
                    except Exception as exc:
                        conversion_error = repr(exc)
                        markdown = doctags_to_text_fallback(doctags)
                    md_path = out_dir / f"{pdf_path.stem}_pg1_repeat1.md"
                    raw_path = raw_dir / f"{pdf_path.stem}_pg1_repeat1.doctags"
                    raw_path.write_text(doctags, encoding="utf-8")
                    md_path.write_text(markdown, encoding="utf-8")
                    done = completed_before + offset + batch_paths.index(pdf_path) + 1
                    runtime = time.time() - started_at
                    rate = (offset + batch_paths.index(pdf_path) + 1) / runtime if runtime > 0 else 0.0
                    eta_seconds = (len(pending) - (offset + batch_paths.index(pdf_path) + 1)) / rate if rate > 0 else None
                    record = {
                        "pdf": pdf_path.name,
                        "done": done,
                        "total": total,
                        "percent": round(done * 100 / total, 3),
                        "batch_size": len(batch_paths),
                        "batch_seconds": round(elapsed, 3),
                        "seconds_per_pdf": round(elapsed / len(batch_paths), 3),
                        "eta_seconds": round(eta_seconds, 1) if eta_seconds is not None else None,
                        "markdown_chars": len(markdown),
                        "doctags_chars": len(doctags),
                        "finish_reason": getattr(output.outputs[0], "finish_reason", None),
                        "conversion_error": conversion_error,
                        "adapter_dir": args.adapter_dir,
                    }
                    with progress_path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
                pbar.update(len(batch_paths))
            except Exception as exc:
                elapsed = time.time() - batch_start
                for pdf_path in batch_paths:
                    record = {
                        "pdf": pdf_path.name,
                        "batch_size": len(batch_paths),
                        "batch_seconds": round(elapsed, 3),
                        "error": repr(exc),
                    }
                    with errors_path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
                raise


if __name__ == "__main__":
    main()
