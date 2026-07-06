#!/usr/bin/env python3
"""Render PPV3-vs-VL1.6 table teacher review artifacts."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.convert_tables_to_granite_docling_doctags import (
    assign_cell_bboxes,
    bbox_iou,
    center,
    clean_text,
    parse_aihub_texts,
    normalize_for_match,
    parse_table_html,
    point_in_bbox,
)

GREEN = (0, 180, 0)
ORANGE = (255, 150, 0)
RED = (230, 20, 20)
BLUE = (20, 90, 255)
WHITE = (255, 255, 255)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(json.loads(line))
    return out


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#"))


def group_by_image(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["image_id"]].append(row)
    return groups


def draw_rect(draw: ImageDraw.ImageDraw, bbox: tuple[float, float, float, float] | list[float], color: tuple[int, int, int], width: int) -> None:
    x0, y0, x1, y1 = [round(float(v)) for v in bbox]
    for inset in range(width):
        draw.rectangle((x0 - inset, y0 - inset, x1 + inset, y1 + inset), outline=color)


def draw_label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, color: tuple[int, int, int]) -> None:
    font = ImageFont.load_default()
    box = draw.textbbox(xy, text, font=font)
    pad = 3
    draw.rectangle((box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad), fill=color)
    draw.text(xy, text, fill=WHITE, font=font)


def cells_for_table(table: dict[str, Any], teacher: str) -> tuple[list[dict[str, Any]], int, int, list[str]]:
    bbox = tuple(map(float, table["bbox"]))
    warnings = list(table.get("warnings") or [])
    if teacher == "ppv3" and table.get("cells"):
        cells = []
        for cell in table["cells"]:
            cells.append(
                {
                    "row": int(cell.get("row", 0)),
                    "col": int(cell.get("col", 0)),
                    "rowspan": int(cell.get("rowspan", 1) or 1),
                    "colspan": int(cell.get("colspan", 1) or 1),
                    "text": clean_text(cell.get("ocr_text") or cell.get("text") or ""),
                    "bbox": tuple(map(float, cell.get("bbox") or bbox)),
                }
            )
        n_rows = int(table.get("n_rows") or max((c["row"] + c["rowspan"] for c in cells), default=0))
        n_cols = int(table.get("n_cols") or max((c["col"] + c["colspan"] for c in cells), default=0))
        return cells, n_rows, n_cols, warnings
    expanded, parsed_cells, parse_warnings = parse_table_html(table.get("table_html", ""))
    n_rows = len(expanded)
    n_cols = len(expanded[0]) if expanded else 0
    assign_cell_bboxes(parsed_cells, n_rows, n_cols, bbox)
    cells = [
        {
            "row": c.row,
            "col": c.col,
            "rowspan": c.rowspan,
            "colspan": c.colspan,
            "text": c.text,
            "bbox": c.bbox,
        }
        for c in parsed_cells
    ]
    return cells, n_rows, n_cols, warnings + parse_warnings


def text_grid(cells: list[dict[str, Any]], n_rows: int, n_cols: int) -> list[list[str]]:
    grid = [["" for _ in range(n_cols)] for _ in range(n_rows)]
    for cell in cells:
        if cell["row"] < n_rows and cell["col"] < n_cols:
            grid[cell["row"]][cell["col"]] = cell.get("text", "")
    return grid


def span_signature(cells: list[dict[str, Any]]) -> list[tuple[int, int, int, int]]:
    return sorted((c["row"], c["col"], c["rowspan"], c["colspan"]) for c in cells)


def match_report(texts: list[Any], table: dict[str, Any], cells: list[dict[str, Any]]) -> dict[str, Any]:
    bbox = tuple(map(float, table["bbox"]))
    consumed = [tb for tb in texts if point_in_bbox(center(tb.bbox), bbox)]
    cell_methods: dict[int, str] = {}
    unplaced = []
    for tb in consumed:
        candidates = [(idx, bbox_iou(tb.bbox, c["bbox"])) for idx, c in enumerate(cells) if point_in_bbox(center(tb.bbox), c["bbox"])]
        if not candidates:
            candidates = [(idx, bbox_iou(tb.bbox, c["bbox"])) for idx, c in enumerate(cells) if bbox_iou(tb.bbox, c["bbox"]) > 0]
        if candidates:
            idx = max(candidates, key=lambda item: (item[1], -cells[item[0]]["row"], -cells[item[0]]["col"]))[0]
            cell_methods[idx] = "geometry"
        else:
            unplaced.append(tb)

    remaining = {tb.source_id: tb for tb in unplaced}
    for idx, cell in enumerate(cells):
        if idx in cell_methods:
            continue
        wanted = normalize_for_match(cell.get("text", ""))
        if not wanted:
            continue
        matched = []
        for source_id, tb in sorted(remaining.items(), key=lambda item: (item[1].bbox[1], item[1].bbox[0], item[0])):
            got = normalize_for_match(tb.text)
            if got and (got in wanted or wanted in got):
                matched.append(source_id)
        if matched:
            for source_id in matched:
                remaining.pop(source_id, None)
            cell_methods[idx] = "text_fallback"

    counts = Counter(cell_methods.values())
    total = len(cells)
    unmatched_cells = max(0, total - len(cell_methods))
    return {
        "cells": total,
        "geometry_cells": counts.get("geometry", 0),
        "text_fallback_cells": counts.get("text_fallback", 0),
        "unmatched_cells": unmatched_cells,
        "consumed_texts": len(consumed),
        "unmatched_texts": len(remaining),
        "geometry_pct": round(100 * counts.get("geometry", 0) / total, 1) if total else 0.0,
        "text_fallback_pct": round(100 * counts.get("text_fallback", 0) / total, 1) if total else 0.0,
        "unmatched_pct": round(100 * unmatched_cells / total, 1) if total else 0.0,
    }


def render_overlay(image_path: Path, label_json: dict[str, Any], tables: list[dict[str, Any]], output: Path, teacher: str) -> None:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    width = max(1, round(max(image.size) / 900))
    _, _, texts = parse_aihub_texts(label_json)
    consumed = set()
    table_bboxes = [tuple(map(float, t["bbox"])) for t in tables]
    for tb in texts:
        if any(point_in_bbox(center(tb.bbox), box) for box in table_bboxes):
            consumed.add(tb.source_id)
    for tb in texts:
        draw_rect(draw, tb.bbox, ORANGE if tb.source_id in consumed else GREEN, max(1, width))
    for ti, table in enumerate(tables):
        draw_rect(draw, table["bbox"], RED, max(3, width * 3))
        draw_label(draw, (round(float(table["bbox"][0])), max(0, round(float(table["bbox"][1])) - 18)), f"{teacher} table {ti}", RED)
        cells, _, _, _ = cells_for_table(table, teacher)
        for cell in cells:
            draw_rect(draw, cell["bbox"], BLUE, max(1, width))
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def simple_table_html(table_html: str) -> str:
    return re.sub(r"<table", "<table border='1'", table_html, count=1) if table_html else "<p>(no table)</p>"


def write_image_md(path: Path, image_id: str, pp_tables: list[dict[str, Any]], vl_tables: list[dict[str, Any]], texts: list[Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {image_id}", ""]
    max_tables = max(len(pp_tables), len(vl_tables))
    warnings = Counter()
    for idx in range(max_tables):
        pp = pp_tables[idx] if idx < len(pp_tables) else None
        vl = vl_tables[idx] if idx < len(vl_tables) else None
        lines.extend([f"## Table {idx}", ""])
        if pp:
            pp_cells, pp_rows, pp_cols, pp_warn = cells_for_table(pp, "ppv3")
        else:
            pp_cells, pp_rows, pp_cols, pp_warn = [], 0, 0, ["missing_ppv3_table"]
        if vl:
            vl_cells, vl_rows, vl_cols, vl_warn = cells_for_table(vl, "vl16")
        else:
            vl_cells, vl_rows, vl_cols, vl_warn = [], 0, 0, ["missing_vl16_table"]
        warnings.update(pp_warn + vl_warn)
        pp_grid = text_grid(pp_cells, pp_rows, pp_cols)
        vl_grid = text_grid(vl_cells, vl_rows, vl_cols)
        text_diffs = []
        for r in range(max(pp_rows, vl_rows)):
            for c in range(max(pp_cols, vl_cols)):
                pv = pp_grid[r][c] if r < pp_rows and c < pp_cols else ""
                vv = vl_grid[r][c] if r < vl_rows and c < vl_cols else ""
                if clean_text(pv) != clean_text(vv):
                    text_diffs.append(f"r{r}c{c}: PPV3=`{pv}` VL1.6=`{vv}`")
        pp_report = match_report(texts, pp, pp_cells) if pp else {"cells": 0, "geometry_cells": 0, "text_fallback_cells": 0, "unmatched_cells": 0, "geometry_pct": 0, "text_fallback_pct": 0, "unmatched_pct": 0}
        vl_report = match_report(texts, vl, vl_cells) if vl else {"cells": 0, "geometry_cells": 0, "text_fallback_cells": 0, "unmatched_cells": 0, "geometry_pct": 0, "text_fallback_pct": 0, "unmatched_pct": 0}
        lines.extend(
            [
                f"- Rows/cols agree: {pp_rows}x{pp_cols} vs {vl_rows}x{vl_cols} -> {pp_rows == vl_rows and pp_cols == vl_cols}",
                f"- Spans agree: {span_signature(pp_cells) == span_signature(vl_cells)}",
                f"- Text differences: {len(text_diffs)}",
                f"- PPV3 match report: geometry {pp_report['geometry_cells']}/{pp_report['cells']} ({pp_report['geometry_pct']}%), text-fallback {pp_report['text_fallback_cells']} ({pp_report['text_fallback_pct']}%), unmatched {pp_report['unmatched_cells']} ({pp_report['unmatched_pct']}%)",
                f"- VL1.6 match report: geometry/current {vl_report['geometry_cells']}/{vl_report['cells']} ({vl_report['geometry_pct']}%), text-fallback {vl_report['text_fallback_cells']} ({vl_report['text_fallback_pct']}%), unmatched {vl_report['unmatched_cells']} ({vl_report['unmatched_pct']}%)",
                "",
                "<div style='display:flex;gap:24px;align-items:flex-start'>",
                "<div><h3>PP-StructureV3</h3>",
                simple_table_html(pp.get("table_html", "") if pp else ""),
                "</div><div><h3>PaddleOCR-VL-1.6</h3>",
                simple_table_html(vl.get("table_html", "") if vl else ""),
                "</div></div>",
                "",
            ]
        )
        if text_diffs:
            lines.append("### Cell Text Diffs")
            lines.extend(f"- {d}" for d in text_diffs[:50])
            if len(text_diffs) > 50:
                lines.append(f"- ... {len(text_diffs) - 50} more")
            lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"warnings": dict(warnings), "tables_compared": max_tables}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ppv3-jsonl", type=Path, default=Path("benchmark_work/paddleocrvl_table_metadata_aihub12/ppstructurev3_table_structure/table_metadata.jsonl"))
    ap.add_argument("--vl-jsonl", type=Path, default=Path("benchmark_work/paddleocrvl_table_metadata_aihub12/training_joined_table_and_original_bbox.jsonl"))
    ap.add_argument("--train26", type=Path, default=Path("data/train_26.jsonl"))
    ap.add_argument("--output-dir", type=Path, default=Path("review_ppv3"))
    ap.add_argument("--ppv3-failed-jsonl", type=Path, default=Path("data/failed_conversions_ppv3.jsonl"))
    ap.add_argument("--vl-failed-jsonl", type=Path, default=Path("data/failed_conversions.jsonl"))
    args = ap.parse_args()

    pp_groups = group_by_image(load_jsonl(args.ppv3_jsonl))
    vl_groups = group_by_image(load_jsonl(args.vl_jsonl))
    ids = [r["image_id"] for r in load_jsonl(args.train26)]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "overlays").mkdir(exist_ok=True)
    (args.output_dir / "markdown").mkdir(exist_ok=True)

    summary_lines = ["# PPV3 Teacher Review Audit", ""]
    table_agree = 0
    warning_counts = Counter()
    missing_pp_records = 0
    missing_vl_records = 0
    index_lines = ["# PPV3 Review Index", ""]
    for image_id in ids:
        pp_recs = pp_groups.get(image_id, [])
        vl_recs = vl_groups.get(image_id, [])
        pp_table_recs = [r for r in pp_recs if r.get("table_metadata")]
        vl_table_recs = [r for r in vl_recs if r.get("table_metadata")]
        pp_tables = [r["table_metadata"] for r in sorted(pp_table_recs, key=lambda r: (r["table_metadata"]["bbox"][1], r["table_metadata"]["bbox"][0], r["table_metadata"].get("table_index", 0)))]
        vl_tables = [r["table_metadata"] for r in sorted(vl_table_recs, key=lambda r: (r["table_metadata"]["bbox"][1], r["table_metadata"]["bbox"][0], r["table_metadata"].get("table_index", 0)))]
        if len(pp_tables) == len(vl_tables):
            table_agree += 1
        if not pp_recs:
            missing_pp_records += 1
            continue
        if not vl_recs:
            missing_vl_records += 1
        first = pp_recs[0] if pp_recs else vl_recs[0]
        _, _, texts = parse_aihub_texts(first["original_bbox_json"])
        render_overlay(Path(first["image_path"]), first["original_bbox_json"], pp_tables, args.output_dir / "overlays" / f"{image_id}_ppv3_overlay.jpg", "ppv3")
        md_stats = write_image_md(args.output_dir / "markdown" / f"{image_id}.md", image_id, pp_tables, vl_tables, texts)
        warning_counts.update(md_stats["warnings"])
        summary_lines.append(f"- {image_id}: PPV3 tables={len(pp_tables)} VL1.6 tables={len(vl_tables)} agree={len(pp_tables) == len(vl_tables)}")
        index_lines.append(f"- [{image_id}](markdown/{image_id}.md) | [overlay](overlays/{image_id}_ppv3_overlay.jpg)")
    summary_lines.extend(
        [
            "",
            "## Totals",
            f"- Images reviewed: {len(ids)}",
            f"- Table count agreement: {table_agree}/{len(ids)}",
            f"- PPV3 Stage 2 conversion hard-fails: {count_jsonl(args.ppv3_failed_jsonl)}",
            f"- VL1.6 Stage 2 conversion hard-fails: {count_jsonl(args.vl_failed_jsonl)}",
            f"- PPV3 missing extraction records: {missing_pp_records}",
            f"- VL1.6 missing extraction records: {missing_vl_records}",
            f"- Warning counts: {dict(sorted(warning_counts.items()))}",
        ]
    )
    (args.output_dir / "audit_summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    (args.output_dir / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(json.dumps({"images": len(ids), "table_count_agreement": table_agree, "ppv3_conversion_hard_fails": count_jsonl(args.ppv3_failed_jsonl), "vl16_conversion_hard_fails": count_jsonl(args.vl_failed_jsonl), "output_dir": str(args.output_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
