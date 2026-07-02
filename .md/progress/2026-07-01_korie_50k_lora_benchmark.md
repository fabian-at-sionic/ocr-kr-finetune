# KORIE OCR Benchmark: Granite/Docling 50K LoRA

Date: 2026-07-01

## Result

The KORIE OCR test benchmark was rerun with the completed Stage 1 50K LoRA adapter.

Final result: the 50K LoRA is not usable on this KORIE cropped receipt-field OCR benchmark. It completed without inference errors, but produced degenerate repeated Latin fragments instead of Korean receipt text.

| Model | Samples | Errors | Exact Match | CER | WER | Blank Predictions | Repetition-Like Predictions |
|---|---:|---:|---:|---:|---:|---:|---:|
| IBM Granite/Docling 50K LoRA | 1,786 | 0 | 0.00% | 2529.08% | 345.65% | 0 | 81 |

Raw metric ratios:

```json
{
  "exact_rate": 0.0,
  "cer": 25.29077068400289,
  "wer": 3.456468424279583,
  "avg_latency_sec": 1.137493586353332
}
```

## Artifacts

- KORIE source repo: `<PROJECT_ROOT>/dataset/external/KORIE`
- OCR test zip: `<PROJECT_ROOT>/dataset/external/KORIE/downloads/korie_ocr_test.zip`
- OCR test manifest: `<PROJECT_ROOT>/dataset/external/KORIE/ocr_test_manifest.jsonl`
- Predictions: `<PROJECT_ROOT>/runs/benchmark/korie/granite_50k_lora_predictions.jsonl`
- Metrics: `<PROJECT_ROOT>/runs/benchmark/korie/granite_50k_lora_metrics.json`
- Runner: `<PROJECT_ROOT>/scripts/run_korie_granite_ocr_test.py`
- Adapter: `<PROJECT_ROOT>/runs/train/stage1_lora_50k_balanced_textonly_v3/final_adapter`

Storage impact:

- KORIE repo plus extracted OCR test data: 65M
- Benchmark output artifacts: 848K
- Total dataset storage after download/extraction: 79G

## Dataset Reconstruction

The KORIE GitHub repository was cloned from:

```text
https://github.com/MahmoudSalah/KORIE.git
```

The repository itself contains README plus sample images. The full OCR test split is linked from the README as a Google Drive file:

```text
OCR Dataset / Test / 1GtEzSUA2wTNfOujO67-JEZ_PLpJOdBhg
```

Downloaded file:

```bash
curl -L 'https://drive.google.com/uc?export=download&id=1GtEzSUA2wTNfOujO67-JEZ_PLpJOdBhg' \
  -o <PROJECT_ROOT>/dataset/external/KORIE/downloads/korie_ocr_test.zip
```

The archive contained 1,786 `.jpg` / `.txt` OCR crop pairs under `test/`, matching the prior KORIE benchmark sample count.

## Evaluation Command

```bash
<PROJECT_ROOT>/.venv-granite-eval/bin/python -u <PROJECT_ROOT>/scripts/run_korie_granite_ocr_test.py \
  --adapter <PROJECT_ROOT>/runs/train/stage1_lora_50k_balanced_textonly_v3/final_adapter \
  --batch-size 16 \
  --max-new-tokens 64 \
  --out <PROJECT_ROOT>/runs/benchmark/korie/granite_50k_lora_predictions.jsonl \
  --metrics-out <PROJECT_ROOT>/runs/benchmark/korie/granite_50k_lora_metrics.json \
  --manifest-out <PROJECT_ROOT>/dataset/external/KORIE/ocr_test_manifest.jsonl
```

Prompt:

```text
Extract all Korean/Hangul text from the image exactly as written.
```

## Important Inference Workaround

Initial adapter generation failed with Granite/Docling + PEFT because the 50K LoRA generated image/control special tokens such as `<image>` and `<fake_token_around_image>`. On the next generation step, the Idefics3 image-token mask no longer matched the available image features, producing this error:

```text
RuntimeError: Number of elements of source < number of ones in mask
```

The final runner suppresses these control tokens during decoding:

```text
100270  <image>
100339  <fake_token_around_image>
100264  <|start_of_role|>
100265  <|end_of_role|>
100338  <|unk|>
100352  <end_of_utterance>
```

EOS remained allowed. This made the benchmark complete with zero inference errors. The need for suppression is itself a failure signal: the adapter learned or exposed unstable generation behavior on receipt crops.

The runner also pads/upscales small OCR crops onto a white canvas because KORIE contains very small fields, with minimum side as low as 14 pixels.

## Qualitative Failure Pattern

Representative predictions:

| Sample | Target | Prediction Preview |
|---|---|---|
| `IMG00001_Item_Total_Price` | `38,000` | `amoto...iginaliginal...` |
| `IMG00001_MerchantPhoneNumber` | `0504-4819-8304` | `amotoamotoamoto...` |
| `IMG00002_MerchantAddress` | `충청북도 청주시 서원구 청남로 1853` | `amotoamotoamoto...` |
| `IMG00003_TransactionTime` | `21:30,` | `amoto...iginal...` |

The model mostly emitted repeated fragments like:

```text
amoto
iginal
applicant
danmark
imagiginal
```

It did not produce useful Korean receipt OCR output.

## Comparison With Previous KORIE Summary

Prior saved KORIE summary:

```text
<PROJECT_ROOT>/progress/2026-07-01_korie_four_model_benchmark_summary.md
```

Previous results:

| Model | Samples | Errors | Exact Match | CER | WER |
|---|---:|---:|---:|---:|---:|
| PaddleOCR GPU Korean PP-OCRv5 | 1,786 | 0 | 54.31% | 15.96% | 48.28% |
| PaddleOCR-VL-1.6-0.9B | 1,786 | 0 | 47.70% | 63.70% | 66.68% |
| IBM Granite/Docling 10K LoRA | 1,786 | 0 | 20.66% | 69.43% | 125.60% |
| Base Granite/Docling | 1,786 | 0 | 0.95% | 141.33% | 158.92% |
| IBM Granite/Docling 50K LoRA | 1,786 | 0 | 0.00% | 2529.08% | 345.65% |

The 50K LoRA is much worse than the prior 10K LoRA on KORIE. This aligns with the abnormal high-loss tail observed during 50K training, where logged loss rose above 140 late in the run.

## Resource Notes

Preflight before evaluation:

- GPU had 0 MiB in use and no running GPU processes.
- System memory was comfortably below the 267.7 GB effective ceiling.
- Dataset storage remained far below the 700 GB cap.

During the run:

- Peak observed VRAM: 105,106 MiB / 275,040 MiB.
- GPU utilization was commonly 99-100% during active batches.
- System memory stayed below 100 GiB used in monitoring snapshots.

After completion:

- GPU memory released to 0 MiB.

## Interpretation

This benchmark should not be read as a normal 50K improvement over 10K. The 50K adapter appears degraded for inference on cropped receipt fields. Likely contributing factors:

- The 50K run was text-only LoRA on recognition data, not receipt-specific OCR.
- Training loss became extremely high late in the run.
- The adapter generated multimodal/control special tokens unless explicitly suppressed.
- KORIE has many tiny receipt-field crops and numeric/merchant fields unlike the 50K training mixture.

Recommendation: do not use the 50K v3 adapter as the main continuation point without further investigation. Prefer evaluating retained checkpoints if available, rebuilding a cleaner Stage 1 adapter with validation, or training a receipt/region-specific adapter with an internal validation set and early stopping.
