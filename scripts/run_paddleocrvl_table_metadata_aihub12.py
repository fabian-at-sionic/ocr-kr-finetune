#!/usr/bin/env python3
"""Extract table metadata from AIHUB document images with PaddleOCR-VL 1.6."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from lxml import etree, html
from PIL import Image, ImageDraw

TITLE = "VL1.6 TABLE METADATA GENERATION"
KST = timezone(timedelta(hours=9), name="KST")
MODEL_NAME = "PaddleOCR-VL-1.6-0.9B"
DEFAULT_OUT = Path("benchmark_work/paddleocrvl_table_metadata_aihub12/paddleocrvl_vllm_table_structure")
DEFAULT_MANIFEST = Path("benchmark_work/paddleocrvl_table_metadata_aihub12/input/aihub12_manifest.json")


@dataclass
class RunStats:
    images_seen: int = 0
    images_processed: int = 0
    images_skipped: int = 0
    images_failed: int = 0
    tables_found: int = 0
    html_parse_failures: int = 0
    non_rectangular_grids: int = 0
    startup_seconds: float = 0.0
    inference_seconds_total: float = 0.0


class GpuSampler:
    def __init__(self, interval_seconds: float = 1.0) -> None:
        self.interval_seconds = interval_seconds
        self.samples: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                out = subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-gpu=timestamp,utilization.gpu,memory.used,power.draw",
                        "--format=csv,noheader,nounits",
                    ],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
                parts = [p.strip() for p in out.split(",")]
                self.samples.append(
                    {
                        "t": time.time(),
                        "timestamp": parts[0] if len(parts) > 0 else None,
                        "util_gpu_pct": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None,
                        "mem_mib": int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None,
                        "power_w": float(parts[3]) if len(parts) > 3 else None,
                    }
                )
            except Exception as exc:  # recorded, not swallowed
                self.samples.append({"t": time.time(), "error": repr(exc)})
            self._stop.wait(self.interval_seconds)

    def summary(self) -> dict[str, Any]:
        utils = [s["util_gpu_pct"] for s in self.samples if isinstance(s.get("util_gpu_pct"), int)]
        mems = [s["mem_mib"] for s in self.samples if isinstance(s.get("mem_mib"), int)]
        power = [s["power_w"] for s in self.samples if isinstance(s.get("power_w"), (int, float))]
        return {
            "sample_count": len(self.samples),
            "avg_gpu_util_pct": mean(utils) if utils else None,
            "max_gpu_util_pct": max(utils) if utils else None,
            "max_mem_mib": max(mems) if mems else None,
            "avg_power_w": mean(power) if power else None,
            "max_power_w": max(power) if power else None,
        }


def kst_now() -> datetime:
    return datetime.now(KST)


def iso_kst(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def load_completed_image_ids(path: Path) -> set[str]:
    done: set[str] = set()
    if not path.exists():
        return done
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            image_id = rec.get("image_id")
            if image_id:
                done.add(str(image_id))
    return done


def verify_paddle_cuda() -> dict[str, Any]:
    import paddle

    if not paddle.device.is_compiled_with_cuda():
        raise RuntimeError("Paddle is CPU-only; refusing to continue.")
    paddle.set_device("gpu:0")
    return {
        "compiled_with_cuda": bool(paddle.device.is_compiled_with_cuda()),
        "device": paddle.device.get_device(),
        "paddle_version": getattr(paddle, "__version__", None),
    }


def read_manifest(path: Path, input_dir: Path | None, limit: int | None) -> list[dict[str, Any]]:
    if path.exists():
        rows = json.loads(path.read_text(encoding="utf-8"))
    elif input_dir is not None:
        rows = []
        for p in sorted(input_dir.glob("*")):
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
                rows.append({"image_id": p.stem, "image_path": str(p)})
    else:
        raise FileNotFoundError(f"No manifest found: {path}")
    if limit is not None:
        rows = rows[:limit]
    return rows


def normalize_result_json(res: Any) -> dict[str, Any]:
    data = getattr(res, "json", None)
    if callable(data):
        data = data()
    if isinstance(data, dict):
        if isinstance(data.get("res"), dict):
            return data["res"]
        return data
    raise TypeError(f"Result JSON is not a dict: {type(data)!r}")


def save_raw_result(res: Any, raw_dir: Path, image_id: str) -> tuple[Path, dict[str, Any]]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    before = {p.resolve() for p in raw_dir.glob("*.json")}
    try:
        res.save_to_json(save_path=str(raw_dir))
    except Exception:
        # Manual serialization below preserves the failure context in the caller if needed.
        pass
    after = [p for p in raw_dir.glob("*.json") if p.resolve() not in before]
    expected = raw_dir / f"{image_id}_res.json"
    if expected.exists():
        return expected, json.loads(expected.read_text(encoding="utf-8"))
    if after:
        data = json.loads(after[0].read_text(encoding="utf-8"))
        return after[0], data
    normalized = normalize_result_json(res)
    write_json(expected, normalized)
    return expected, normalized


def cell_text(node: etree._Element) -> str:
    return " ".join(" ".join(node.itertext()).split())


def parse_table_html(table_html: str) -> dict[str, Any]:
    warnings: list[str] = []
    has_merged = False
    try:
        doc = html.fromstring(table_html)
    except Exception as exc:
        return {
            "n_rows": 0,
            "n_cols": 0,
            "cell_texts": [],
            "has_merged_cells": False,
            "warnings": [f"html_parse_failure: {type(exc).__name__}: {exc}"],
            "html_parse_failed": True,
            "non_rectangular": False,
            "empty_cell_ratio": None,
        }
    table = doc if getattr(doc, "tag", "").lower() == "table" else doc.find(".//table")
    if table is None:
        return {
            "n_rows": 0,
            "n_cols": 0,
            "cell_texts": [],
            "has_merged_cells": False,
            "warnings": ["html_parse_failure: no <table> element found"],
            "html_parse_failed": True,
            "non_rectangular": False,
            "empty_cell_ratio": None,
        }

    grid: list[list[str | None]] = []
    occupied: dict[tuple[int, int], str] = {}
    rows = table.xpath(".//tr")
    for r, tr in enumerate(rows):
        row: list[str | None] = []
        c = 0
        for cell in tr.xpath("./th|./td"):
            while (r, c) in occupied:
                row.append(occupied[(r, c)])
                c += 1
            try:
                rowspan = max(1, int(cell.get("rowspan", "1") or "1"))
                colspan = max(1, int(cell.get("colspan", "1") or "1"))
            except ValueError:
                warnings.append("invalid_rowspan_or_colspan")
                rowspan, colspan = 1, 1
            if rowspan > 1 or colspan > 1:
                has_merged = True
            text = cell_text(cell)
            for dc in range(colspan):
                row.append(text)
                for dr in range(1, rowspan):
                    occupied[(r + dr, c + dc)] = text
            c += colspan
        while (r, c) in occupied:
            row.append(occupied[(r, c)])
            c += 1
        grid.append(row)

    # Rowspans can extend below the last explicit <tr>.
    extra_rows = [rr for rr, _ in occupied if rr >= len(grid)]
    for r in range(len(grid), max(extra_rows) + 1 if extra_rows else len(grid)):
        row = []
        c = 0
        while (r, c) in occupied:
            row.append(occupied[(r, c)])
            c += 1
        grid.append(row)

    widths = [len(row) for row in grid]
    n_cols = max(widths, default=0)
    non_rect = len(set(widths)) > 1 if widths else False
    if non_rect:
        warnings.append(f"non_rectangular_grid: row_widths={widths}")
        for row in grid:
            row.extend([""] * (n_cols - len(row)))
    cell_texts = [[cell or "" for cell in row] for row in grid]
    total = sum(len(row) for row in cell_texts)
    empty = sum(1 for row in cell_texts for cell in row if not cell)
    return {
        "n_rows": len(cell_texts),
        "n_cols": n_cols,
        "cell_texts": cell_texts,
        "has_merged_cells": has_merged,
        "warnings": warnings,
        "html_parse_failed": False,
        "non_rectangular": non_rect,
        "empty_cell_ratio": empty / total if total else None,
    }


def extract_table_blocks(raw: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = raw.get("parsing_res_list")
    if blocks is None and isinstance(raw.get("res"), dict):
        blocks = raw["res"].get("parsing_res_list")
    if not isinstance(blocks, list):
        return []
    tables = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if str(block.get("block_label", "")).lower() == "table":
            tables.append(block)
    return tables


def load_aihub_label_boxes(label_path: str | None) -> list[list[int]]:
    if not label_path:
        return []
    p = Path(label_path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    boxes = []
    for item in data.get("annotations", []):
        ann = item.get("annotation", item) if isinstance(item, dict) else {}
        bbox = ann.get("annotation.bbox") or ann.get("bbox")
        if isinstance(bbox, list) and len(bbox) == 4:
            x, y, w, h = bbox
            boxes.append([int(x), int(y), int(x + w), int(y + h)])
    return boxes


def bbox_sanity(bbox: list[Any], width: int, height: int, label_boxes: list[list[int]]) -> dict[str, Any]:
    warnings: list[str] = []
    if not isinstance(bbox, list) or len(bbox) != 4:
        return {"in_bounds": False, "warnings": ["invalid_bbox"], "ocr_label_centers_inside": 0}
    x1, y1, x2, y2 = [float(v) for v in bbox]
    in_bounds = x1 >= 0 and y1 >= 0 and x2 <= width and y2 <= height and x2 > x1 and y2 > y1
    if not in_bounds:
        warnings.append("bbox_out_of_image_bounds")
    centers_inside = 0
    for bx1, by1, bx2, by2 in label_boxes:
        cx = (bx1 + bx2) / 2
        cy = (by1 + by2) / 2
        if x1 <= cx <= x2 and y1 <= cy <= y2:
            centers_inside += 1
    if label_boxes and centers_inside == 0:
        warnings.append("no_aihub_ocr_label_centers_inside_table_bbox")
    return {"in_bounds": in_bounds, "warnings": warnings, "ocr_label_centers_inside": centers_inside}


def draw_overlay(image_path: Path, table_records: list[dict[str, Any]], label_boxes: list[list[int]], out_path: Path) -> None:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    for bx in label_boxes:
        draw.rectangle(bx, outline=(40, 120, 255, 90), width=1)
    for rec in table_records:
        bbox = rec.get("bbox")
        if isinstance(bbox, list) and len(bbox) == 4:
            box = [int(float(v)) for v in bbox]
            draw.rectangle(box, outline=(255, 40, 40, 255), width=5)
            draw.rectangle([box[0], max(0, box[1] - 24), box[0] + 170, box[1]], fill=(255, 40, 40, 180))
            draw.text((box[0] + 4, max(0, box[1] - 21)), f"table {rec.get('table_index')}", fill=(255, 255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path)


def build_pipeline(args: argparse.Namespace) -> Any:
    from paddleocr import PaddleOCRVL

    return PaddleOCRVL(
        pipeline_version="v1.6",
        vl_rec_model_name=MODEL_NAME,
        vl_rec_backend="vllm-server",
        vl_rec_server_url=args.server_url,
        vl_rec_api_model_name=MODEL_NAME,
        vl_rec_max_concurrency=args.vl_rec_max_concurrency,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_layout_detection=True,
        use_chart_recognition=False,
        use_seal_recognition=False,
        use_ocr_for_image_block=False,
        format_block_content=True,
        merge_layout_blocks=True,
        use_queues=False,
        device="gpu:0",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=TITLE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--input-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--output-jsonl", type=Path, default=None)
    parser.add_argument("--failed-log", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--server-url", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--vl-rec-max-concurrency", type=int, default=16)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_jsonl = args.output_jsonl or args.output_dir / "table_metadata.jsonl"
    failed_log = args.failed_log or args.output_dir / "failed.jsonl"
    image_summary_jsonl = args.output_dir / "image_summary.jsonl"
    raw_dir = args.output_dir / "raw"
    overlay_dir = args.output_dir / "overlays"

    paddle_info = verify_paddle_cuda()
    rows = read_manifest(args.manifest, args.input_dir, args.limit)
    completed = load_completed_image_ids(output_jsonl) if args.resume else set()
    stats = RunStats(images_seen=len(rows))
    empty_ratios: list[float] = []
    started = time.time()

    sampler = GpuSampler(interval_seconds=1.0)
    sampler.start()
    startup0 = time.time()
    pipeline = build_pipeline(args)
    stats.startup_seconds = time.time() - startup0

    run_manifest = {
        "title": TITLE,
        "created_at_kst": iso_kst(kst_now()),
        "command": " ".join(sys.argv),
        "paddle": paddle_info,
        "pipeline": {
            "class": "PaddleOCRVL",
            "pipeline_version": "v1.6",
            "vl_rec_backend": "vllm-server",
            "vl_rec_server_url": args.server_url,
            "vl_rec_api_model_name": MODEL_NAME,
            "vl_rec_max_concurrency": args.vl_rec_max_concurrency,
            "use_layout_detection": True,
            "device": "gpu:0",
        },
        "input_manifest": str(args.manifest),
        "output_jsonl": str(output_jsonl),
        "failed_log": str(failed_log),
        "limit": args.limit,
        "resume": args.resume,
        "startup_seconds": stats.startup_seconds,
    }
    write_json(args.output_dir / "run_manifest.json", run_manifest)

    try:
        for idx, row in enumerate(rows, 1):
            image_path = Path(row["image_path"])
            image_id = str(row.get("image_id") or image_path.stem)
            category = row.get("category")
            if args.resume and image_id in completed:
                stats.images_skipped += 1
                continue
            image_started = time.time()
            try:
                with Image.open(image_path) as im:
                    width, height = im.size
                label_boxes = load_aihub_label_boxes(row.get("label_path"))
                results = list(pipeline.predict(str(image_path)))
                infer_seconds = time.time() - image_started
                stats.inference_seconds_total += infer_seconds
                image_table_records: list[dict[str, Any]] = []
                raw_paths: list[str] = []
                for res in results:
                    raw_path, raw = save_raw_result(res, raw_dir, image_id)
                    raw_paths.append(str(raw_path))
                    for table_idx, block in enumerate(extract_table_blocks(raw)):
                        table_html = str(block.get("block_content") or "")
                        parsed = parse_table_html(table_html)
                        warnings = list(parsed["warnings"])
                        bbox = block.get("block_bbox")
                        sanity = bbox_sanity(bbox, width, height, label_boxes)
                        warnings.extend(sanity["warnings"])
                        rec = {
                            "image_id": image_id,
                            "category": category,
                            "table_index": table_idx,
                            "bbox": bbox,
                            "table_html": table_html,
                            "n_rows": parsed["n_rows"],
                            "n_cols": parsed["n_cols"],
                            "has_merged_cells": parsed["has_merged_cells"],
                            "cell_texts": parsed["cell_texts"],
                            "warnings": warnings,
                            "raw_json_path": str(raw_path),
                            "source_image_path": str(image_path),
                            "bbox_validation": sanity,
                            "empty_cell_ratio": parsed["empty_cell_ratio"],
                        }
                        append_jsonl(output_jsonl, rec)
                        image_table_records.append(rec)
                        stats.tables_found += 1
                        if parsed["html_parse_failed"]:
                            stats.html_parse_failures += 1
                        if parsed["non_rectangular"]:
                            stats.non_rectangular_grids += 1
                        if parsed["empty_cell_ratio"] is not None:
                            empty_ratios.append(float(parsed["empty_cell_ratio"]))
                overlay_path = overlay_dir / f"{image_id}_tables_overlay.jpg"
                draw_overlay(image_path, image_table_records, label_boxes, overlay_path)
                stats.images_processed += 1
                append_jsonl(
                    image_summary_jsonl,
                    {
                        "image_id": image_id,
                        "category": category,
                        "image_path": str(image_path),
                        "raw_json_paths": raw_paths,
                        "overlay_path": str(overlay_path),
                        "tables_found": len(image_table_records),
                        "inference_seconds": infer_seconds,
                        "width": width,
                        "height": height,
                    },
                )
                elapsed = time.time() - started
                done = stats.images_processed + stats.images_failed + stats.images_skipped
                rate = done / elapsed if elapsed > 0 else 0
                eta = kst_now() + timedelta(seconds=(len(rows) - done) / rate) if rate > 0 else None
                pct = done * 100 / len(rows) if rows else 100.0
                print(
                    f"{TITLE}. progress={pct:.1f}% done={done}/{len(rows)} image={image_id} "
                    f"tables={len(image_table_records)} infer_s={infer_seconds:.2f} eta_finish_kst={iso_kst(eta) if eta else 'unknown'}",
                    flush=True,
                )
            except Exception as exc:
                stats.images_failed += 1
                append_jsonl(
                    failed_log,
                    {
                        "image_id": image_id,
                        "image_path": str(image_path),
                        "category": category,
                        "error": repr(exc),
                        "traceback": traceback.format_exc(),
                    },
                )
                print(f"{TITLE}. image_failed={image_id} error={type(exc).__name__}: {exc}", flush=True)
    finally:
        sampler.stop()

    ratios = empty_ratios
    report = {
        "title": TITLE,
        "finished_at_kst": iso_kst(kst_now()),
        "images_seen": stats.images_seen,
        "images_processed": stats.images_processed,
        "images_skipped": stats.images_skipped,
        "images_failed": stats.images_failed,
        "tables_found": stats.tables_found,
        "html_parse_failures": stats.html_parse_failures,
        "non_rectangular_grids": stats.non_rectangular_grids,
        "empty_cell_ratio_stats": {
            "count": len(ratios),
            "min": min(ratios) if ratios else None,
            "max": max(ratios) if ratios else None,
            "mean": mean(ratios) if ratios else None,
        },
        "startup_seconds": stats.startup_seconds,
        "inference_seconds_total": stats.inference_seconds_total,
        "gpu_sampling": sampler.summary(),
        "outputs": {
            "table_metadata_jsonl": str(output_jsonl),
            "image_summary_jsonl": str(image_summary_jsonl),
            "failed_log": str(failed_log),
            "raw_dir": str(raw_dir),
            "overlay_dir": str(overlay_dir),
        },
    }
    write_json(args.output_dir / "validation_report.json", report)
    write_json(args.output_dir / "gpu_samples.json", sampler.samples)
    print(f"{TITLE}. completed report={args.output_dir / 'validation_report.json'}", flush=True)


if __name__ == "__main__":
    main()
