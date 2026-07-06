#!/usr/bin/env python3
"""Render AIHub text/table overlay review artifacts for DocTags training samples."""

from __future__ import annotations

import argparse
import html
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from lxml import html as lxml_html
from PIL import Image, ImageDraw, ImageFont


DEFAULT_TRAIN = Path("data/train_12.jsonl")
DEFAULT_JOINED = Path("benchmark_work/paddleocrvl_table_metadata_aihub12/training_joined_table_and_original_bbox.jsonl")
DEFAULT_REVIEW = Path("review")

GREEN = (0, 180, 0)
ORANGE = (255, 150, 0)
RED = (230, 20, 20)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def xywh_to_xyxy(bbox: list[float]) -> tuple[float, float, float, float]:
    x, y, w, h = bbox
    return float(x), float(y), float(x) + float(w), float(y) + float(h)


def center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    x0, y0, x1, y1 = bbox
    return (x0 + x1) / 2.0, (y0 + y1) / 2.0


def point_in_bbox(pt: tuple[float, float], bbox: tuple[float, float, float, float]) -> bool:
    x, y = pt
    x0, y0, x1, y1 = bbox
    return x0 <= x <= x1 and y0 <= y <= y1


def bbox_iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    denom = area_a + area_b - inter
    return inter / denom if denom else 0.0


def parse_aihub_texts(label_json: dict[str, Any]) -> list[dict[str, Any]]:
    texts = []
    for ann in label_json.get("annotations") or []:
        text = clean_text(ann.get("annotation.text"))
        bbox = ann.get("annotation.bbox")
        if not text or not bbox or len(bbox) != 4:
            continue
        texts.append({"id": str(ann.get("id")), "text": text, "bbox": xywh_to_xyxy(bbox)})
    texts.sort(key=lambda r: (r["bbox"][1], r["bbox"][0], r["id"]))
    return texts


def parse_cells(table_html: str, table_bbox: tuple[float, float, float, float]) -> tuple[list[dict[str, Any]], list[str], int, int]:
    warnings: list[str] = []
    try:
        doc = lxml_html.fromstring(table_html)
        table = doc if doc.tag.lower() == "table" else doc.find(".//table")
    except Exception as exc:
        return [], [f"html_parse_failure:{exc}"], 0, 0
    if table is None:
        return [], ["html_parse_failure:no_table"], 0, 0

    occupied: dict[tuple[int, int], int] = {}
    cells: list[dict[str, Any]] = []
    row_count = 0
    for r, tr in enumerate(table.xpath(".//tr")):
        row_count = max(row_count, r + 1)
        c = 0
        while (r, c) in occupied:
            c += 1
        for td in tr.xpath("./th|./td"):
            while (r, c) in occupied:
                c += 1
            rowspan = int(td.get("rowspan") or 1)
            colspan = int(td.get("colspan") or 1)
            text = clean_text(" ".join(td.itertext()))
            idx = len(cells)
            cells.append({"row": r, "col": c, "rowspan": rowspan, "colspan": colspan, "text": text})
            for rr in range(r, r + rowspan):
                row_count = max(row_count, rr + 1)
                for cc in range(c, c + colspan):
                    occupied[(rr, cc)] = idx
            c += colspan
    n_cols = max((c for _, c in occupied.keys()), default=-1) + 1
    if row_count == 0 or n_cols == 0:
        warnings.append("empty_table_grid")
        return cells, warnings, row_count, n_cols

    x0, y0, x1, y1 = table_bbox
    col_w = (x1 - x0) / n_cols
    row_h = (y1 - y0) / row_count
    for cell in cells:
        cell["bbox"] = (
            x0 + cell["col"] * col_w,
            y0 + cell["row"] * row_h,
            x0 + (cell["col"] + cell["colspan"]) * col_w,
            y0 + (cell["row"] + cell["rowspan"]) * row_h,
        )
    return cells, warnings, row_count, n_cols


