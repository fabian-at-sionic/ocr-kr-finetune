#!/usr/bin/env python3
import argparse
import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup
from rapidfuzz import fuzz
from tqdm import tqdm


def normalize_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"<br\s*/?>", " ", text)
    text = re.sub(r"</?p>", "", text)
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)
    text = re.sub(r"\s+", " ", text)
    text = unicodedata.normalize("NFC", text)
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\uff3f": "_",
        "\u2013": "-",
        "\u2014": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2212": "-",
        "\u00b5": "\u03bc",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


@dataclass(frozen=True)
class TableData:
    cell_text: dict[tuple[int, int], str]
    heading_cells: set[tuple[int, int]]
    is_rectangular: bool
    up_relations: dict[tuple[int, int], set[tuple[int, int]]]
    down_relations: dict[tuple[int, int], set[tuple[int, int]]]
    left_relations: dict[tuple[int, int], set[tuple[int, int]]]
    right_relations: dict[tuple[int, int], set[tuple[int, int]]]

    def _walk_heading_relations(
        self, start: tuple[int, int], relation: dict[tuple[int, int], set[tuple[int, int]]]
    ) -> set[tuple[int, int]]:
        heading_cells = set()
        end_cells = set()
        visited = set()
        to_visit = {start}
        while to_visit:
            cur = to_visit.pop()
            visited.add(cur)
            if cur in self.heading_cells:
                heading_cells.add(cur)
            if not relation.get(cur):
                end_cells.add(cur)
            else:
                to_visit |= relation[cur] - visited
        heading_cells.discard(start)
        end_cells.discard(start)
        return heading_cells or end_cells

    def top_heading_relations(self, row: int, col: int) -> set[tuple[int, int]]:
        return self._walk_heading_relations((row, col), self.up_relations)

    def left_heading_relations(self, row: int, col: int) -> set[tuple[int, int]]:
        return self._walk_heading_relations((row, col), self.left_relations)


def safe_span_int(value, default: int = 1) -> int:
    if value in (None, "", 0):
        return default
    try:
        span = int(value)
    except (TypeError, ValueError):
        return default
    return span if span > 0 else default


