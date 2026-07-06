#!/usr/bin/env python3
"""Convert teacher table metadata plus AIHub text bboxes to DocTags targets."""

from __future__ import annotations

import argparse
import html
import json
import re
import traceback
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lxml import html as lxml_html


DEFAULT_ROOT = Path("benchmark_work/paddleocrvl_table_metadata_aihub12")
DEFAULT_INPUT = DEFAULT_ROOT / "training_joined_table_and_original_bbox.jsonl"
DEFAULT_OUTPUT = Path("data/train_12.jsonl")
DEFAULT_AUDIT = Path("data/conversion_audit.md")
DEFAULT_FAILED = Path("data/failed_conversions.jsonl")
LOC_GRID = 500
EOS = "<|end_of_text|>"


@dataclass(frozen=True)
class TextBox:
    source_id: str
    text: str
    bbox: tuple[float, float, float, float]


@dataclass
class HtmlCell:
    row: int
    col: int
    rowspan: int
    colspan: int
    text: str
    bbox: tuple[float, float, float, float] | None = None
    final_text: str = ""
    matched_text_ids: list[str] = field(default_factory=list)
    match_methods: list[str] = field(default_factory=list)
    warning: str | None = None


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip() and not line.lstrip().startswith("#")]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def bbox_xywh_to_xyxy(bbox: list[float] | tuple[float, ...]) -> tuple[float, float, float, float]:
    x, y, w, h = bbox
    return (float(x), float(y), float(x) + float(w), float(y) + float(h))


def center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    x0, y0, x1, y1 = bbox
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)


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


def parse_aihub_texts(label_json: dict[str, Any]) -> tuple[int, int, list[TextBox]]:
    image_info = (label_json.get("images") or [{}])[0]
    width = int(image_info["image.width"])
    height = int(image_info["image.height"])
    texts: list[TextBox] = []
    for ann in label_json.get("annotations") or []:
        text = clean_text(ann.get("annotation.text"))
        if not text:
            continue
        bbox = ann.get("annotation.bbox")
        if not bbox or len(bbox) != 4:
            raise ValueError(f"invalid AIHub bbox for annotation {ann.get('id')}: {bbox}")
        texts.append(TextBox(str(ann.get("id")), text, bbox_xywh_to_xyxy(bbox)))
    texts.sort(key=lambda t: (t.bbox[1], t.bbox[0], t.source_id))
    return width, height, texts


def parse_table_html(table_html: str) -> tuple[list[list[str]], list[HtmlCell], list[str]]:
    warnings: list[str] = []
    try:
        doc = lxml_html.fromstring(table_html)
    except Exception as exc:
        raise ValueError(f"HTML parse failure: {exc}") from exc
    table = doc if doc.tag.lower() == "table" else doc.find(".//table")
    if table is None:
        raise ValueError("HTML parse failure: no <table> element")

    occupied: dict[tuple[int, int], int] = {}
    rows: list[list[str]] = []
    cells: list[HtmlCell] = []
    for r, tr in enumerate(table.xpath(".//tr")):
        c = 0
        row: list[str] = []
        while (r, c) in occupied:
            row.append("")
            c += 1
        for td in tr.xpath("./th|./td"):
            while (r, c) in occupied:
                row.append("")
                c += 1
            rowspan = int(td.get("rowspan") or 1)
            colspan = int(td.get("colspan") or 1)
            if rowspan < 1 or colspan < 1:
                raise ValueError(f"invalid span rowspan={rowspan} colspan={colspan}")
            text = clean_text(" ".join(td.itertext()))
            cell = HtmlCell(r, c, rowspan, colspan, text)
            cells.append(cell)
            for rr in range(r, r + rowspan):
                for cc in range(c, c + colspan):
                    occupied[(rr, cc)] = len(cells) - 1
            while len(row) < c:
                row.append("")
            row.append(text)
            for _ in range(colspan - 1):
                row.append(text)
            c += colspan
        rows.append(row)

    n_cols = max((len(row) for row in rows), default=0)
    for r, row in enumerate(rows):
        if len(row) < n_cols:
            row.extend([""] * (n_cols - len(row)))
            warnings.append(f"row_{r}_padded_for_rectangular_grid")
    if not rows or n_cols == 0:
        raise ValueError("empty table grid")

    expanded = [["" for _ in range(n_cols)] for _ in range(len(rows))]
    for (r, c), idx in occupied.items():
        if r >= len(expanded):
            for _ in range(len(expanded), r + 1):
                expanded.append(["" for _ in range(n_cols)])
        if c >= n_cols:
            raise ValueError("non-rectangular table grid after span expansion")
        expanded[r][c] = cells[idx].text
    widths = {len(row) for row in expanded}
    if len(widths) != 1:
        raise ValueError("non-rectangular table grid after span expansion")
    return expanded, cells, warnings