def compute_review_stats(texts: list[dict[str, Any]], tables: list[dict[str, Any]]) -> dict[str, Any]:
    table_bboxes = [tuple(map(float, table["bbox"])) for table in tables]
    consumed_by: dict[str, int] = {}
    for tb in texts:
        containing = [idx for idx, box in enumerate(table_bboxes) if point_in_bbox(center(tb["bbox"]), box)]
        if containing:
            consumed_by[tb["id"]] = min(containing, key=lambda i: (table_bboxes[i][1], table_bboxes[i][0], i))

    table_stats = []
    total_matched = 0
    warning_counts: defaultdict[str, int] = defaultdict(int)
    for idx, table in enumerate(tables):
        table_bbox = table_bboxes[idx]
        cells, parse_warnings, n_rows, n_cols = parse_cells(table.get("table_html", ""), table_bbox)
        consumed = [tb for tb in texts if consumed_by.get(tb["id"]) == idx]
        matched_ids: set[str] = set()
        matched_cells: set[int] = set()
        unplaced = []
        for tb in consumed:
            candidates = [(ci, bbox_iou(tb["bbox"], cell.get("bbox", (0, 0, 0, 0)))) for ci, cell in enumerate(cells) if "bbox" in cell and point_in_bbox(center(tb["bbox"]), cell["bbox"])]
            if not candidates:
                candidates = [(ci, bbox_iou(tb["bbox"], cell.get("bbox", (0, 0, 0, 0)))) for ci, cell in enumerate(cells) if "bbox" in cell and bbox_iou(tb["bbox"], cell["bbox"]) > 0]
            if candidates:
                ci = max(candidates, key=lambda item: (item[1], -cells[item[0]]["row"], -cells[item[0]]["col"]))[0]
                matched_ids.add(tb["id"])
                matched_cells.add(ci)
            else:
                unplaced.append(tb)
        paddle_text_only = sum(1 for ci, cell in enumerate(cells) if ci not in matched_cells and cell.get("text"))
        warnings = list(table.get("warnings") or []) + parse_warnings
        if paddle_text_only:
            warnings.append("paddle_text_only")
        if unplaced:
            warnings.append("unplaced_in_table")
        for w in warnings:
            warning_counts[w] += 1
        total_matched += len(matched_cells)
        table_stats.append(
            {
                "table_index": table.get("table_index", idx),
                "bbox": list(map(int, table_bbox)),
                "n_rows": int(table.get("n_rows") or n_rows),
                "n_cols": int(table.get("n_cols") or n_cols),
                "consumed_texts": len(consumed),
                "matched_cells": len(matched_cells),
                "paddle_text_only": paddle_text_only,
                "unplaced": len(unplaced),
                "warnings": warnings,
                "table_html": table.get("table_html", ""),
            }
        )
    return {
        "consumed_ids": set(consumed_by.keys()),
        "consumed": len(consumed_by),
        "free": len(texts) - len(consumed_by),
        "matched": total_matched,
        "warnings": dict(sorted(warning_counts.items())),
        "tables": table_stats,
    }


def draw_rect(draw: ImageDraw.ImageDraw, bbox: tuple[float, float, float, float], color: tuple[int, int, int], width: int) -> None:
    box = tuple(round(v) for v in bbox)
    for inset in range(width):
        draw.rectangle((box[0]-inset, box[1]-inset, box[2]+inset, box[3]+inset), outline=color)


def draw_label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str) -> None:
    font = ImageFont.load_default()
    x, y = xy
    bbox = draw.textbbox((x, y), text, font=font)
    pad = 3
    bg = (bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad)
    draw.rectangle(bg, fill=RED)
    draw.text((x, y), text, fill=WHITE, font=font)


def render_overlay(image_path: Path, texts: list[dict[str, Any]], tables: list[dict[str, Any]], stats: dict[str, Any], output_path: Path) -> None:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    scale = max(image.size) / 2000.0
    thin = max(1, round(1 * scale))
    orange_w = max(2, round(2 * scale))
    thick = max(4, round(5 * scale))
    consumed_ids = stats["consumed_ids"]

    for tb in texts:
        draw_rect(draw, tb["bbox"], GREEN, thin)
    for tb in texts:
        if tb["id"] in consumed_ids:
            draw_rect(draw, tb["bbox"], ORANGE, orange_w)
    for table in tables:
        bbox = tuple(map(float, table["bbox"]))
        draw_rect(draw, bbox, RED, thick)
        label = f"{int(table.get('n_rows') or 0)} x {int(table.get('n_cols') or 0)}"
        draw_label(draw, (round(bbox[0]), max(0, round(bbox[1]) - 18)), label)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def safe_table_html(table_html: str) -> str:
    try:
        doc = lxml_html.fromstring(table_html)
        table = doc if doc.tag.lower() == "table" else doc.find(".//table")
        if table is None:
            return f"<pre>{html.escape(table_html)}</pre>"
        # Strip inline styles but preserve table structure and spans.
        for el in table.iter():
            for attr in ["style", "border", "class", "width", "height"]:
                el.attrib.pop(attr, None)
        return lxml_html.tostring(table, encoding="unicode")
    except Exception:
        return f"<pre>{html.escape(table_html)}</pre>"


