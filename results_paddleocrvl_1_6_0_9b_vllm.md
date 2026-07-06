# KDoc OCRBench V2 - PPStructureV3 + PaddleOCR-VL-1.6-0.9B vLLM

- Dataset: `/workspace/ocr-bench/dataset/KDoc-OCRBench-V2`
- Candidate outputs: `/workspace/ocr-bench/dataset/KDoc-OCRBench-V2/paddleocrvl_1_6_0_9b_vllm`
- Model: `model/PaddlePaddle/PaddleOCR-VL-1.6`
- Prompt: `PaddleOCRVL v1.6 with PaddleOCR-VL-1.6-0.9B via vLLM server`
- PDFs expected: 849
- Missing markdown outputs: 0
- Failed test details: `failed_tests_paddleocrvl_1_6_0_9b_vllm.jsonl`

## Scores

| Suite | Passed | Total | Pass rate |
|---|---:|---:|---:|
| baseline | 688 | 849 | 81.04% |
| header_footer_tests | 767 | 792 | 96.84% |
| text_present | 2659 | 6290 | 42.27% |
| tables | 13526 | 49115 | 27.54% |

**Overall (mean of suite pass rates): 61.92%**

## By Document Category

| Suite | Category | Passed | Total | Pass rate |
|---|---|---:|---:|---:|
| baseline | Manuals | 175 | 216 | 81.02% |
| baseline | Notices | 80 | 112 | 71.43% |
| baseline | Reports | 206 | 238 | 86.55% |
| baseline | Statistics | 227 | 283 | 80.21% |
| header_footer_tests | Manuals | 198 | 202 | 98.02% |
| header_footer_tests | Notices | 82 | 85 | 96.47% |
| header_footer_tests | Reports | 248 | 257 | 96.50% |
| header_footer_tests | Statistics | 239 | 248 | 96.37% |
| text_present | Manuals | 801 | 1836 | 43.63% |
| text_present | Notices | 591 | 1489 | 39.69% |
| text_present | Reports | 677 | 1539 | 43.99% |
| text_present | Statistics | 590 | 1426 | 41.37% |
| tables | Manuals | 1354 | 6430 | 21.06% |
| tables | Notices | 837 | 5275 | 15.87% |
| tables | Reports | 4697 | 12714 | 36.94% |
| tables | Statistics | 6638 | 24696 | 26.88% |
