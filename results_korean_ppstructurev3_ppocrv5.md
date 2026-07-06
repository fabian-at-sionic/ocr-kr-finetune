# KDoc OCRBench V2 - Korean PPStructureV3 PP-OCRv5 mobile rec

- Dataset: `/workspace/ocr-bench/dataset/KDoc-OCRBench-V2`
- Candidate outputs: `/workspace/ocr-bench/dataset/KDoc-OCRBench-V2/korean_ppstructurev3_ppocrv5`
- Model: `model/PaddlePaddle/korean_PP-OCRv5_mobile_rec`
- Prompt: `PPStructureV3 with korean_PP-OCRv5_mobile_rec`
- PDFs expected: 849
- Missing markdown outputs: 0
- Failed test details: `failed_tests_korean_ppstructurev3_ppocrv5.jsonl`

## Scores

| Suite | Passed | Total | Pass rate |
|---|---:|---:|---:|
| baseline | 849 | 849 | 100.00% |
| header_footer_tests | 767 | 792 | 96.84% |
| text_present | 2221 | 6290 | 35.31% |
| tables | 9411 | 49115 | 19.16% |

**Overall (mean of suite pass rates): 62.83%**

## By Document Category

| Suite | Category | Passed | Total | Pass rate |
|---|---|---:|---:|---:|
| baseline | Manuals | 216 | 216 | 100.00% |
| baseline | Notices | 112 | 112 | 100.00% |
| baseline | Reports | 238 | 238 | 100.00% |
| baseline | Statistics | 283 | 283 | 100.00% |
| header_footer_tests | Manuals | 201 | 202 | 99.50% |
| header_footer_tests | Notices | 82 | 85 | 96.47% |
| header_footer_tests | Reports | 245 | 257 | 95.33% |
| header_footer_tests | Statistics | 239 | 248 | 96.37% |
| text_present | Manuals | 657 | 1836 | 35.78% |
| text_present | Notices | 504 | 1489 | 33.85% |
| text_present | Reports | 529 | 1539 | 34.37% |
| text_present | Statistics | 531 | 1426 | 37.24% |
| tables | Manuals | 772 | 6430 | 12.01% |
| tables | Notices | 500 | 5275 | 9.48% |
| tables | Reports | 3032 | 12714 | 23.85% |
| tables | Statistics | 5107 | 24696 | 20.68% |