def build_table_data(row_specs: list[list[dict]]) -> Optional[TableData]:
    if not row_specs:
        return None
    cell_text = {}
    heading_cells = set()
    cell_meta = {}
    occupancy = []
    active_rowspans = []

    for row_idx, cells in enumerate(row_specs):
        row_entries = []
        col_index = 0
        spec_idx = 0
        while spec_idx < len(cells) or col_index < len(active_rowspans):
            if col_index < len(active_rowspans) and active_rowspans[col_index] is not None:
                cell_id, remaining = active_rowspans[col_index]
                row_entries.append(cell_id)
                remaining -= 1
                active_rowspans[col_index] = (cell_id, remaining) if remaining > 0 else None
                col_index += 1
                continue
            if spec_idx >= len(cells):
                if col_index < len(active_rowspans):
                    row_entries.append(None)
                    col_index += 1
                    continue
                break
            spec = cells[spec_idx]
            spec_idx += 1
            rowspan = max(1, safe_span_int(spec.get("rowspan", 1)))
            colspan = max(1, safe_span_int(spec.get("colspan", 1)))
            cell_id = (row_idx, col_index)
            cell_text[cell_id] = spec.get("text", "") or ""
            if spec.get("is_heading", False):
                heading_cells.add(cell_id)
            cell_meta[cell_id] = {"row": row_idx, "col": col_index, "rowspan": rowspan, "colspan": colspan}
            required_len = col_index + colspan
            if len(active_rowspans) < required_len:
                active_rowspans.extend([None] * (required_len - len(active_rowspans)))
            for offset in range(colspan):
                current_col = col_index + offset
                row_entries.append(cell_id)
                active_rowspans[current_col] = (cell_id, rowspan - 1) if rowspan > 1 else None
            col_index += colspan
        occupancy.append(row_entries)

    while any(entry is not None for entry in active_rowspans):
        row_entries = []
        for col_index, span_entry in enumerate(active_rowspans):
            if span_entry is None:
                row_entries.append(None)
                continue
            cell_id, remaining = span_entry
            row_entries.append(cell_id)
            remaining -= 1
            active_rowspans[col_index] = (cell_id, remaining) if remaining > 0 else None
        occupancy.append(row_entries)

    if not cell_text:
        return None
    valid_columns = {idx for row in occupancy for idx, value in enumerate(row) if value is not None}
    if not valid_columns:
        return None
    table_width = max(valid_columns) + 1
    for row in occupancy:
        if len(row) < table_width:
            row.extend([None] * (table_width - len(row)))
        elif len(row) > table_width:
            del row[table_width:]

    table_height = len(occupancy)
    up_rel = defaultdict(set)
    down_rel = defaultdict(set)
    left_rel = defaultdict(set)
    right_rel = defaultdict(set)

    for cell_id, meta in cell_meta.items():
        row_start = meta["row"]
        col_start = meta["col"]
        if row_start >= table_height or col_start >= table_width:
            continue
        row_end = min(table_height - 1, row_start + meta["rowspan"] - 1)
        col_end = min(table_width - 1, col_start + meta["colspan"] - 1)
        for row in range(row_start, row_end + 1):
            for col in range(col_end + 1, table_width):
                neighbor = occupancy[row][col]
                if neighbor is not None and neighbor != cell_id:
                    right_rel[cell_id].add(neighbor)
                    break
            for col in range(col_start - 1, -1, -1):
                neighbor = occupancy[row][col]
                if neighbor is not None and neighbor != cell_id:
                    left_rel[cell_id].add(neighbor)
                    break
        for col in range(col_start, col_end + 1):
            for row in range(row_end + 1, table_height):
                neighbor = occupancy[row][col]
                if neighbor is not None and neighbor != cell_id:
                    down_rel[cell_id].add(neighbor)
                    break
            for row in range(row_start - 1, -1, -1):
                neighbor = occupancy[row][col]
                if neighbor is not None and neighbor != cell_id:
                    up_rel[cell_id].add(neighbor)
                    break

    return TableData(
        cell_text=cell_text,
        heading_cells=heading_cells,
        is_rectangular=not any(any(x is None for x in row) for row in occupancy),
        up_relations={cell_id: set(up_rel[cell_id]) for cell_id in cell_text},
        down_relations={cell_id: set(down_rel[cell_id]) for cell_id in cell_text},
        left_relations={cell_id: set(left_rel[cell_id]) for cell_id in cell_text},
        right_relations={cell_id: set(right_rel[cell_id]) for cell_id in cell_text},
    )


def parse_markdown_tables(md_content: str) -> list[TableData]:
    parsed = []
    current = []
    in_table = False
    for line in md_content.strip().split("\n"):
        if "|" in line:
            current.append(line)
            in_table = True
            continue
        if in_table and len(current) >= 2:
            table = process_markdown_table(current)
            if table:
                parsed.append(table)
        current = []
        in_table = False
    if in_table and len(current) >= 2:
        table = process_markdown_table(current)
        if table:
            parsed.append(table)
    return parsed


def process_markdown_table(lines: list[str]) -> Optional[TableData]:
    rows = []
    separator_row_index = None
    for i, line in enumerate(lines):
        content = line.replace("|", "").strip()
        if content and all(c in "- :" for c in content):
            separator_row_index = i
            break
    for i, line in enumerate(lines):
        if i == separator_row_index:
            continue
        if line.strip() and all(c in "- :|" for c in line):
            continue
        cells = [cell.strip() for cell in line.split("|")]
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]
        if cells:
            rows.append(cells)
    if not rows:
        return None
    row_specs = [
        [
            {"text": cell, "rowspan": 1, "colspan": 1, "is_heading": row_idx == 0 or col_idx == 0}
            for col_idx, cell in enumerate(row)
        ]
        for row_idx, row in enumerate(rows)
    ]
    return build_table_data(row_specs)


