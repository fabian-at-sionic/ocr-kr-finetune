#!/usr/bin/env python3
"""Extract PP-StructureV3 table metadata for the 26-image teacher comparison."""

from __future__ import annotations

import argparse
import inspect
import json
import re
import time
import traceback
from dataclasses import dataclass
from html.parser import HTMLParser
from importlib import metadata
from pathlib import Path
from typing import Any

from PIL import Image

REC_MODEL_NAME = "korean_PP-OCRv5_mobile_rec"
DEFAULT_ROOT = Path("benchmark_work/paddleocrvl_table_metadata_aihub12")
DEFAULT_TRAIN26 = Path("data/train_26.jsonl")
DEFAULT_OUT = DEFAULT_ROOT / "ppstructurev3_table_structure"

SCHEMA_COMMENT = (
    "# schema: one JSON object per detected table. Fields: image_id, category, image_path, "
    "original_label_path, original_bbox_json, table_metadata. For images with no detected tables, "
    "table_metadata is null. Otherwise table_metadata contains bbox xyxy, table_html/structure_html, "
    "cells[{row,col,rowspan,colspan,bbox,text,ocr_text,ocr_items}], "
    "detection_score when available, raw_json_path, source_image_path, warnings."
)


@dataclass
class Cell:
    row: int
    col: int
    rowspan: int
    colspan: int
    text: str


class TableHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_row = False
        self.in_cell = False
        self.rows: list[list[dict[str, Any]]] = []
        self.current_row: list[dict[str, Any]] = []
        self.current_cell: dict[str, Any] | None = None
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "tr":
            self.in_row = True
            self.current_row = []
        elif tag in {"td", "th"} and self.in_row:
            attr = {k.lower(): v for k, v in attrs}
            self.in_cell = True
            self.text_parts = []
            self.current_cell = {
                "rowspan": max(1, int(attr.get("rowspan") or 1)),
                "colspan": max(1, int(attr.get("colspan") or 1)),
            }

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self.in_cell and self.current_cell is not None:
            self.current_cell["text"] = clean_text("".join(self.text_parts))
            self.current_row.append(self.current_cell)
            self.current_cell = None
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            self.rows.append(self.current_row)
            self.current_row = []
            self.in_row = False

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.text_parts.append(data)


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", encoding="utf-8") as f:
        if new_file:
            f.write(SCHEMA_COMMENT + "\n")
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str) + "\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                rows.append(json.loads(line))
    return rows


def package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def verify_paddle() -> dict[str, Any]:
    gpu_version = package_version("paddlepaddle-gpu")
    cpu_version = package_version("paddlepaddle")
    if cpu_version:
        raise RuntimeError("CPU package 'paddlepaddle' is installed. Refusing to run PPV3 extraction.")
    if not gpu_version:
        raise RuntimeError("GPU package 'paddlepaddle-gpu' is not installed.")
    import paddle

    if not paddle.is_compiled_with_cuda():
        raise RuntimeError("paddlepaddle-gpu is installed but is not compiled with CUDA")
    return {
        "paddlepaddle_gpu": gpu_version,
        "paddlepaddle_cpu": cpu_version,
        "paddle_version": getattr(paddle, "__version__", None),
        "paddleocr": package_version("paddleocr"),
        "paddlex": package_version("paddlex"),
        "compiled_with_cuda": True,
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
    if not any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()):
        kwargs = {key: value for key, value in kwargs.items() if key in signature.parameters}
    return PPStructureV3(**kwargs)


def normalize_result_json(res: Any) -> dict[str, Any]:
    data = getattr(res, "json", None)
    if callable(data):
        data = data()
    if isinstance(data, dict):
        return data.get("res", data) if isinstance(data.get("res", data), dict) else data
    raise TypeError(f"Result JSON is not a dict: {type(data)!r}")


def save_raw_result(res: Any, raw_dir: Path, image_id: str) -> tuple[Path, dict[str, Any]]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    expected = raw_dir / f"{image_id}_res.json"
    try:
        res.save_to_json(save_path=str(raw_dir))
    except Exception:
        pass
    if expected.exists():
        return expected, json.loads(expected.read_text(encoding="utf-8"))
    raw = normalize_result_json(res)
    write_json(expected, raw)
    return expected, raw


def parse_html_cells(table_html: str) -> tuple[list[Cell], int, int, list[str]]:
    parser = TableHTMLParser()
    warnings: list[str] = []
    try:
        parser.feed(table_html or "")
    except Exception as exc:
        return [], 0, 0, [f"html_parse_failure:{type(exc).__name__}:{exc}"]
    occupied: dict[tuple[int, int], int] = {}
    cells: list[Cell] = []
    row_count = 0
    for r, row in enumerate(parser.rows):
        row_count = max(row_count, r + 1)
        c = 0
        while (r, c) in occupied:
            c += 1
        for raw in row:
            while (r, c) in occupied:
                c += 1
            rowspan = int(raw.get("rowspan") or 1)
            colspan = int(raw.get("colspan") or 1)
            cell = Cell(r, c, rowspan, colspan, clean_text(raw.get("text")))
            idx = len(cells)
            cells.append(cell)
            for rr in range(r, r + rowspan):
                row_count = max(row_count, rr + 1)
                for cc in range(c, c + colspan):
                    occupied[(rr, cc)] = idx
            c += colspan
    n_cols = max((c for _, c in occupied), default=-1) + 1
    if not cells:
        warnings.append("empty_table_grid")
    return cells, row_count, n_cols, warnings