def write_index(review_dir: Path, image_rows: list[dict[str, Any]]) -> None:
    css = """
    body { font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 24px; color: #151515; background: #f5f5f5; }
    h1 { margin-bottom: 4px; }
    .legend span { display: inline-block; margin-right: 18px; }
    .swatch { width: 14px; height: 14px; border: 2px solid; vertical-align: -2px; margin-right: 5px; background: white; }
    .green { border-color: #00b400; } .orange { border-color: #ff9600; } .red { border-color: #e61414; }
    section { background: white; border: 1px solid #cfcfcf; margin: 18px 0; padding: 16px; }
    .row { display: grid; grid-template-columns: minmax(360px, 52%) minmax(320px, 48%); gap: 18px; align-items: start; }
    .overlay img { width: 100%; height: auto; border: 1px solid #aaa; background: #fff; }
    .meta { font-size: 13px; line-height: 1.45; margin: 8px 0 12px; }
    .tables { overflow-x: auto; }
    table { border-collapse: collapse; margin: 0 0 14px; width: max-content; max-width: 100%; background: #fff; }
    th, td { border: 1px solid #777; padding: 4px 7px; font-size: 12px; vertical-align: top; white-space: pre-wrap; }
    .table-title { font-weight: 700; margin: 12px 0 6px; }
    code { background: #eee; padding: 1px 4px; }
    """
    sections = []
    for row in image_rows:
        table_blocks = []
        for t in row["stats"]["tables"]:
            warnings = ", ".join(t["warnings"]) if t["warnings"] else "none"
            table_blocks.append(
                f"<div class='table-title'>table {t['table_index']} · {t['n_rows']} x {t['n_cols']} · bbox {html.escape(str(t['bbox']))}</div>"
                f"<div class='meta'>consumed={t['consumed_texts']} · matched_cells={t['matched_cells']} · paddle_text_only={t['paddle_text_only']} · unplaced={t['unplaced']} · warnings={html.escape(warnings)}</div>"
                f"<div class='tables'>{safe_table_html(t['table_html'])}</div>"
            )
        warnings = ", ".join(f"{k}:{v}" for k, v in row["stats"]["warnings"].items()) or "none"
        sections.append(
            f"<section id='{html.escape(row['image_id'])}'>"
            f"<h2>{html.escape(row['image_id'])} · {html.escape(row['category'])}</h2>"
            f"<div class='meta'>AIHub text: {row['text_count']} · consumed/free: {row['stats']['consumed']} / {row['stats']['free']} · matched cells: {row['stats']['matched']} · warnings: {html.escape(warnings)}</div>"
            f"<div class='row'><div class='overlay'><a href='overlays/{html.escape(row['image_id'])}.png'><img src='overlays/{html.escape(row['image_id'])}.png' alt='overlay {html.escape(row['image_id'])}'></a></div>"
            f"<div>{''.join(table_blocks)}</div></div></section>"
        )
    html_doc = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>AIHub Table Overlay Review</title><style>{css}</style></head>
<body>
<h1>AIHub Table Overlay Review</h1>
<p>Generated from <code>data/train_12.jsonl</code> and joined Paddle/AIHub metadata. Click an overlay for full resolution.</p>
<p class='legend'><span><i class='swatch green'></i>AIHub text bbox</span><span><i class='swatch orange'></i>AIHub text consumed by table</span><span><i class='swatch red'></i>Paddle table bbox</span></p>
<p>Total images: {len(image_rows)}</p>
{''.join(sections)}
</body></html>"""
    (review_dir / "index.html").write_text(html_doc, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-jsonl", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--joined-jsonl", type=Path, default=DEFAULT_JOINED)
    parser.add_argument("--review-dir", type=Path, default=DEFAULT_REVIEW)
    args = parser.parse_args()

    train = load_jsonl(args.train_jsonl)
    joined = load_jsonl(args.joined_jsonl)
    joined_by_image: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in joined:
        joined_by_image[rec["image_id"]].append(rec)

    image_rows = []
    overlay_dir = args.review_dir / "overlays"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    for train_rec in sorted(train, key=lambda r: r["image_id"]):
        image_id = train_rec["image_id"]
        joined_rows = joined_by_image.get(image_id)
        if not joined_rows:
            raise KeyError(f"no joined metadata for {image_id}")
        original_bbox_json = joined_rows[0]["original_bbox_json"]
        texts = parse_aihub_texts(original_bbox_json)
        tables = [r["table_metadata"] for r in sorted(joined_rows, key=lambda r: int(r["table_metadata"].get("table_index", 0)))]
        stats = compute_review_stats(texts, tables)
        image_path = Path(train_rec["image_path"])
        if not image_path.exists():
            raise FileNotFoundError(image_path)
        render_overlay(image_path, texts, tables, stats, overlay_dir / f"{image_id}.png")
        image_rows.append(
            {
                "image_id": image_id,
                "category": train_rec.get("category", ""),
                "text_count": len(texts),
                "stats": stats,
            }
        )

    write_index(args.review_dir, image_rows)
    summary = {
        "images": len(image_rows),
        "tables": sum(len(row["stats"]["tables"]) for row in image_rows),
        "overlay_dir": str(overlay_dir),
        "index_html": str(args.review_dir / "index.html"),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