def parse_html_tables(html_content: str) -> list[TableData]:
    soup = BeautifulSoup(html_content, "html.parser")
    parsed = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        row_specs = []
        total_rows = len(rows)
        for row_idx, row in enumerate(rows):
            heading_context = row.find_parent("thead") is not None
            row_spec = []
            for cell in row.find_all(["th", "td"], recursive=False):
                for br in cell.find_all("br"):
                    br.replace_with("\n")
                raw_rowspan = cell.get("rowspan")
                rowspan = safe_span_int(raw_rowspan, 1)
                if isinstance(raw_rowspan, str) and raw_rowspan.strip() == "0":
                    rowspan = max(1, total_rows - row_idx)
                row_spec.append(
                    {
                        "text": cell.get_text(separator="").strip(),
                        "rowspan": rowspan,
                        "colspan": safe_span_int(cell.get("colspan"), 1),
                        "is_heading": cell.name == "th" or heading_context,
                    }
                )
            row_specs.append(row_spec)
        table_data = build_table_data(row_specs)
        if table_data:
            parsed.append(table_data)
    return parsed


def run_text_test(test: dict, content: str) -> tuple[bool, str]:
    query = normalize_text(test["text"])
    md_content = normalize_text(content)
    if not test.get("case_sensitive", True):
        query = query.lower()
        md_content = md_content.lower()
    first_n = test.get("first_n")
    last_n = test.get("last_n")
    if first_n and last_n:
        md_content = md_content[:first_n] + md_content[-last_n:]
    elif first_n:
        md_content = md_content[:first_n]
    elif last_n:
        md_content = md_content[-last_n:]
    threshold = 1.0 - (test.get("max_diffs", 0) / (len(query) or 1))
    best_ratio = fuzz.partial_ratio(query, md_content) / 100.0
    if test["type"] == "present":
        return best_ratio >= threshold, f"best={best_ratio:.3f} threshold={threshold:.3f}"
    return best_ratio < threshold, f"best={best_ratio:.3f} threshold={threshold:.3f}"


def run_table_test(test: dict, content: str) -> tuple[bool, str]:
    cell = normalize_text(test["cell"])
    tables = parse_markdown_tables(content) + parse_html_tables(content)
    if not tables:
        return False, "no tables found"
    threshold = max(0.5, 1.0 - (test.get("max_diffs", 0) / (len(cell) or 1)))
    for table in tables:
        matches = []
        for rowcol, cell_content in table.cell_text.items():
            if fuzz.ratio(cell, normalize_text(cell_content)) / 100.0 >= threshold:
                matches.append(rowcol)
        for rowcol in matches:
            ok = True
            for key, relation_func in [
                ("up", lambda rc: table.up_relations[rc]),
                ("down", lambda rc: table.down_relations[rc]),
                ("left", lambda rc: table.left_relations[rc]),
                ("right", lambda rc: table.right_relations[rc]),
                ("left_heading", lambda rc: table.left_heading_relations(*rc)),
                ("top_heading", lambda rc: table.top_heading_relations(*rc)),
            ]:
                expected = normalize_text(test.get(key, ""))
                if not expected:
                    continue
                rel_threshold = max(0.5, 1.0 - (test.get("max_diffs", 0) / (len(expected) or 1)))
                relation_ok = any(
                    fuzz.ratio(expected, normalize_text(table.cell_text[rel])) / 100.0 >= rel_threshold
                    for rel in relation_func(rowcol)
                )
                if not relation_ok:
                    ok = False
                    break
            if ok:
                return True, ""
    return False, f"no matching table cell for {cell[:40]!r}"