def center(box: list[float]) -> tuple[float, float]:
    return (float(box[0]) + float(box[2])) / 2.0, (float(box[1]) + float(box[3])) / 2.0


def point_in_box(pt: tuple[float, float], box: list[float]) -> bool:
    return float(box[0]) <= pt[0] <= float(box[2]) and float(box[1]) <= pt[1] <= float(box[3])


def iou(a: list[float], b: list[float]) -> float:
    ax0, ay0, ax1, ay1 = map(float, a)
    bx0, by0, bx1, by1 = map(float, b)
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    return inter / (area_a + area_b - inter) if area_a + area_b > inter else 0.0


def table_blocks(raw: dict[str, Any]) -> list[dict[str, Any]]:
    return [b for b in raw.get("parsing_res_list") or [] if isinstance(b, dict) and str(b.get("block_label", "")).lower() == "table"]


def layout_score_for(raw: dict[str, Any], bbox: list[float]) -> float | None:
    boxes = ((raw.get("layout_det_res") or {}).get("boxes") or [])
    candidates = []
    for box in boxes:
        if str(box.get("label", "")).lower() == "table" and isinstance(box.get("coordinate"), list):
            candidates.append((iou(bbox, box["coordinate"]), box.get("score")))
    if not candidates:
        return None
    _, score = max(candidates, key=lambda item: item[0])
    return float(score) if score is not None else None


def assign_ocr_to_cells(cell_records: list[dict[str, Any]], table_res: dict[str, Any]) -> None:
    pred = table_res.get("table_ocr_pred") or {}
    texts = pred.get("rec_texts") or []
    scores = pred.get("rec_scores") or []
    boxes = pred.get("rec_boxes") or []
    grouped: dict[int, list[dict[str, Any]]] = {i: [] for i in range(len(cell_records))}
    for idx, (text, box) in enumerate(zip(texts, boxes)):
        if not isinstance(box, list) or len(box) != 4:
            continue
        candidates = [(ci, iou(box, cell["bbox"])) for ci, cell in enumerate(cell_records) if point_in_box(center(box), cell["bbox"])]
        if not candidates:
            candidates = [(ci, iou(box, cell["bbox"])) for ci, cell in enumerate(cell_records) if iou(box, cell["bbox"]) > 0]
        if candidates:
            ci = max(candidates, key=lambda item: (item[1], -cell_records[item[0]]["row"], -cell_records[item[0]]["col"]))[0]
            grouped[ci].append({"text": clean_text(text), "bbox": box, "score": scores[idx] if idx < len(scores) else None})
    for ci, items in grouped.items():
        items.sort(key=lambda item: (item["bbox"][1], item["bbox"][0], item["text"]))
        cell_records[ci]["ocr_items"] = items
        cell_records[ci]["ocr_text"] = clean_text(" ".join(item["text"] for item in items))
        vals = [item["score"] for item in items if isinstance(item.get("score"), (int, float))]
        cell_records[ci]["ocr_score_mean"] = sum(vals) / len(vals) if vals else None


def table_record_from_raw(raw: dict[str, Any], block: dict[str, Any], table_res: dict[str, Any], table_index: int, raw_path: Path, image_id: str, category: str | None, image_path: Path) -> dict[str, Any]:
    bbox = [float(v) for v in (block.get("block_bbox") or [])]
    html = str(table_res.get("pred_html") or block.get("block_content") or "")
    html_cells, n_rows, n_cols, warnings = parse_html_cells(html)
    cell_boxes = table_res.get("cell_box_list") or []
    if len(cell_boxes) != len(html_cells):
        warnings.append(f"cell_box_count_mismatch:html={len(html_cells)} boxes={len(cell_boxes)}")
    cell_records = []
    for idx, cell in enumerate(html_cells):
        if idx < len(cell_boxes) and isinstance(cell_boxes[idx], list) and len(cell_boxes[idx]) == 4:
            cb = [float(v) for v in cell_boxes[idx]]
        else:
            x0, y0, x1, y1 = bbox
            col_w = (x1 - x0) / max(1, n_cols)
            row_h = (y1 - y0) / max(1, n_rows)
            cb = [x0 + cell.col * col_w, y0 + cell.row * row_h, x0 + (cell.col + cell.colspan) * col_w, y0 + (cell.row + cell.rowspan) * row_h]
        cell_records.append({"row": cell.row, "col": cell.col, "rowspan": cell.rowspan, "colspan": cell.colspan, "bbox": cb, "text": cell.text})
    assign_ocr_to_cells(cell_records, table_res)
    return {
        "image_id": image_id,
        "category": category,
        "table_index": table_index,
        "bbox": bbox,
        "table_html": html,
        "structure_html": html,
        "n_rows": n_rows,
        "n_cols": n_cols,
        "cells": cell_records,
        "cell_texts": [[c["text"] for c in cell_records if c["row"] == r] for r in range(n_rows)],
        "detection_score": layout_score_for(raw, bbox),
        "structure_score": None,
        "warnings": warnings,
        "raw_json_path": str(raw_path),
        "source_image_path": str(image_path),
    }


