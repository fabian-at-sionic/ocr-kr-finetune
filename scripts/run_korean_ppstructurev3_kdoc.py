#!/usr/bin/env python3
import argparse
import inspect
import json
import threading
import time
from datetime import datetime, timezone, timedelta
from importlib import metadata
from pathlib import Path
from typing import Any

import fitz
import numpy as np
from PIL import Image


TITLE = "KOREAN PPStructureV3 (PP OCRv5) Pipeline BENCHMARK"
KST = timezone(timedelta(hours=9), name="KST")
REC_MODEL_NAME = "korean_PP-OCRv5_mobile_rec"


def package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def verify_gpu_paddle() -> dict[str, Any]:
    gpu_version = package_version("paddlepaddle-gpu")
    cpu_version = package_version("paddlepaddle")
    if cpu_version:
        raise RuntimeError(
            "CPU package 'paddlepaddle' is installed. Refusing to run; install only 'paddlepaddle-gpu'."
        )
    if not gpu_version:
        raise RuntimeError("GPU package 'paddlepaddle-gpu' is not installed.")

    import paddle

    compiled_with_cuda = bool(paddle.is_compiled_with_cuda())
    if not compiled_with_cuda:
        raise RuntimeError("'paddlepaddle-gpu' is installed but Paddle is not compiled with CUDA.")
    return {
        "paddlepaddle_gpu": gpu_version,
        "paddlepaddle_cpu": cpu_version,
        "paddle_version": getattr(paddle, "__version__", None),
        "compiled_with_cuda": compiled_with_cuda,
        "device": paddle.device.get_device(),
    }


def build_pipeline(rec_model_dir: Path | None, device: str) -> Any:
    from paddleocr import PPStructureV3

    kwargs = {
        "text_recognition_model_name": REC_MODEL_NAME,
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "use_textline_orientation": False,
        "use_formula_recognition": False,
        "use_seal_recognition": False,
        "use_chart_recognition": False,
        "device": device,
    }
    if rec_model_dir and rec_model_dir.exists():
        kwargs["text_recognition_model_dir"] = str(rec_model_dir)

    signature = inspect.signature(PPStructureV3)
    has_var_kwargs = any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values())
    if not has_var_kwargs:
        kwargs = {key: value for key, value in kwargs.items() if key in signature.parameters}
    return PPStructureV3(**kwargs)


def pipeline_spec(dataset_dir: Path, candidate: str, dpi: int, rec_model_dir: Path, device: str) -> dict[str, Any]:
    return {
        "title": TITLE,
        "pipeline": {
            "class": "PPStructureV3",
            "text_recognition_model_name": REC_MODEL_NAME,
            "text_recognition_model_dir": str(rec_model_dir),
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
            "use_formula_recognition": False,
            "use_seal_recognition": False,
            "use_chart_recognition": False,
            "device": device,
        },
        "dataset_dir": str(dataset_dir),
        "candidate": candidate,
        "dpi": dpi,
    }


def save_pipeline_manifest(path: Path, spec: dict[str, Any], paddle_info: dict[str, Any], pipeline: Any) -> None:
    interesting_methods = [
        name
        for name in dir(pipeline)
        if not name.startswith("_") and any(token in name.lower() for token in ("save", "export", "config"))
    ]
    manifest = {
        "created_at_kst": kst_now(),
        "pipeline_spec": spec,
        "runtime": {
            **paddle_info,
            "paddleocr": package_version("paddleocr"),
            "paddlex": package_version("paddlex"),
        },
        "pipeline_type": f"{type(pipeline).__module__}.{type(pipeline).__name__}",
        "available_save_or_config_methods": interesting_methods,
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_first_page(pdf_path: Path, dpi: int) -> Image.Image:
    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0), alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    finally:
        doc.close()


def result_to_markdown(result: Any) -> str:
    markdown = getattr(result, "markdown", None)
    if callable(markdown):
        markdown = markdown()
    if isinstance(markdown, dict):
        text = markdown.get("markdown_texts") or markdown.get("markdown") or ""
        if isinstance(text, list):
            return "\n\n".join(str(item) for item in text)
        return str(text)
    if markdown is not None:
        return str(markdown)
    if isinstance(result, dict):
        for key in ("markdown_texts", "rec_text", "text"):
            if key in result:
                return str(result[key])
    return str(result)


