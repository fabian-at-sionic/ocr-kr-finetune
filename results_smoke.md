# KDoc OCRBench V2 - SmolDocling 256M

- Dataset: `/workspace/ocr-bench/dataset/KDoc-OCRBench-V2`
- Candidate outputs: `/workspace/ocr-bench/dataset/KDoc-OCRBench-V2/smol_docling_256m_batch_smoke_leftpad`
- Model: `model/docling-project/SmolDocling-256M-preview`
- Prompt: `Convert this page to docling.`
- PDFs expected: 849
- Missing markdown outputs: 841
- Failed test details: `failed_tests_smoke.jsonl`

## Scores

| Suite | Passed | Total | Pass rate |
|---|---:|---:|---:|
| baseline | 8 | 849 | 0.94% |
| header_footer_tests | 1 | 792 | 0.13% |
| text_present | 0 | 6290 | 0.00% |
| tables | 0 | 49115 | 0.00% |

**Overall (mean of suite pass rates): 0.27%**

## By Document Category

| Suite | Category | Passed | Total | Pass rate |
|---|---|---:|---:|---:|
| baseline | Manuals | 0 | 216 | 0.00% |
| baseline | Notices | 3 | 112 | 2.68% |
| baseline | Reports | 5 | 238 | 2.10% |
| baseline | Statistics | 0 | 283 | 0.00% |
| header_footer_tests | Manuals | 0 | 202 | 0.00% |
| header_footer_tests | Notices | 1 | 85 | 1.18% |
| header_footer_tests | Reports | 0 | 257 | 0.00% |
| header_footer_tests | Statistics | 0 | 248 | 0.00% |
| text_present | Manuals | 0 | 1836 | 0.00% |
| text_present | Notices | 0 | 1489 | 0.00% |
| text_present | Reports | 0 | 1539 | 0.00% |
| text_present | Statistics | 0 | 1426 | 0.00% |
| tables | Manuals | 0 | 6430 | 0.00% |
| tables | Notices | 0 | 5275 | 0.00% |
| tables | Reports | 0 | 12714 | 0.00% |
| tables | Statistics | 0 | 24696 | 0.00% |
