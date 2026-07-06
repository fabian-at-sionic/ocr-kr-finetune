# Evaluation Notes

## Scorer input contract

`KDoc-OCRBench-V2` scoring is performed by `scripts/score_kdoc.py`. For a candidate named `<candidate>`, the scorer expects markdown files under:

```text
dataset/KDoc-OCRBench-V2/<candidate>/<pdf-stem>_pg1_repeat1.md
```

The scorer loads the benchmark manifests from `dataset/KDoc-OCRBench-V2` and reads exactly one markdown file per PDF listed in `categories.jsonl`. Missing files are counted as failed outputs.

The markdown content is the scorer-format artifact. It is expected to be produced from model DocTags with `docling_core`:

1. Strip only the terminal tokenizer EOS marker (`<|end_of_text|>`) when present.
2. Build `DocTagsDocument.from_doctags_and_image_pairs([doctags], [page_image])`.
3. Load `DoclingDocument.load_from_doctags(...)`.
4. Write `DoclingDocument.export_to_markdown()` to the candidate markdown path.

No fallback text extraction is valid for benchmark scoring. If `docling_core` cannot parse a generation or cannot export markdown, the run must record that exception for the document and count it as an invalid parse. Silent fallback extraction would make table, text, and baseline metrics incomparable.

## Scorer behavior

`score_kdoc.py` evaluates four suites:

- `baseline`: verifies that output exists, contains alphanumeric content, avoids disallowed character classes, and does not end in obvious repeated n-grams.
- `header_footer_tests`: fuzzy present/absent text checks over markdown text.
- `text_present`: fuzzy present text checks over markdown text.
- `tables`: parses markdown and HTML tables, then checks cell text and neighbor/header relationships.

The table suite therefore requires real table structure in markdown or HTML. Plain fallback text from DocTags is not an acceptable substitute.

## Training image preprocessing

The overfit training data in `data/train_26.jsonl` uses pre-rendered JPEG images from `benchmark_work/paddleocrvl_table_metadata_aihub12/additional_table_search/input/images`. Training did not rasterize PDFs inside `scripts/train_overfit_granite_docling_lora.py`; it opened those JPEGs directly through `GraniteDoclingJsonlDataset` and then used the Granite/Idefics3 processor. The benchmark PDF rasterization DPI must therefore be treated as a benchmark-specific approximation, not as a confirmed match to the training image source.