def write_jsonl(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def kst_now() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S %Z")


def eta_string(done: int, total: int, started_at: float) -> tuple[float, str | None, str | None]:
    progress = round(done * 100 / total, 3) if total else 100.0
    elapsed = time.time() - started_at
    rate = done / elapsed if done > 0 and elapsed > 0 else 0.0
    remaining = (total - done) / rate if rate > 0 else None
    eta = datetime.now(KST) + timedelta(seconds=remaining) if remaining is not None else None
    remaining_text = str(timedelta(seconds=int(remaining))) if remaining is not None else None
    eta_text = eta.strftime("%Y-%m-%d %H:%M:%S %Z") if eta else None
    return progress, remaining_text, eta_text


class ProgressReporter:
    def __init__(self, total: int, started_at: float, interval_seconds: int) -> None:
        self.total = total
        self.started_at = started_at
        self.interval_seconds = interval_seconds
        self.done = 0
        self.phase = "ocr"
        self.current_pdf = ""
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        if self.interval_seconds > 0:
            self._thread.start()

    def update(self, *, done: int | None = None, phase: str | None = None, current_pdf: str | None = None) -> None:
        with self._lock:
            if done is not None:
                self.done = done
            if phase is not None:
                self.phase = phase
            if current_pdf is not None:
                self.current_pdf = current_pdf

    def stop(self) -> None:
        self._stop.set()
        if self.interval_seconds > 0:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            with self._lock:
                done = self.done
                phase = self.phase
                current_pdf = self.current_pdf
            progress, remaining_text, eta_text = eta_string(done, self.total, self.started_at)
            print(
                f"{TITLE}. Phase={phase}; progress={progress:.3f}%; done={done}/{self.total}; "
                f"current={current_pdf}; remaining={remaining_text}; eta_kst={eta_text}",
                flush=True,
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=TITLE)
    parser.add_argument("--dataset-dir", type=Path, default=Path("dataset/KDoc-OCRBench-V2"))
    parser.add_argument("--candidate", default="korean_ppstructurev3_ppocrv5")
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--rec-model-dir", type=Path, default=Path("model/PaddlePaddle/korean_PP-OCRv5_mobile_rec"))
    parser.add_argument("--device", default="gpu:0")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--progress-interval-seconds", type=int, default=60)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    dataset_dir = args.dataset_dir.resolve()
    rec_model_dir = args.rec_model_dir.resolve()
    pdf_dir = dataset_dir / "pdfs"
    out_dir = dataset_dir / args.candidate
    out_dir.mkdir(parents=True, exist_ok=True)
    progress_path = out_dir / "run_progress.jsonl"
    errors_path = out_dir / "errors.jsonl"
    config_path = out_dir / "pipeline_config.json"
    manifest_path = out_dir / "pipeline_manifest.json"

    spec = pipeline_spec(dataset_dir, args.candidate, args.dpi, rec_model_dir, args.device)
    config_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if args.limit is not None:
        pdfs = pdfs[: args.limit]

    pending = []
    for pdf_path in pdfs:
        md_path = out_dir / f"{pdf_path.stem}_pg1_repeat1.md"
        if args.force or not md_path.exists():
            pending.append(pdf_path)

    print(f"{TITLE}. Phase=initialize pipeline; total={len(pdfs)}; pending={len(pending)}; kst={kst_now()}", flush=True)
    paddle_info = verify_gpu_paddle()
    print(
        f"{TITLE}. Phase=verify gpu paddle; paddlepaddle-gpu={paddle_info['paddlepaddle_gpu']}; "
        f"cpu_paddle={paddle_info['paddlepaddle_cpu']}; compiled_with_cuda={paddle_info['compiled_with_cuda']}; "
        f"device={paddle_info['device']}",
        flush=True,
    )
    pipeline = build_pipeline(rec_model_dir, args.device)
    save_pipeline_manifest(manifest_path, spec, paddle_info, pipeline)
    print(f"{TITLE}. Phase=save pipeline; config={config_path}; manifest={manifest_path}", flush=True)
    if args.prepare_only:
        print(f"{TITLE}. Phase=prepare complete; kst={kst_now()}", flush=True)
        return

    run_start = time.time()
    reporter = ProgressReporter(len(pending), run_start, args.progress_interval_seconds)
    reporter.start()
    try:
        for index, pdf_path in enumerate(pending, start=1):
            start = time.time()
            md_path = out_dir / f"{pdf_path.stem}_pg1_repeat1.md"
            reporter.update(done=index - 1, phase="render+ocr", current_pdf=pdf_path.name)
            try:
                image = render_first_page(pdf_path, dpi=args.dpi)
                results = pipeline.predict(np.asarray(image))
                reporter.update(phase="write output")
                markdown_parts = [result_to_markdown(result) for result in results]
                markdown = "\n\n".join(part for part in markdown_parts if part.strip()).strip()
                md_path.write_text(markdown + "\n", encoding="utf-8")

                elapsed = time.time() - start
                done = index
                total = len(pending)
                reporter.update(done=done, phase="ocr")
                progress, remaining_text, eta_text = eta_string(done, total, run_start)
                record = {
                    "title": TITLE,
                    "phase": "ocr",
                    "pdf": pdf_path.name,
                    "done": done,
                    "total": total,
                    "progress_pct": progress,
                    "seconds_per_pdf": round(elapsed, 3),
                    "markdown_chars": len(markdown),
                    "result_count": len(results),
                    "remaining": remaining_text,
                    "eta_kst": eta_text,
                    "finished_at_kst": kst_now(),
                }
                write_jsonl(progress_path, record)
                print(
                    f"{TITLE}. Phase=ocr; progress={record['progress_pct']:.3f}%; "
                    f"done={done}/{total}; seconds_per_pdf={record['seconds_per_pdf']}; "
                    f"markdown_chars={record['markdown_chars']}; remaining={record['remaining']}; "
                    f"eta_kst={record['eta_kst']}",
                    flush=True,
                )
            except Exception as exc:
                record = {
                    "title": TITLE,
                    "phase": "ocr",
                    "pdf": pdf_path.name,
                    "done": index - 1,
                    "total": len(pending),
                    "error": repr(exc),
                    "failed_at_kst": kst_now(),
                }
                write_jsonl(errors_path, record)
                print(f"{TITLE}. Phase=error; pdf={pdf_path.name}; error={exc!r}", flush=True)
                raise
    finally:
        reporter.stop()

    print(f"{TITLE}. Phase=complete; processed={len(pending)}; kst={kst_now()}", flush=True)


if __name__ == "__main__":
    main()
