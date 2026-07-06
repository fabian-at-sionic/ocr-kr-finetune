# KDoc OCRBench V2 - SmolDocling 256M

- Dataset: `/workspace/ocr-bench/dataset/KDoc-OCRBench-V2`
- Candidate outputs: `/workspace/ocr-bench/dataset/KDoc-OCRBench-V2/smol_docling_256m_full_cap2048`
- Model: `model/docling-project/SmolDocling-256M-preview`
- Prompt: `Convert this page to docling.`
- PDFs expected: 849
- Missing markdown outputs: 0
- Failed test details: `failed_tests.jsonl`
- Inference settings: `batch_size=32`, `max_new_tokens=2048`, `attn_implementation=eager`
- Note: an initial 8192-token run was much slower because SmolDocling-256M repeatedly looped on many Korean pages. On the first 16 PDFs, the 2048-token cap matched the 8192-token subset scores, so the full run used 2048 to avoid wasting time on repeated tails.
- Note: 2 PDFs generated raw doctags but failed `docling_core` markdown conversion; fallback markdown was created from stripped doctags so all 849 PDFs have outputs.

## Benchmark Table Row

| Model | Baseline | Header/Footer | Long Text | Table | Overall |
|---|---:|---:|---:|---:|---:|
| SmolDocling 256M | 72.7 | 97.9 | 2.3 | 1.7 | 43.6 |

Column mapping: **Baseline** = auto-generated baseline tests, **Header/Footer** = `header_footer_tests.jsonl` (ABSENT), **Long Text** = `text_present.jsonl` (PRESENT), **Table** = `tables.jsonl`.

## Interpretation

SmolDocling 256M is not competitive on KDoc OCRBench V2 for Korean document OCR. It often emits non-empty output, so the baseline score is moderate, but the actual content recovery is very weak: 2.29% on long-text presence and 1.71% on table tests.

The high Header/Footer score should be read carefully because it is an absence test. A model can pass it by omitting or garbling page chrome, even while missing the main body text and table structure.

## Scores

| Suite | Passed | Total | Pass rate |
|---|---:|---:|---:|
| baseline | 617 | 849 | 72.67% |
| header_footer_tests | 775 | 792 | 97.85% |
| text_present | 144 | 6290 | 2.29% |
| tables | 841 | 49115 | 1.71% |

**Overall (mean of suite pass rates): 43.63%**

## By Document Category

| Suite | Category | Passed | Total | Pass rate |
|---|---|---:|---:|---:|
| baseline | Manuals | 156 | 216 | 72.22% |
| baseline | Notices | 85 | 112 | 75.89% |
| baseline | Reports | 157 | 238 | 65.97% |
| baseline | Statistics | 219 | 283 | 77.39% |
| header_footer_tests | Manuals | 199 | 202 | 98.51% |
| header_footer_tests | Notices | 82 | 85 | 96.47% |
| header_footer_tests | Reports | 253 | 257 | 98.44% |
| header_footer_tests | Statistics | 241 | 248 | 97.18% |
| text_present | Manuals | 32 | 1836 | 1.74% |
| text_present | Notices | 9 | 1489 | 0.60% |
| text_present | Reports | 32 | 1539 | 2.08% |
| text_present | Statistics | 71 | 1426 | 4.98% |
| tables | Manuals | 15 | 6430 | 0.23% |
| tables | Notices | 0 | 5275 | 0.00% |
| tables | Reports | 105 | 12714 | 0.83% |
| tables | Statistics | 721 | 24696 | 2.92% |
