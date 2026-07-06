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
        names = []
        with categories_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    names.append(json.loads(line)["pdf"])
        return names
    return sorted(p.name for p in (dataset_dir / "pdfs").glob("*.pdf"))


def render_first_page(pdf_path: Path, scale: float) -> Image.Image:
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        page = pdf[0]
        bitmap = page.render(scale=scale)
        return bitmap.to_pil().convert("RGB")
    finally:
        pdf.close()


def doctags_to_markdown(doctags: str, image: Image.Image, document_name: str) -> str:
    doctags_doc = DocTagsDocument.from_doctags_and_image_pairs([doctags], [image])
    doc = DoclingDocument.load_from_doctags(doctags_doc, document_name=document_name)
    return doc.export_to_markdown()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", type=Path, default=Path("dataset/KDoc-OCRBench-V2"))
    parser.add_argument("--model-dir", type=Path, default=Path("model/docling-project/SmolDocling-256M-preview"))
    parser.add_argument("--candidate", default="smol_docling_256m")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--scale", type=float, default=2.0)
    parser.add_argument("--max-new-tokens", type=int, default=8192)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--attn-implementation", default="sdpa", choices=["sdpa", "eager"])
    args = parser.parse_args()

    dataset_dir = args.dataset_dir.resolve()
    output_dir = dataset_dir / args.candidate
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_names = load_pdf_names(dataset_dir)
    if args.limit is not None:
        pdf_names = pdf_names[: args.limit]

    processor = AutoProcessor.from_pretrained(args.model_dir, local_files_only=True)
    if args.device.startswith("cuda") and args.attn_implementation == "sdpa" and hasattr(torch.backends.cuda, "enable_cudnn_sdp"):
        torch.backends.cuda.enable_cudnn_sdp(False)

    model = AutoDoclingModel.from_pretrained(
        args.model_dir,
        local_files_only=True,
        torch_dtype=torch.bfloat16 if args.device.startswith("cuda") else torch.float32,
        _attn_implementation=args.attn_implementation,
    ).to(args.device)
    model.eval()

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": "Convert this page to docling."},
            ],
        }
    ]
    prompt = processor.apply_chat_template(messages, add_generation_prompt=True)

    started = time.time()
    failures = []
    for pdf_name in tqdm(pdf_names, desc="SmolDocling"):
        stem = Path(pdf_name).stem
        md_path = output_dir / f"{stem}_pg1_repeat1.md"
        dt_path = output_dir / f"{stem}_pg1_repeat1.dt"
        err_path = output_dir / f"{stem}_pg1_repeat1.err.json"
        if args.resume and md_path.exists():
            continue

        pdf_path = dataset_dir / "pdfs" / pdf_name
        try:
            image = render_first_page(pdf_path, args.scale)
            inputs = processor(text=prompt, images=[image], return_tensors="pt").to(args.device)
            with torch.inference_mode():
                generated_ids = model.generate(
                    **inputs,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=False,
                )
            prompt_length = inputs.input_ids.shape[1]
            doctags = processor.batch_decode(
                generated_ids[:, prompt_length:],
                skip_special_tokens=False,
            )[0].lstrip()
            dt_path.write_text(doctags, encoding="utf-8")
            markdown = doctags_to_markdown(doctags, image, stem)
            md_path.write_text(markdown, encoding="utf-8")
            if err_path.exists():
                err_path.unlink()
        except Exception as exc:
            failures.append({"pdf": pdf_name, "error": repr(exc)})
            err_path.write_text(json.dumps(failures[-1], ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "candidate": args.candidate,
        "model_dir": str(args.model_dir),
        "dataset_dir": str(dataset_dir),
        "requested_pdfs": len(pdf_names),
        "failures": len(failures),
        "elapsed_sec": round(time.time() - started, 3),
    }
    (output_dir / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures:
        raise SystemExit(f"{len(failures)} PDF(s) failed; see {output_dir}/*.err.json")


if __name__ == "__main__":
    main()