def assign_cell_bboxes(cells: list[HtmlCell], n_rows: int, n_cols: int, table_bbox: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = table_bbox
    col_w = (x1 - x0) / n_cols
    row_h = (y1 - y0) / n_rows
    for cell in cells:
        cell.bbox = (
            x0 + cell.col * col_w,
            y0 + cell.row * row_h,
            x0 + (cell.col + cell.colspan) * col_w,
            y0 + (cell.row + cell.rowspan) * row_h,
        )


def match_texts_to_cells(cells: list[HtmlCell], table_texts: list[TextBox]) -> list[TextBox]:
    by_cell: dict[int, list[TextBox]] = defaultdict(list)
    unplaced: list[TextBox] = []
    for tb in table_texts:
        candidates = [
            (idx, bbox_iou(tb.bbox, cell.bbox or (0, 0, 0, 0)))
            for idx, cell in enumerate(cells)
            if cell.bbox and point_in_bbox(center(tb.bbox), cell.bbox)
        ]
        if not candidates:
            overlaps = [
                (idx, bbox_iou(tb.bbox, cell.bbox or (0, 0, 0, 0)))
                for idx, cell in enumerate(cells)
                if cell.bbox and bbox_iou(tb.bbox, cell.bbox) > 0
            ]
            candidates = overlaps
        if candidates:
            idx = max(candidates, key=lambda item: (item[1], -cells[item[0]].row, -cells[item[0]].col))[0]
            by_cell[idx].append(tb)
        else:
            unplaced.append(tb)

    for idx, cell in enumerate(cells):
        matched = sorted(by_cell.get(idx, []), key=lambda t: (t.bbox[1], t.bbox[0], t.source_id))
        if matched:
            cell.final_text = " ".join(t.text for t in matched)
            cell.matched_text_ids = [t.source_id for t in matched]
            cell.match_methods = ["geometry"] * len(matched)
        else:
            cell.final_text = cell.text
            if cell.text:
                cell.warning = "paddle_text_only"
    return unplaced


def append_unplaced_to_nearest_cells(cells: list[HtmlCell], unplaced: list[TextBox]) -> None:
    for tb in unplaced:
        cx, cy = center(tb.bbox)
        idx = min(
            range(len(cells)),
            key=lambda i: (
                (center(cells[i].bbox or (0, 0, 0, 0))[0] - cx) ** 2
                + (center(cells[i].bbox or (0, 0, 0, 0))[1] - cy) ** 2,
                cells[i].row,
                cells[i].col,
            ),
        )
        cell = cells[idx]
        cell.final_text = clean_text(f"{cell.final_text} {tb.text}")
        cell.matched_text_ids.append(tb.source_id)
        cell.match_methods.append("nearest_unplaced")


def normalize_for_match(value: Any) -> str:
    return re.sub(r"[\s\W_]+", "", str(value or "").casefold())


def cell_from_ppv3(raw: dict[str, Any]) -> HtmlCell:
    bbox = raw.get("bbox")
    cell = HtmlCell(
        row=int(raw.get("row", 0)),
        col=int(raw.get("col", 0)),
        rowspan=int(raw.get("rowspan", 1) or 1),
        colspan=int(raw.get("colspan", 1) or 1),
        text=clean_text(raw.get("ocr_text") or raw.get("text") or ""),
    )
    if isinstance(bbox, list) and len(bbox) == 4:
        cell.bbox = tuple(float(v) for v in bbox)
    return cell


def match_texts_to_ppv3_cells(cells: list[HtmlCell], table_texts: list[TextBox]) -> tuple[list[TextBox], dict[str, int]]:
    by_cell: dict[int, list[tuple[TextBox, str]]] = defaultdict(list)
    unplaced: list[TextBox] = []
    used_text_ids: set[str] = set()
    counts: Counter[str] = Counter()

    for tb in table_texts:
        candidates = [
            (idx, bbox_iou(tb.bbox, cell.bbox or (0, 0, 0, 0)))
            for idx, cell in enumerate(cells)
            if cell.bbox and point_in_bbox(center(tb.bbox), cell.bbox)
        ]
        if not candidates:
            candidates = [
                (idx, bbox_iou(tb.bbox, cell.bbox or (0, 0, 0, 0)))
                for idx, cell in enumerate(cells)
                if cell.bbox and bbox_iou(tb.bbox, cell.bbox) > 0
            ]
        if candidates:
            idx = max(candidates, key=lambda item: (item[1], -cells[item[0]].row, -cells[item[0]].col))[0]
            by_cell[idx].append((tb, "geometry"))
            used_text_ids.add(tb.source_id)
            counts["geometry_texts"] += 1
        else:
            unplaced.append(tb)

    remaining = {tb.source_id: tb for tb in unplaced}
    for idx, cell in enumerate(cells):
        if by_cell.get(idx):
            continue
        wanted = normalize_for_match(cell.text)
        if not wanted:
            continue
        matched: list[str] = []
        for source_id, tb in sorted(remaining.items(), key=lambda item: (item[1].bbox[1], item[1].bbox[0], item[0])):
            got = normalize_for_match(tb.text)
            if got and (got in wanted or wanted in got):
                matched.append(source_id)
        for source_id in matched:
            tb = remaining.pop(source_id)
            by_cell[idx].append((tb, "text_fallback"))
            used_text_ids.add(tb.source_id)
            counts["text_fallback_texts"] += 1

    still_unplaced = [tb for tb in unplaced if tb.source_id not in used_text_ids]
    for idx, cell in enumerate(cells):
        matched = sorted(by_cell.get(idx, []), key=lambda item: (item[0].bbox[1], item[0].bbox[0], item[0].source_id))
        if matched:
            cell.final_text = " ".join(t.text for t, _ in matched)
            cell.matched_text_ids = [t.source_id for t, _ in matched]
            cell.match_methods = [method for _, method in matched]
        else:
            cell.final_text = cell.text
            if cell.text:
                cell.warning = "ppv3_text_only"
            counts["unmatched_cells"] += 1
    return still_unplaced, dict(counts)


def otsl_from_cells(cells: list[HtmlCell], n_rows: int, n_cols: int) -> str:
    slot: list[list[tuple[str, HtmlCell | None]]] = [[("empty", None) for _ in range(n_cols)] for _ in range(n_rows)]
    for cell in cells:
        for rr in range(cell.row, cell.row + cell.rowspan):
            for cc in range(cell.col, cell.col + cell.colspan):
                if rr >= n_rows or cc >= n_cols:
                    raise ValueError("cell span exceeds rectangular grid")
                if rr == cell.row and cc == cell.col:
                    slot[rr][cc] = ("origin", cell)
                elif rr == cell.row:
                    slot[rr][cc] = ("left", cell)
                elif cc == cell.col:
                    slot[rr][cc] = ("up", cell)
                else:
                    slot[rr][cc] = ("x", cell)
    out: list[str] = []
    for row in slot:
        for kind, cell in row:
            if kind == "origin":
                text = html.escape(cell.final_text if cell else "", quote=False)
                out.append(f"<fcel>{text}" if text else "<ecel>")
            elif kind == "left":
                out.append("<lcel>")
            elif kind == "up":
                out.append("<ucel>")
            elif kind == "x":
                out.append("<xcel>")
            else:
                out.append("<ecel>")
        out.append("<nl>")
    return "".join(out)


def loc(v: float, full: int) -> int:
    if full <= 0:
        raise ValueError("invalid image dimension")
    return max(0, min(LOC_GRID - 1, int(round(LOC_GRID * v / full))))


def loc_tokens(bbox: tuple[float, float, float, float], width: int, height: int) -> str:
    x0, y0, x1, y1 = bbox
    vals = [loc(x0, width), loc(y0, height), loc(x1, width), loc(y1, height)]
    return "".join(f"<loc_{v}>" for v in vals)


def rebuild_joined_input(output_path: Path, root: Path, source_scope: str) -> None:
    manifests: dict[str, dict[str, Any]] = {}
    manifest_paths = [root / "additional_table_search/input/additional_candidates_manifest.json"]
    table_paths = [root / "additional_table_search/paddleocrvl_vllm_table_structure/table_metadata.jsonl"]
    if source_scope == "all":
        manifest_paths.insert(0, root / "input/aihub12_manifest.json")
        table_paths.insert(0, root / "paddleocrvl_vllm_table_structure/table_metadata.jsonl")
    for mp in manifest_paths:
        if not mp.exists():
            continue
        for rec in read_json(mp):
            manifests[rec["image_id"]] = rec

    table_records: list[dict[str, Any]] = []
    for tp in table_paths:
        if tp.exists():
            table_records.extend(load_jsonl(tp))
    if not table_records:
        raise FileNotFoundError("no table_metadata.jsonl files found to rebuild joined input")

    joined: list[dict[str, Any]] = []
    for tm in sorted(table_records, key=lambda r: (r["image_id"], int(r.get("table_index", 0)), r.get("category", ""))):
        image_id = tm["image_id"]
        if image_id not in manifests:
            raise KeyError(f"missing manifest record for {image_id}")
        manifest = manifests[image_id]
        label_path = Path(manifest["label_path"])
        if not label_path.exists():
            raise FileNotFoundError(f"missing label file: {label_path}")
        joined.append(
            {
                "image_id": image_id,
                "category": tm.get("category") or manifest.get("category"),
                "image_path": manifest["image_path"],
                "original_label_path": str(label_path),
                "original_bbox_json": read_json(label_path),
                "table_metadata": tm,
            }
        )
    write_jsonl(output_path, joined)


def convert_image(image_id: str, records: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    first = records[0]
    category = first["category"]
    image_path = first["image_path"]
    width, height, all_texts = parse_aihub_texts(first["original_bbox_json"])
    tables = sorted([r["table_metadata"] for r in records if r.get("table_metadata")], key=lambda r: (r["bbox"][1], r["bbox"][0], int(r.get("table_index", 0))))
    table_bboxes = [tuple(map(float, t["bbox"])) for t in tables]

    consumed_by_table: dict[str, int] = {}
    for tb in all_texts:
        containing = [idx for idx, box in enumerate(table_bboxes) if point_in_bbox(center(tb.bbox), box)]
        if containing:
            idx = min(containing, key=lambda i: (table_bboxes[i][1], table_bboxes[i][0], i))
            consumed_by_table[tb.source_id] = idx
    free_texts = [tb for tb in all_texts if tb.source_id not in consumed_by_table]

    elements: list[tuple[tuple[float, float, str, int], str]] = []
    table_audits: list[dict[str, Any]] = []
    assigned_source_ids: list[str] = []
    expected_text_units: list[str] = []

    for tb in free_texts:
        tag = f"<text>{loc_tokens(tb.bbox, width, height)}{html.escape(tb.text, quote=False)}</text>"
        elements.append(((tb.bbox[1], tb.bbox[0], "text", int(tb.source_id)), tag))
        assigned_source_ids.append(tb.source_id)
        expected_text_units.append(tb.text)

    for idx, table in enumerate(tables):
        table_bbox = table_bboxes[idx]
        expanded, cells, parse_warnings = parse_table_html(table["table_html"])
        n_rows = len(expanded)
        n_cols = len(expanded[0]) if expanded else 0
        if any(len(row) != n_cols for row in expanded):
            raise ValueError(f"{image_id} table {idx} non-rectangular grid")
        assign_cell_bboxes(cells, n_rows, n_cols, table_bbox)
        table_texts = [tb for tb in all_texts if consumed_by_table.get(tb.source_id) == idx]
        unplaced = match_texts_to_cells(cells, table_texts)
        append_unplaced_to_nearest_cells(cells, unplaced)
        for cell in cells:
            assigned_source_ids.extend(cell.matched_text_ids)
            if cell.final_text:
                expected_text_units.append(cell.final_text)
        otsl = otsl_from_cells(cells, n_rows, n_cols)
        table_tag = f"<otsl>{loc_tokens(table_bbox, width, height)}{otsl}</otsl>"
        elements.append(((table_bbox[1], table_bbox[0], "table", int(table.get("table_index", idx))), table_tag))
        paddle_only = sum(1 for cell in cells if cell.warning == "paddle_text_only")
        matched = sum(1 for cell in cells if cell.matched_text_ids)
        table_audits.append(
            {
                "table_index": table.get("table_index", idx),
                "bbox": list(map(int, table_bbox)),
                "rows": n_rows,
                "cols": n_cols,
                "cells_total": len(cells),
                "matched_to_aihub": matched,
                "paddle_text_only": paddle_only,
                "unplaced_in_table": [{"id": t.source_id, "text": t.text, "bbox": list(t.bbox)} for t in unplaced],
                "warnings": parse_warnings
                + (["paddle_text_only"] if paddle_only else [])
                + (["unplaced_in_table"] if unplaced else []),
            }
        )

    elements.sort(key=lambda item: item[0])
    target = "<doctag>" + "\n".join(tag for _, tag in elements) + "</doctag>" + EOS
    validate_source_assignment(all_texts, assigned_source_ids)
    validate_target(target, expected_text_units)

    consumed_count = len(consumed_by_table)
    audit = {
        "image_id": image_id,
        "category": category,
        "aihub_text_items": len(all_texts),
        "consumed_text_items": consumed_count,
        "free_text_items": len(free_texts),
        "tables": len(tables),
        "cells_total": sum(t["cells_total"] for t in table_audits),
        "matched_to_aihub": sum(t["matched_to_aihub"] for t in table_audits),
        "paddle_text_only": sum(t["paddle_text_only"] for t in table_audits),
        "unplaced": sum(len(t["unplaced_in_table"]) for t in table_audits),
        "table_details": table_audits,
        "target_first_300": target[:300],
        "target_last_100": target[-100:],
        "target_length": len(target),
    }
    out = {"image_id": image_id, "category": category, "image_path": image_path, "doctags_target": target}
    return out, audit


def convert_image_ppv3(image_id: str, records: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    first = records[0]
    category = first["category"]
    image_path = first["image_path"]
    width, height, all_texts = parse_aihub_texts(first["original_bbox_json"])
    tables = sorted([r["table_metadata"] for r in records if r.get("table_metadata")], key=lambda r: (r["bbox"][1], r["bbox"][0], int(r.get("table_index", 0))))
    table_bboxes = [tuple(map(float, t["bbox"])) for t in tables]

    consumed_by_table: dict[str, int] = {}
    for tb in all_texts:
        containing = [idx for idx, box in enumerate(table_bboxes) if point_in_bbox(center(tb.bbox), box)]
        if containing:
            idx = min(containing, key=lambda i: (table_bboxes[i][1], table_bboxes[i][0], i))
            consumed_by_table[tb.source_id] = idx
    free_texts = [tb for tb in all_texts if tb.source_id not in consumed_by_table]

    elements: list[tuple[tuple[float, float, str, int], str]] = []
    table_audits: list[dict[str, Any]] = []
    assigned_source_ids: list[str] = []
    expected_text_units: list[str] = []

    for tb in free_texts:
        tag = f"<text>{loc_tokens(tb.bbox, width, height)}{html.escape(tb.text, quote=False)}</text>"
        elements.append(((tb.bbox[1], tb.bbox[0], "text", int(tb.source_id)), tag))
        assigned_source_ids.append(tb.source_id)
        expected_text_units.append(tb.text)

    for idx, table in enumerate(tables):
        table_bbox = table_bboxes[idx]
        raw_cells = table.get("cells") or []
        cells = [cell_from_ppv3(raw) for raw in raw_cells]
        if not cells:
            expanded, cells, parse_warnings = parse_table_html(table.get("table_html") or table.get("structure_html") or "")
            n_rows = len(expanded)
            n_cols = len(expanded[0]) if expanded else 0
            assign_cell_bboxes(cells, n_rows, n_cols, table_bbox)
        else:
            parse_warnings = list(table.get("warnings") or [])
            n_rows = int(table.get("n_rows") or max((cell.row + cell.rowspan for cell in cells), default=0))
            n_cols = int(table.get("n_cols") or max((cell.col + cell.colspan for cell in cells), default=0))
        if n_rows <= 0 or n_cols <= 0:
            raise ValueError(f"{image_id} table {idx} empty ppv3 grid")
        if any(cell.bbox is None for cell in cells):
            assign_cell_bboxes(cells, n_rows, n_cols, table_bbox)

        table_texts = [tb for tb in all_texts if consumed_by_table.get(tb.source_id) == idx]
        unplaced, method_counts = match_texts_to_ppv3_cells(cells, table_texts)
        append_unplaced_to_nearest_cells(cells, unplaced)
        for cell in cells:
            assigned_source_ids.extend(cell.matched_text_ids)
            if cell.final_text:
                expected_text_units.append(cell.final_text)
        otsl = otsl_from_cells(cells, n_rows, n_cols)
        table_tag = f"<otsl>{loc_tokens(table_bbox, width, height)}{otsl}</otsl>"
        elements.append(((table_bbox[1], table_bbox[0], "table", int(table.get("table_index", idx))), table_tag))
        ppv3_only = sum(1 for cell in cells if cell.warning == "ppv3_text_only")
        matched = sum(1 for cell in cells if cell.matched_text_ids)
        method_counter = Counter(method for cell in cells for method in cell.match_methods)
        table_audits.append(
            {
                "table_index": table.get("table_index", idx),
                "bbox": list(map(int, table_bbox)),
                "rows": n_rows,
                "cols": n_cols,
                "cells_total": len(cells),
                "matched_to_aihub": matched,
                "ppv3_text_only": ppv3_only,
                "match_methods": dict(sorted(method_counter.items())),
                "match_text_counts": method_counts,
                "unplaced_in_table": [{"id": t.source_id, "text": t.text, "bbox": list(t.bbox)} for t in unplaced],
                "warnings": parse_warnings
                + (["ppv3_text_only"] if ppv3_only else [])
                + (["unplaced_in_table"] if unplaced else []),
            }
        )

    elements.sort(key=lambda item: item[0])
    target = "<doctag>" + "\n".join(tag for _, tag in elements) + "</doctag>" + EOS
    validate_source_assignment(all_texts, assigned_source_ids)
    validate_target(target, expected_text_units)

    consumed_count = len(consumed_by_table)
    audit = {
        "image_id": image_id,
        "category": category,
        "aihub_text_items": len(all_texts),
        "consumed_text_items": consumed_count,
        "free_text_items": len(free_texts),
        "tables": len(tables),
        "cells_total": sum(t["cells_total"] for t in table_audits),
        "matched_to_aihub": sum(t["matched_to_aihub"] for t in table_audits),
        "ppv3_text_only": sum(t["ppv3_text_only"] for t in table_audits),
        "unplaced": sum(len(t["unplaced_in_table"]) for t in table_audits),
        "table_details": table_audits,
        "target_first_300": target[:300],
        "target_last_100": target[-100:],
        "target_length": len(target),
    }
    out = {"image_id": image_id, "category": category, "image_path": image_path, "doctags_target": target}
    return out, audit


def validate_source_assignment(all_texts: list[TextBox], assigned_source_ids: list[str]) -> None:
    expected = Counter(tb.source_id for tb in all_texts)
    observed = Counter(assigned_source_ids)
    if observed != expected:
        missing = sorted((expected - observed).elements())
        duplicated = sorted((observed - expected).elements())
        raise ValueError(f"AIHub text source assignment mismatch missing={missing[:10]} duplicated={duplicated[:10]}")


def extract_roundtrip_text_units(target: str) -> list[str]:
    units: list[str] = []
    body = target.replace(EOS, "")
    for match in re.finditer(r"<text>(.*?)</text>", body, flags=re.S):
        content = re.sub(r"^(?:<loc_\d+>){4}", "", match.group(1))
        text = clean_text(html.unescape(re.sub(r"<[^>]+>", "", content)))
        if text:
            units.append(text)
    for match in re.finditer(r"<otsl>(.*?)</otsl>", body, flags=re.S):
        table_body = re.sub(r"^(?:<loc_\d+>){4}", "", match.group(1))
        parts = re.split(r"(<(?:fcel|ecel|lcel|ucel|xcel|nl)>)", table_body)
        current_tag: str | None = None
        for part in parts:
            if not part:
                continue
            if re.fullmatch(r"<(?:fcel|ecel|lcel|ucel|xcel|nl)>", part):
                current_tag = part
                continue
            if current_tag == "<fcel>":
                text = clean_text(html.unescape(re.sub(r"<[^>]+>", "", part)))
                if text:
                    units.append(text)
    return units


def validate_target(target: str, expected_text_units: list[str]) -> None:
    if not target.endswith(f"</doctag>{EOS}"):
        raise ValueError("target does not end with </doctag><|end_of_text|>")
    locs = [int(v) for v in re.findall(r"<loc_(\d+)>", target)]
    if not locs:
        raise ValueError("target has no loc tokens")
    bad = [v for v in locs if v < 0 or v >= LOC_GRID]
    if bad:
        raise ValueError(f"loc tokens out of range: {bad[:10]}")
    for table_body in re.findall(r"<otsl>.*?(?:<loc_\d+>){4}(.*?)</otsl>", target, flags=re.S):
        rows = [row for row in table_body.split("<nl>") if row]
        widths = []
        for row in rows:
            tokens = re.findall(r"<(?:fcel|ecel|lcel|ucel|xcel)>", row)
            widths.append(len(tokens))
        if widths and len(set(widths)) != 1:
            raise ValueError(f"OTSL grid not rectangular: {widths}")
    observed_units = Counter(extract_roundtrip_text_units(target))
    expected_units = Counter(clean_text(unit) for unit in expected_text_units if clean_text(unit))
    if observed_units != expected_units:
        raise ValueError(
            f"round-trip text unit mismatch missing={list((expected_units - observed_units).elements())[:10]} "
            f"extra={list((observed_units - expected_units).elements())[:10]}"
        )

def write_audit(path: Path, audits: list[dict[str, Any]], failures: list[dict[str, Any]], input_count: int, adapter: str = "vl16") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Conversion Audit",
        "",
        f"- Adapter: {adapter}",
        f"- Input table records: {input_count}",
        f"- Converted images: {len(audits)}",
        f"- Failed images: {len(failures)}",
        "- Ordering rule: sort merged free-text and table elements by top-left y, then x; text precedes table for identical coordinates; stable id/table index breaks ties.",
        "",
    ]
    for audit in audits:
        lines.extend(
            [
                f"## {audit['image_id']} ({audit['category']})",
                "",
                f"- AIHub text items: {audit['aihub_text_items']}",
                f"- Consumed vs free: {audit['consumed_text_items']} consumed / {audit['free_text_items']} free",
                f"- Tables: {audit['tables']}",
                f"- Cells total / matched-to-AIHub / teacher_text_only / unplaced: {audit['cells_total']} / {audit['matched_to_aihub']} / {audit.get('paddle_text_only', audit.get('ppv3_text_only', 0))} / {audit['unplaced']}",
                f"- Target length: {audit['target_length']}",
                f"- First 300 chars: `{audit['target_first_300']}`",
                f"- Last 100 chars: `{audit['target_last_100']}`",
                "",
            ]
        )
        for table in audit["table_details"]:
            lines.append(
                f"  - table {table['table_index']} bbox={table['bbox']} grid={table['rows']}x{table['cols']} "
                f"cells={table['cells_total']} matched={table['matched_to_aihub']} teacher_text_only={table.get('paddle_text_only', table.get('ppv3_text_only', 0))} "
                f"unplaced={len(table['unplaced_in_table'])} warnings={table['warnings']}"
            )
            if table.get("match_methods"):
                lines.append(f"    - match_methods={table['match_methods']}")
            for item in table["unplaced_in_table"][:10]:
                lines.append(f"    - unplaced id={item['id']} bbox={item['bbox']} text={item['text']}")
        lines.append("")
    if failures:
        lines.extend(["# Failures", ""])
        for failure in failures:
            lines.append(f"- {failure['image_id']}: {failure['reason']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--audit-md", type=Path, default=DEFAULT_AUDIT)
    ap.add_argument("--failed-jsonl", type=Path, default=DEFAULT_FAILED)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--source-scope", choices=["additional", "all"], default="additional")
    ap.add_argument("--rebuild-joined", action="store_true")
    ap.add_argument("--adapter", choices=["vl16", "ppv3"], default="vl16")
    args = ap.parse_args()

    if args.rebuild_joined or not args.input_jsonl.exists():
        rebuild_joined_input(args.input_jsonl, args.root, args.source_scope)

    records = load_jsonl(args.input_jsonl)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        groups[rec["image_id"]].append(rec)
    image_ids = sorted(groups)
    if args.limit is not None:
        image_ids = image_ids[: args.limit]

    outputs: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for image_id in image_ids:
        try:
            if args.adapter == "vl16":
                out, audit = convert_image(image_id, groups[image_id])
            else:
                out, audit = convert_image_ppv3(image_id, groups[image_id])
            outputs.append(out)
            audits.append(audit)
        except Exception as exc:
            failures.append(
                {
                    "image_id": image_id,
                    "reason": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )

    outputs.sort(key=lambda r: r["image_id"])
    audits.sort(key=lambda r: r["image_id"])
    failures.sort(key=lambda r: r["image_id"])
    write_jsonl(args.output_jsonl, outputs)
    write_jsonl(args.failed_jsonl, failures)
    write_audit(args.audit_md, audits, failures, len(records), args.adapter)
    print(
        json.dumps(
            {
                "input_table_records": len(records),
                "grouped_images": len(groups),
                "attempted_images": len(image_ids),
                "converted_images": len(outputs),
                "failed_images": len(failures),
                "output_jsonl": str(args.output_jsonl),
                "audit_md": str(args.audit_md),
                "failed_jsonl": str(args.failed_jsonl),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
