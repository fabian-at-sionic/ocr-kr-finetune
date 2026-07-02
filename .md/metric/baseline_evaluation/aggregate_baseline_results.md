# Baseline Evaluation Aggregate Results

## Dataset

- Manifest: `<PROJECT_ROOT>/dataset/hangul_recognition/baseline_testing/prepared/manifests/baseline_eval.jsonl`
- Total samples: 1000
- Dataset mix: 500 `Jiwon-Kang/OCR-Synthetic-Rendered-Korean-200K` + 500 `AbdullahRian/Korean.OCR.Img.text.pair`

## Overall Comparison

| Rank | Model | Samples | Exact match | CER |
| ---: | --- | ---: | ---: | ---: |
| 1 | `PaddlePaddle/PaddleOCR-VL-1.6` | 1000 | 0.4410 | 0.1337 |
| 2 | `ibm-granite/granite-docling-258M` | 1000 | 0.0000 | 1.9703 |
| 3 | `docling-project/SmolDocling-256M-preview` | 1000 | 0.0000 | 3.3308 |

## Dataset-Level CER

| Model | Jiwon CER | AbdullahRian CER |
| --- | ---: | ---: |
| `PaddlePaddle/PaddleOCR-VL-1.6` | 0.0040 | 0.2029 |
| `ibm-granite/granite-docling-258M` | 0.8958 | 2.5434 |
| `docling-project/SmolDocling-256M-preview` | 2.7908 | 3.6188 |

## Short Takeaway

PaddleOCR-VL is the strongest baseline by a large margin on this Korean OCR benchmark. Granite Docling is the stronger non-Chinese baseline among the two Docling-family models tested, but both Docling-family models need Korean OCR fine-tuning before they can plausibly compete with PaddleOCR-VL.

## Per-Model Reports

- `metric/baseline_evaluation/paddleocr_vl_1_6_baseline.md`
- `metric/baseline_evaluation/ibm_granite_docling_258m_baseline.md`
- `metric/baseline_evaluation/smoldocling_256m_baseline.md`
