#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from PIL import Image
from docling_core.types.doc import DoclingDocument
from docling_core.types.doc.document import DocTagsDocument

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.granite_docling_lora_data import EOS_TEXT
from scripts.score_kdoc import parse_html_tables, parse_markdown_tables, run_baseline


def doctags_to_scorer_markdown(doctags: str, image_path: str, document_name: str) -> str:
    doctags = doctags.rstrip()
    if doctags.endswith(EOS_TEXT):
        doctags = doctags[: -len(EOS_TEXT)]
    image = Image.open(image_path).convert("RGB")
    doctags_doc = DocTagsDocument.from_doctags_and_image_pairs([doctags], [image])
    doc = DoclingDocument.load_from_doctags(doctags_doc, document_name=document_name)
    return doc.export_to_markdown()


class DocTagsDecodeToScorerFormatTest(unittest.TestCase):
    def test_first_three_training_targets_decode_to_scorer_markdown(self) -> None:
        records = []
        with Path("data/train_26.jsonl").open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
                if len(records) == 3:
                    break

        self.assertEqual(len(records), 3)
        decoded_markdown = []
        for rec in records:
            markdown = doctags_to_scorer_markdown(
                rec["doctags_target"], rec["image_path"], rec["image_id"]
            )
            ok, reason = run_baseline(markdown)
            self.assertTrue(ok, f"baseline scorer rejected {rec['image_id']}: {reason}")
            self.assertGreater(len(markdown.strip()), 100, rec["image_id"])
            decoded_markdown.append(markdown)

        parsed_table_count = sum(
            len(parse_markdown_tables(markdown)) + len(parse_html_tables(markdown))
            for markdown in decoded_markdown
        )
        self.assertGreater(parsed_table_count, 0)


if __name__ == "__main__":
    unittest.main()
