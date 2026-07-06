# Granite Docling 258M Overfit26 LoRA Phase2 cap8192 dpi100 b16

- Dataset: `/workspace/ocr-bench/dataset/KDoc-OCRBench-V2`
- Candidate outputs: `/workspace/ocr-bench/dataset/KDoc-OCRBench-V2/granite_docling_258m_overfit26_lora_phase2_cap8192_dpi100_b16`
- Model: `granite-docling-258M+overfit26-lora`
- Prompt: `docling_core_doctags_strict`
- PDFs expected: 849
- Missing markdown outputs: 27
- Failed test details: `failed_tests_granite_docling_258m_overfit26_lora_phase2_cap8192_dpi100_b16.jsonl`

## Scores

| Suite | Passed | Total | Pass rate |
|---|---:|---:|---:|
| baseline | 529 | 849 | 62.31% |
| header_footer_tests | 656 | 792 | 82.83% |
| text_present | 321 | 6290 | 5.10% |
| tables | 544 | 49115 | 1.11% |

**Overall (mean of suite pass rates): 37.84%**

## By Document Category

| Suite | Category | Passed | Total | Pass rate |
|---|---|---:|---:|---:|
| baseline | Manuals | 143 | 216 | 66.20% |
| baseline | Notices | 67 | 112 | 59.82% |
| baseline | Reports | 125 | 238 | 52.52% |
| baseline | Statistics | 194 | 283 | 68.55% |
| header_footer_tests | Manuals | 172 | 202 | 85.15% |
| header_footer_tests | Notices | 75 | 85 | 88.24% |
| header_footer_tests | Reports | 216 | 257 | 84.05% |
| header_footer_tests | Statistics | 193 | 248 | 77.82% |
| text_present | Manuals | 89 | 1836 | 4.85% |
| text_present | Notices | 40 | 1489 | 2.69% |
| text_present | Reports | 93 | 1539 | 6.04% |
| text_present | Statistics | 99 | 1426 | 6.94% |
| tables | Manuals | 13 | 6430 | 0.20% |
| tables | Notices | 6 | 5275 | 0.11% |
| tables | Reports | 77 | 12714 | 0.61% |
| tables | Statistics | 448 | 24696 | 1.81% |