def run_baseline(content: str) -> tuple[bool, str]:
    base_len = len("".join(c for c in content if c.isalnum()).strip())
    if base_len == 0:
        return False, "no alphanumeric content"
    disallowed = re.compile(
        r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f6ff\U0001f1e0-\U0001f1ff]",
        flags=re.UNICODE,
    )
    matches = disallowed.findall(content)
    if matches:
        return False, f"disallowed characters: {matches[:10]}"
    compact = re.sub(r"\s+", " ", content)
    for n in range(1, 6):
        tokens = compact.split()
        if len(tokens) < n * 31:
            continue
        ngrams = [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]
        last = ngrams[-1]
        repeat_count = 0
        for item in reversed(ngrams):
            if item == last:
                repeat_count += 1
            else:
                break
        if repeat_count > 30:
            return False, f"ends with {repeat_count} repeated {n}-grams"
    return True, ""


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", type=Path, default=Path("dataset/KDoc-OCRBench-V2"))
    parser.add_argument("--candidate", default="smol_docling_256m")
    parser.add_argument("--output", type=Path, default=Path("results.md"))
    parser.add_argument("--failed-output", type=Path, default=Path("failed_tests.jsonl"))
    parser.add_argument("--title", default="KDoc OCRBench V2 - SmolDocling 256M")
    parser.add_argument("--model", default="model/docling-project/SmolDocling-256M-preview")
    parser.add_argument("--prompt", default="Convert this page to docling.")
    args = parser.parse_args()

    dataset_dir = args.dataset_dir.resolve()
    candidate_dir = dataset_dir / args.candidate
    categories = load_jsonl(dataset_dir / "categories.jsonl")
    pdf_names = [row["pdf"] for row in categories]
    category_by_pdf = {row["pdf"]: row["category"] for row in categories}

    contents = {}
    missing = []
    for pdf_name in pdf_names:
        path = candidate_dir / f"{Path(pdf_name).stem}_pg1_repeat1.md"
        if path.exists():
            contents[pdf_name] = path.read_text(encoding="utf-8")
        else:
            missing.append(pdf_name)

    suites = [
        ("baseline", [{"pdf": pdf_name, "id": f"{Path(pdf_name).stem}_baseline", "type": "baseline"} for pdf_name in pdf_names]),
        ("header_footer_tests", load_jsonl(dataset_dir / "header_footer_tests.jsonl")),
        ("text_present", load_jsonl(dataset_dir / "text_present.jsonl")),
        ("tables", load_jsonl(dataset_dir / "tables.jsonl")),
    ]

    failed = []
    suite_results = []
    category_results = defaultdict(lambda: [0, 0])

    for suite_name, tests in suites:
        passed = 0
        total = 0
        for test in tqdm(tests, desc=suite_name):
            pdf_name = test["pdf"]
            content = contents.get(pdf_name)
            if content is None:
                ok, reason = False, "missing output"
            elif test["type"] == "baseline":
                ok, reason = run_baseline(content)
            elif test["type"] in {"present", "absent"}:
                ok, reason = run_text_test(test, content)
            elif test["type"] == "table":
                ok, reason = run_table_test(test, content)
            else:
                ok, reason = False, f"unsupported test type {test['type']}"
            total += 1
            passed += int(ok)
            category = category_by_pdf.get(pdf_name, "Unknown")
            category_results[(suite_name, category)][0] += int(ok)
            category_results[(suite_name, category)][1] += 1
            if not ok:
                failed.append({"suite": suite_name, "id": test["id"], "pdf": pdf_name, "reason": reason})
        suite_results.append({"suite": suite_name, "passed": passed, "total": total, "rate": passed / total if total else 0.0})

    overall = sum(row["rate"] for row in suite_results) / len(suite_results)
    args.failed_output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in failed),
        encoding="utf-8",
    )

    lines = [
        f"# {args.title}",
        "",
        f"- Dataset: `{dataset_dir}`",
        f"- Candidate outputs: `{candidate_dir}`",
        f"- Model: `{args.model}`",
        f"- Prompt: `{args.prompt}`",
        f"- PDFs expected: {len(pdf_names)}",
        f"- Missing markdown outputs: {len(missing)}",
        f"- Failed test details: `{args.failed_output}`",
        "",
        "## Scores",
        "",
        "| Suite | Passed | Total | Pass rate |",
        "|---|---:|---:|---:|",
    ]
    for row in suite_results:
        lines.append(f"| {row['suite']} | {row['passed']} | {row['total']} | {row['rate'] * 100:.2f}% |")
    lines.extend(["", f"**Overall (mean of suite pass rates): {overall * 100:.2f}%**", "", "## By Document Category", ""])
    lines.append("| Suite | Category | Passed | Total | Pass rate |")
    lines.append("|---|---|---:|---:|---:|")
    for suite_name, _ in suites:
        for category in ["Manuals", "Notices", "Reports", "Statistics"]:
            passed, total = category_results[(suite_name, category)]
            rate = passed / total if total else 0.0
            lines.append(f"| {suite_name} | {category} | {passed} | {total} | {rate * 100:.2f}% |")
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
