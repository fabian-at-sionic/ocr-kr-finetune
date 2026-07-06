#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path

import pypdfium2 as pdfium
import torch
from docling_core.types.doc import DoclingDocument
from docling_core.types.doc.document import DocTagsDocument
from PIL import Image
from tqdm import tqdm
try:
    from transformers import AutoModelForVision2Seq as AutoDoclingModel
except ImportError:
    from transformers import AutoModelForImageTextToText as AutoDoclingModel
from transformers import AutoProcessor


def load_pdf_names(dataset_dir: Path) -> list[str]:
    categories_path = dataset_dir / "categories.jsonl"
    if categories_path.exists():
        with categories_path.open("r", encoding="utf-8") as f:
            return [json.loads(line)["pdf"] for line in f if line.strip()]
    return sorted(p.name for p in (dataset_dir / "pdfs").glob("*.pdf"))


def render_first_page(pdf_path: Path, scale: float) -> Image.Image:
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        return pdf[0].render(scale=scale).to_pil().convert("RGB")
    finally:
        pdf.close()


def doctags_to_markdown(doctags: str, image: Image.Image, document_name: str) -> str:
    doctags_doc = DocTagsDocument.from_doctags_and_image_pairs([doctags], [image])
    doc = DoclingDocument.load_from_doctags(doctags_doc, document_name=document_name)
    return doc.export_to_markdown()


def chunks(items: list[str], size: int):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", type=Path, default=Path("dataset/KDoc-OCRBench-V2"))
    parser.add_argument("--model-dir", type=Path, default=Path("model/docling-project/SmolDocling-256M-preview"))
    parser.add_argument("--candidate", default="smol_docling_256m")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--scale", type=float, default=2.0)
    parser.add_argument("--max-new-tokens", type=int, default=8192)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--attn-implementation", default="eager", choices=["eager", "sdpa"])
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    dataset_dir = args.dataset_dir.resolve()
    output_dir = dataset_dir / args.candidate
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_names = load_pdf_names(dataset_dir)
    if args.limit is not None:
        pdf_names = pdf_names[: args.limit]
    if args.resume:
        pdf_names = [
            name for name in pdf_names
            if not (output_dir / f"{Path(name).stem}_pg1_repeat1.md").exists()
        ]

    processor = AutoProcessor.from_pretrained(args.model_dir, local_files_only=True)
    eos_token_ids = []
    if hasattr(processor, "tokenizer"):
        processor.tokenizer.padding_side = "left"
        for token_id in (processor.tokenizer.eos_token_id, processor.tokenizer.convert_tokens_to_ids("<end_of_utterance>")):
            if isinstance(token_id, int) and token_id >= 0 and token_id not in eos_token_ids:
                eos_token_ids.append(token_id)
        pad_token_id = processor.tokenizer.pad_token_id
    else:
        pad_token_id = None
    if args.device.startswith("cuda") and args.attn_implementation == "sdpa" and hasattr(torch.backends.cuda, "enable_cudnn_sdp"):
        torch.backends.cuda.enable_cudnn_sdp(False)
    model = AutoDoclingModel.from_pretrained(
        args.model_dir,
        local_files_only=True,
        torch_dtype=torch.bfloat16 if args.device.startswith("cuda") else torch.float32,
        _attn_implementation=args.attn_implementation,
    ).to(args.device)
    model.eval()

    messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": "Convert this page to docling."}]}]
    prompt = processor.apply_chat_template(messages, add_generation_prompt=True)

    started = time.time()
    failures = []
    done = 0
    for batch_names in tqdm(list(chunks(pdf_names, args.batch_size)), desc="SmolDocling batches"):
        images = []
        active_names = []
        for pdf_name in batch_names:
            try:
                images.append(render_first_page(dataset_dir / "pdfs" / pdf_name, args.scale))
                active_names.append(pdf_name)
            except Exception as exc:
                failures.append({"pdf": pdf_name, "stage": "render", "error": repr(exc)})
        if not active_names:
            continue
        try:
            inputs = processor(text=[prompt] * len(images), images=images, return_tensors="pt", padding=True).to(args.device)
            with torch.inference_mode():
                generated_ids = model.generate(
                    **inputs,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=False,
                    eos_token_id=eos_token_ids or None,
                    pad_token_id=pad_token_id,
                )
            prompt_length = inputs.input_ids.shape[1]
            doctags_batch = processor.batch_decode(generated_ids[:, prompt_length:], skip_special_tokens=False)
        except Exception as exc:
            for pdf_name in active_names:
                failures.append({"pdf": pdf_name, "stage": "generate", "error": repr(exc)})
            continue

        for pdf_name, image, doctags in zip(active_names, images, doctags_batch):
            stem = Path(pdf_name).stem
            md_path = output_dir / f"{stem}_pg1_repeat1.md"
            dt_path = output_dir / f"{stem}_pg1_repeat1.dt"
            err_path = output_dir / f"{stem}_pg1_repeat1.err.json"
            try:
                doctags = doctags.lstrip()
                if "<|im_end|>" in doctags:
                    doctags = doctags.split("<|im_end|>", 1)[0].rstrip()
                if doctags.count("<end_of_utterance>") > 1:
                    doctags = doctags.split("<end_of_utterance>", 1)[0].rstrip() + "<end_of_utterance>"
                dt_path.write_text(doctags, encoding="utf-8")
                md_path.write_text(doctags_to_markdown(doctags, image, stem), encoding="utf-8")
                if err_path.exists():
                    err_path.unlink()
                done += 1
            except Exception as exc:
                failure = {"pdf": pdf_name, "stage": "postprocess", "error": repr(exc)}
                failures.append(failure)
                err_path.write_text(json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "candidate": args.candidate,
        "model_dir": str(args.model_dir),
        "dataset_dir": str(dataset_dir),
        "completed_pdfs": done,
        "remaining_or_failed": len(failures),
        "elapsed_sec": round(time.time() - started, 3),
        "batch_size": args.batch_size,
        "max_new_tokens": args.max_new_tokens,
        "attn_implementation": args.attn_implementation,
    }
    (output_dir / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures:
        (output_dir / "run_failures.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in failures), encoding="utf-8")
        raise SystemExit(f"{len(failures)} PDF(s) failed; see {output_dir / 'run_failures.jsonl'}")


if __name__ == "__main__":
    main()
