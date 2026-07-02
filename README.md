# ocr-kr-finetune

## Status

This project failed and has been abolished.

The repository is retained only as historical reference. Future work on Korean OCR benchmarking and training should start over completely instead of continuing from the current implementation, experiments, datasets, checkpoints, or benchmark results.

## Project Summary

OCR Bench was an experimental workspace for fine-tuning and evaluating OCR/document models for Korean and Hangul document understanding.

The intended scope was:

- Hangul text-region detection.
- Korean OCR recognition.
- Mixed Korean, English, number, and table document parsing.
- Benchmarking against stronger OCR baselines.

The primary fine-tuning target was IBM Granite/Docling 258M:

```text
model/ibm-granite/granite-docling-258M
```

Comparison-only baselines included PaddleOCR, PaddleOCR-VL, and SmolDocling variants. PaddleOCR/PaddleOCR-VL were used for evaluation context, not as training targets.

## What Was Attempted

The project explored a staged training plan:

1. Build a non-AIHub Korean OCR foundation from synthetic and cropped real Korean recognition data.
2. Continue with AIHub 91 printed Korean region OCR.
3. Add page-level detection and structured OCR from AIHub 91 page data.
4. Patch measured weaknesses with targeted robustness datasets.

Historical data sources included:

- Jiwon-Kang synthetic rendered Korean OCR.
- AbdullahRian real cropped Korean OCR.
- AIHub 91 printed Hangul OCR data.
- KORIE receipt-field OCR benchmark data.

The project also produced benchmark notes, training plans, checkpoint-gating proposals, and progress reports. These are archived under `.md/`.

## Why It Was Abolished

The training strategy failed in a way that made the current project state unsafe to continue from.

The completed Stage 1 50K LoRA adapter was treated as useful because the training run finished, but later benchmark evaluation showed catastrophic output collapse on KORIE cropped receipt-field OCR:

```text
Exact match: 0.00%
CER: 2529.08%
WER: 345.65%
```

Observed failures included repeated junk fragments, unstable generation, and special/control-token output. This was not a normal OCR accuracy miss; it indicated that the checkpoint selection and validation process was fundamentally inadequate.

Earlier benchmark work showed that specialized PaddleOCR Korean recognition was much stronger on KORIE than the Granite/Docling fine-tuning path used here. The project concluded that continuing from the existing checkpoints and assumptions would likely compound bad results.

## Archive Layout

Historical markdown documentation retained for reference has been moved under:

```text
.md/
```

Notable archived files:

- `.md/0702.md`
- `.md/buckets.md`
- `.md/nonaihub_training_plan.md`
- `.md/train_instruction.md`
- `.md/progress/`
- `.md/metric/baseline_evaluation/`

The archived documents describe the old plan and failure analysis. They should be read as historical notes, not as current operating instructions.

## Restart Guidance

A new project should begin with a clean repository, explicit validation gates, and a smaller bounded benchmark-first workflow.

Minimum requirements for any restart:

- Establish frozen evaluation sets before training.
- Evaluate base models and every candidate checkpoint before promotion.
- Track CER, WER, exact match, blank rate, repetition rate, output length ratio, and special-token generation.
- Run bounded shards before long jobs.
- Keep dataset storage and model execution within the resource limits documented in the archived warning file.

Do not reuse the abolished checkpoints as trusted parents for new training.
