# Granite Docling 258M Base Phase2 cap8192 dpi100 b16

- Dataset: `/workspace/ocr-bench/dataset/KDoc-OCRBench-V2`
- Candidate outputs: `/workspace/ocr-bench/dataset/KDoc-OCRBench-V2/granite_docling_258m_base_phase2_cap8192_dpi100_b16`
- Model: `granite-docling-258M-base`
- Prompt: `docling_core_doctags_strict`
- PDFs expected: 849
- Missing markdown outputs: 0
- Failed test details: `failed_tests_granite_docling_258m_base_phase2_cap8192_dpi100_b16.jsonl`

## Scores

| Suite | Passed | Total | Pass rate |
|---|---:|---:|---:|
| baseline | 736 | 849 | 86.69% |
| header_footer_tests | 745 | 792 | 94.07% |
| text_present | 1158 | 6290 | 18.41% |
| tables | 1090 | 49115 | 2.22% |

**Overall (mean of suite pass rates): 50.35%**

## By Document Category

| Suite | Category | Passed | Total | Pass rate |
|---|---|---:|---:|---:|
| baseline | Manuals | 191 | 216 | 88.43% |
| baseline | Notices | 91 | 112 | 81.25% |
| baseline | Reports | 209 | 238 | 87.82% |
| baseline | Statistics | 245 | 283 | 86.57% |
| header_footer_tests | Manuals | 197 | 202 | 97.52% |
| header_footer_tests | Notices | 77 | 85 | 90.59% |
| header_footer_tests | Reports | 242 | 257 | 94.16% |
| header_footer_tests | Statistics | 229 | 248 | 92.34% |
| text_present | Manuals | 355 | 1836 | 19.34% |
| text_present | Notices | 183 | 1489 | 12.29% |
| text_present | Reports | 305 | 1539 | 19.82% |
| text_present | Statistics | 315 | 1426 | 22.09% |
| tables | Manuals | 163 | 6430 | 2.53% |
| tables | Notices | 155 | 5275 | 2.94% |
| tables | Reports | 499 | 12714 | 3.92% |
| tables | Statistics | 273 | 24696 | 1.11% |
