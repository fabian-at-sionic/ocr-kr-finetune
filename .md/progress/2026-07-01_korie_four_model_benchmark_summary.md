# KORIE OCR Benchmark Summary

Date: 2026-07-01

This report summarizes the KORIE OCR test benchmark run that compared four OCR/VLM paths. The detailed prediction artifacts and temporary KORIE files were deleted afterward at the user's request; this file keeps only the progress-level summary.

## Benchmark Setup

- Dataset: KORIE OCR test split
- Evaluation unit: cropped receipt field images
- Sample count: 1,786
- Metrics: exact match rate, character error rate (CER), word error rate (WER)
- All model runs completed with 0 inference errors.

## Results

| Rank by CER | Model | Samples | Errors | Exact Match | CER | WER |
|---:|---|---:|---:|---:|---:|---:|
| 1 | PaddleOCR GPU Korean PP-OCRv5 | 1,786 | 0 | 54.31% | 15.96% | 48.28% |
| 2 | PaddleOCR-VL-1.6-0.9B | 1,786 | 0 | 47.70% | 63.70% | 66.68% |
| 3 | IBM Granite/Docling 10k LoRA | 1,786 | 0 | 20.66% | 69.43% | 125.60% |
| 4 | Base Granite/Docling | 1,786 | 0 | 0.95% | 141.33% | 158.92% |

## Notes

- The first PaddleOCR run used the Korean PP-OCRv5 pipeline: `PP-OCRv5_server_det` plus `korean_PP-OCRv5_mobile_rec`, running on `gpu:0`.
- The larger Paddle run used `PaddleOCR-VL-1.6-0.9B` through `PaddleOCRVL(pipeline_version="v1.6", device="gpu:0")`.
- PaddleOCR-VL loaded successfully from the local `model/PaddlePaddle/PaddleOCR-VL-1.6` model directory during the benchmark.
- The IBM 10k run used the Granite/Docling base model with the 10k LoRA adapter that existed under `runs/train/stage1_lora_10k_smoke_textonly/final_adapter` before cleanup.
- Base Granite/Docling was evaluated without the LoRA adapter.

## Interpretation

The specialized PaddleOCR Korean recognizer was the strongest baseline on this cropped-field OCR benchmark. PaddleOCR-VL-1.6-0.9B was stronger than the current IBM 10k LoRA on exact match and WER, and slightly stronger on CER, but it produced many masked/hash-style outputs such as `#################`, which heavily hurt CER. The IBM 10k LoRA improved substantially over base Granite/Docling, but still showed repeated-token, blank-output, hallucination, and punctuation/spacing failure modes.

Base Granite/Docling was not usable as a strict cropped Korean receipt OCR recognizer without fine-tuning.

## Follow-Up Guidance

- Do not train on the KORIE test split.
- For the IBM model, train on full receipt pages or region-labeled receipt data with validation by CER/WER, not just cropped text smoke data.
- Add coverage for hard fields: merchant address, merchant name, item quantity/weight, discounts, totals, and mixed item rows.
- Track blank rate and repetition rate during validation, not only CER.
- For physical bounding boxes or markdown on original receipt pages, use a full-page receipt dataset with annotations. The KORIE OCR test split used here is already cropped and is not suitable for evaluating full-page detection quality.