def manifest_from_train26(train26: Path) -> list[dict[str, Any]]:
    return [{"image_id": r["image_id"], "image_path": r["image_path"], "category": r.get("category")} for r in load_jsonl(train26)]


def attach_labels(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {}
    for manifest_path in [DEFAULT_ROOT / "additional_table_search/input/additional_candidates_manifest.json", DEFAULT_ROOT / "input/aihub12_manifest.json"]:
        if manifest_path.exists():
            for rec in json.loads(manifest_path.read_text(encoding="utf-8")):
                by_id[rec["image_id"]] = rec
    out = []
    for row in rows:
        merged = dict(by_id.get(row["image_id"], {}))
        merged.update(row)
        if "label_path" not in merged:
            guess = Path(str(merged["image_path"]).replace("/images/", "/labels/")).with_suffix(".json")
            merged["label_path"] = str(guess)
        out.append(merged)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, default=None)
    ap.add_argument("--from-train26", type=Path, default=DEFAULT_TRAIN26)
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--output-jsonl", type=Path, default=None)
    ap.add_argument("--rec-model-dir", type=Path, default=Path("model/PaddlePaddle/korean_PP-OCRv5_mobile_rec"))
    ap.add_argument("--device", default="gpu:0")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_jsonl = args.output_jsonl or args.output_dir / "table_metadata.jsonl"
    raw_dir = args.output_dir / "raw_ppv3"
    failed_jsonl = args.output_dir / "failed.jsonl"
    summary_jsonl = args.output_dir / "image_summary.jsonl"

    rows = json.loads(args.manifest.read_text(encoding="utf-8")) if args.manifest else manifest_from_train26(args.from_train26)
    rows = attach_labels(rows)
    if args.limit is not None:
        rows = rows[: args.limit]
    done = set()
    if args.resume and output_jsonl.exists():
        done = {r["image_id"] for r in load_jsonl(output_jsonl)}

    runtime = verify_paddle()
    pipeline = build_pipeline(args.rec_model_dir, args.device)
    write_json(args.output_dir / "run_manifest.json", {"runtime": runtime, "rows": len(rows), "output_jsonl": str(output_jsonl), "raw_dir": str(raw_dir)})

    totals = {"images": len(rows), "processed": 0, "skipped": 0, "failed": 0, "tables": 0}
    for row in rows:
        image_path = Path(row["image_path"])
        image_id = str(row.get("image_id") or image_path.stem)
        if image_id in done:
            totals["skipped"] += 1
            continue
        started = time.time()
        try:
            with Image.open(image_path) as im:
                width, height = im.size
            results = list(pipeline.predict(str(image_path)))
            image_tables = []
            raw_paths = []
            for res in results:
                raw_path, raw = save_raw_result(res, raw_dir, image_id)
                raw_paths.append(str(raw_path))
                blocks = table_blocks(raw)
                table_res_list = raw.get("table_res_list") or []
                for table_index, block in enumerate(blocks):
                    table_res = table_res_list[table_index] if table_index < len(table_res_list) else {}
                    tm = table_record_from_raw(raw, block, table_res, table_index, raw_path, image_id, row.get("category"), image_path)
                    record = {
                        "image_id": image_id,
                        "category": row.get("category"),
                        "image_path": str(image_path),
                        "original_label_path": row.get("label_path"),
                        "original_bbox_json": json.loads(Path(row["label_path"]).read_text(encoding="utf-8")),
                        "table_metadata": tm,
                    }
                    append_jsonl(output_jsonl, record)
                    image_tables.append(tm)
            if not image_tables:
                append_jsonl(
                    output_jsonl,
                    {
                        "image_id": image_id,
                        "category": row.get("category"),
                        "image_path": str(image_path),
                        "original_label_path": row.get("label_path"),
                        "original_bbox_json": json.loads(Path(row["label_path"]).read_text(encoding="utf-8")),
                        "table_metadata": None,
                    },
                )
            totals["processed"] += 1
            totals["tables"] += len(image_tables)
            append_jsonl(summary_jsonl, {"image_id": image_id, "image_path": str(image_path), "width": width, "height": height, "tables_found": len(image_tables), "raw_json_paths": raw_paths, "seconds": round(time.time() - started, 3)})
            print(json.dumps({"image_id": image_id, "tables": len(image_tables), "seconds": round(time.time() - started, 3)}, ensure_ascii=False), flush=True)
        except Exception as exc:
            totals["failed"] += 1
            append_jsonl(failed_jsonl, {"image_id": image_id, "image_path": str(image_path), "error": repr(exc), "traceback": traceback.format_exc()})
            print(f"PPV3 extraction failed {image_id}: {exc!r}", flush=True)
    write_json(args.output_dir / "validation_report.json", totals)
    return 0 if totals["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
