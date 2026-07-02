# IBM Granite Docling 258M Baseline Evaluation

## Run Artifacts

- Manifest: `<PROJECT_ROOT>/dataset/hangul_recognition/baseline_testing/prepared/manifests/baseline_eval.jsonl`
- Predictions: `<PROJECT_ROOT>/runs/baseline/ibm-granite-granite-docling-258M/predictions_full.jsonl`
- Metrics JSON: `<PROJECT_ROOT>/runs/baseline/ibm-granite-granite-docling-258M/metrics_full.json`

## Overall Results

| Metric | Value |
| --- | ---: |
| Total samples | 1000 |
| Matched predictions | 1000 |
| Missing predictions | 0 |
| Exact match rate | 0.0000 |
| CER | 1.9703 |

## Dataset Breakdown

| Dataset | Samples | Matched | Missing | Exact match | CER |
| --- | ---: | ---: | ---: | ---: | ---: |
| Jiwon-Kang/OCR-Synthetic-Rendered-Korean-200K | 500 | 500 | 0 | 0.0000 | 0.8958 |
| AbdullahRian/Korean.OCR.Img.text.pair | 500 | 500 | 0 | 0.0000 | 2.5434 |

## Inference Setup

Granite Docling was run with the Docling-family baseline runner on GPU through `.venv-granite-eval`. The prompt was `Convert this page to docling.`, and visible OCR text was extracted from generated DocTags by stripping tags before metric evaluation.

## Interpretation Notes

- Exact match is strict: the normalized prediction must match the normalized reference exactly.
- CER is character error rate: lower is better; `0.0` means no character-level errors.
- This model produced many long repeated-token outputs on the harder subtitle-like samples, which heavily increased CER.
