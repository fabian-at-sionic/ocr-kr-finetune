# KDoc OCRBench V2 - Granite Docling 258M Overfit26 LoRA TF DPI100 512

- Dataset: `/workspace/ocr-bench/dataset/KDoc-OCRBench-V2`
- Candidate outputs: `/workspace/ocr-bench/dataset/KDoc-OCRBench-V2/granite_docling_258m_overfit26_lora_tf_dpi100_512`
- Model: `model/ibm-granite/granite-docling-258M+runs/overfit_26/adapter`
- Prompt: `Convert this page to docling.`
- PDFs expected: 849
- Missing markdown outputs: 0
- Failed test details: `failed_tests_granite_docling_258m_overfit26_lora_tf_dpi100_512.jsonl`

## Scores

| Suite | Passed | Total | Pass rate |
|---|---:|---:|---:|
| baseline | 689 | 849 | 81.15% |
| header_footer_tests | 730 | 792 | 92.17% |
| text_present | 219 | 6290 | 3.48% |
| tables | 0 | 49115 | 0.00% |

**Overall (mean of suite pass rates): 44.20%**

## By Document Category

| Suite | Category | Passed | Total | Pass rate |
|---|---|---:|---:|---:|
| baseline | Manuals | 182 | 216 | 84.26% |
| baseline | Notices | 96 | 112 | 85.71% |
| baseline | Reports | 183 | 238 | 76.89% |
| baseline | Statistics | 228 | 283 | 80.57% |
| header_footer_tests | Manuals | 194 | 202 | 96.04% |
| header_footer_tests | Notices | 80 | 85 | 94.12% |
| header_footer_tests | Reports | 240 | 257 | 93.39% |
| header_footer_tests | Statistics | 216 | 248 | 87.10% |
| text_present | Manuals | 55 | 1836 | 3.00% |
| text_present | Notices | 32 | 1489 | 2.15% |
| text_present | Reports | 62 | 1539 | 4.03% |
| text_present | Statistics | 70 | 1426 | 4.91% |
| tables | Manuals | 0 | 6430 | 0.00% |
| tables | Notices | 0 | 5275 | 0.00% |
| tables | Reports | 0 | 12714 | 0.00% |
| tables | Statistics | 0 | 24696 | 0.00% |
