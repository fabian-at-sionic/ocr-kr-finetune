# PaddleOCR-VL 1.6 Baseline Evaluation

## Run Artifacts

- Manifest: `<PROJECT_ROOT>/dataset/hangul_recognition/baseline_testing/prepared/manifests/baseline_eval.jsonl`
- Predictions: `<PROJECT_ROOT>/runs/baseline/PaddlePaddle-PaddleOCR-VL-1.6/predictions_full_gpu_wrapped.jsonl`
- Metrics JSON: `<PROJECT_ROOT>/runs/baseline/PaddlePaddle-PaddleOCR-VL-1.6/metrics_full_gpu_wrapped.json`

## Overall Results

| Metric | Value |
| --- | ---: |
| Total samples | 1000 |
| Matched predictions | 1000 |
| Missing predictions | 0 |
| Exact match rate | 0.4410 |
| CER | 0.1337 |

## Dataset Breakdown

| Dataset | Samples | Matched | Missing | Exact match | CER |
| --- | ---: | ---: | ---: | ---: | ---: |
| Jiwon-Kang/OCR-Synthetic-Rendered-Korean-200K | 500 | 500 | 0 | 0.8260 | 0.0040 |
| AbdullahRian/Korean.OCR.Img.text.pair | 500 | 500 | 0 | 0.0560 | 0.2029 |

## Input Preprocessing

PaddleOCR-VL rejects extreme aspect-ratio inputs internally. For this run, very wide text strips were wrapped into shorter rows on a white canvas before inference. The original sample IDs and ground-truth text were kept unchanged for evaluation.

| Item | Count |
| --- | ---: |
| Prediction rows | 1000 |
| Padded images | 70 |
| Wrapped images | 70 |
| Runtime errors | 0 |
| Empty predictions | 17 |

## Interpretation Notes

- Exact match is strict: the normalized prediction must match the normalized reference exactly.
- CER is character error rate: lower is better; `0.0` means no character-level errors.
- AbdullahRian is substantially harder for PaddleOCR-VL in this setup because many samples are narrow subtitle-like strips, including extreme width-to-height ratios.
