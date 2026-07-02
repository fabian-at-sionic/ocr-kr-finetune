# TODO.md

> Resource warning: before executing tasks from this document, read `warning.md`. The project is constrained to a single container with an effective 267.7 GB memory/GPU-resource ceiling and a 700 GB dataset-storage cap under `<PROJECT_ROOT>/dataset`; avoid unbounded downloads, extraction, tiling, concurrent VLM inference, or training jobs that may exceed these limits.



## 2026-07-01 Training Strategy Correction

A completed Stage 1 50K LoRA adapter failed catastrophically on the KORIE receipt-field OCR benchmark with repeated-token generation (`0.00%` exact match, `2529.08%` CER, `345.65%` WER). This changes the operating plan.

The project now uses checkpoint-gated training:

```text
small run or checkpoint -> bounded eval gate -> promote only if generation is sane -> continue training
```

Do not treat longer training, lower local loss, or a completed adapter as progress unless it improves bounded evaluation and avoids repetition/control-token generation. Any future SOTA claim must be backed by checkpoint-selected results, not by final checkpoint by default.

## Step 1: OCR Model Research and Benchmark Setup (Day 1-2)

First, define the target clearly: this is **not primarily medical OCR** and it is **not general VLM fine-tuning**. The core target is **Hangul-focused OCR detection and recognition**. Medical, biomedical, and health-check documents are high-priority application domains, but the main research question is: "Can a non-Chinese OCR/document model be fine-tuned to better detect and recognize Hangul text, narrowing the gap with famous Chinese OCR systems such as PaddleOCR-VL?"

- **Core objective:** The primary objective is to reliably detect text regions that contain Hangul in document images, then accurately recover the Hangul strings. Evaluation should be split into (1) Hangul-containing text-region detection, (2) Hangul OCR recognition, and (3) mixed Korean/English/number/table document parsing. Medical documents should be treated as one difficult domain slice, not the whole project.
- **Why the target must be OCR-first and lineage-clean:** `google/gemma-3-12b-it` is a general instruction-tuned VLM, not an OCR model. However, OCR branding alone is not enough. `lightonai/LightOnOCR-2-1B-base` looks attractive, but its config uses `Qwen3ForCausalLM` and `model_type: qwen3`, so it fails the current model-selection principle.
- **Pre-training vs instruction tuning vs fine-tuning:** Pre-training is the stage where a foundation model is originally created from massive web, text, image, and image-text data. We are not doing that. Instruction tuning teaches a model to follow prompts and output schemas. Fine-tuning is our stage: we adapt an OCR/document model to Hangul OCR, table/form extraction, and strict markdown/JSON output formats.
- **Why this is fine-tuning, not pre-training:** The goal is not to teach Korean from zero. The goal is to improve visual recognition of Hangul in documents, localization of Hangul-containing regions, and OCR output behavior. That is task fine-tuning. Pre-training would only make sense if the model had no useful visual-text grounding or no ability to represent Hangul at all.
- **Model-selection principle:** The fine-tuning target must be a non-Chinese OCR/document model. Do not exclude a model only because it supports Chinese. Exclude it from fine-tuning if its foundation/base lineage or required inference stack is Chinese-origin or Chinese-controlled, such as `Qwen`, `PaddlePaddle`, `PaddleOCR`, `ERNIE`, `DeepSeek`, `GLM`, `Baidu`, or `Zhipu`. Always inspect the actual model config and base-model tags, not just the model name.
- **OCR-focused model candidates and decision:**
  - **Selected: `ibm-granite/granite-docling-258M`** - IBM document-conversion/OCR model with full-page OCR, layout, table, DocTags, and markdown-style outputs. Its config uses Idefics3 plus a Llama/Granite text stack and does not show Qwen/Paddle/ERNIE. This is the safest rule-compliant fine-tuning target found so far.
  - **Baseline/control: `docling-project/SmolDocling-256M-preview`** - Predecessor to Granite Docling. It is also an OCR/document-conversion model using Idefics3/Llama-family config and SmolVLM base lineage. Run it as-is to measure improvement.
  - **Optional recognition-only baseline: `microsoft/trocr-large-printed`** - Useful for cropped text-line recognition, but not a full-page document OCR/layout model.
  - **Fallback only: `google/gemma-3-12b-it`** - General instruction-tuned VLM. Use only if OCR/document targets fail technically; do not make it the main thesis.
  - **Excluded target: `lightonai/LightOnOCR-2-1B-base`** - Strong OCR model, but its config shows `Qwen3ForCausalLM` / `qwen3`; excluded by lineage rule.
  - **Excluded target: `lightonai/LightOnOCR-2-1B-bbox-base`** - Exclude unless a separate config audit proves it is not Qwen-based.
  - **Excluded target: `allenai/olmOCR-2-7B-1025`** - Strong OCR model, but the model card states it is fine-tuned from `Qwen2.5-VL-7B-Instruct`.
  - **Excluded targets: `nanonets/Nanonets-OCR2-3B`, `datalab-to/chandra-ocr-2`, `datalab-to/surya-ocr-2`, `deepseek-ai/DeepSeek-OCR`, `zai-org/GLM-OCR`, `baidu/Unlimited-OCR`** - OCR models, but they fail the Qwen/DeepSeek/GLM/Baidu lineage or stack rule.
  - **Comparison only: `PaddlePaddle/PaddleOCR-VL-1.6`** - Chinese/top OCR comparison ceiling. Do not train it and do not use its predictions as pseudo-labels.
- **Download targets:** Download `ibm-granite/granite-docling-258M` as the fine-tuning target, `docling-project/SmolDocling-256M-preview` as the non-Chinese baseline/control, and `PaddlePaddle/PaddleOCR-VL-1.6` as the Chinese/top OCR comparison ceiling.
- **Fine-tuning path:** Start with supervised LoRA/QLoRA on `ibm-granite/granite-docling-258M`, but only promote checkpoints that pass bounded evaluation gates. Use page-level DocTags/markdown outputs for full-page OCR and bbox-guided prompts for localization/region OCR if available. Consider full fine-tuning only after LoRA proves improved Hangul CER, layout stability, low repetition rate, sane generated length, and valid output formatting.
- **Benchmark definition:** Prioritize Hangul-focused benchmarks over generic OCR benchmarks. Minimum benchmark set: (1) synthetic Hangul document benchmark, (2) real-world Korean document benchmark, and (3) medical/biomedical/health-check/table domain slice.

## Step 2: Build a Difficult Hangul-Centered Dataset Pipeline (Day 3-5)

The main performance gain will come from making Hangul genuinely difficult in the training and evaluation data. Medical documents are an important slice, but the central axis is Hangul detection and recognition.

- **Collect and generate Hangul data:** Prioritize AIHUB, public documents, forms, receipts, invoices, health-check forms, insurance forms, and other document types that contain Korean. Tag medical records, health-check documents, and biomedical documents as a domain-stress subset.
- **Create OCR-specific training samples:** Build examples for page-level OCR, region-level OCR, table/form extraction, and bbox-plus-transcript output. Prompts should stay simple and consistent so the model learns OCR behavior, not arbitrary chat behavior.
- **Generate synthetic Hangul documents:** Include diverse Korean fonts, width/letter-spacing variation, blur, scan noise, rotation, low resolution, small text inside table cells, and mixed Korean/English/number strings. Prioritize tables, forms, and health-check-style documents that contain Hangul text.
- **Separate label formats:** Keep labels separate for detection boxes/segmentation, recognition transcripts, and structured markdown/HTML/JSON/DocTags output. This lets the OCR target and baselines train or evaluate on the same data in their appropriate formats.
- **Preprocess and format data:** Standardize rendering DPI, image resolution, crop strategy, prompts, and output format. Tag ground-truth text by script so Hangul CER/WER, Hangul-only CER, and mixed-script CER can all be computed.

## Step 3: Fine-Tune and Record the Process (Day 6-8)

Train the OCR/document model and record every meaningful issue. This process will become the main technical content for the deep-research presentation.

- **Fine-tune the model:** Task fine-tune `ibm-granite/granite-docling-258M` on Hangul OCR data using checkpoint-gated LoRA/QLoRA. Do not run long jobs without intermediate checkpoints and eval gates. Decide whether full fine-tuning is worth it only after data, output formats, decoding, and checkpoint selection are stable.
- **Do not pre-train:** Do not attempt foundation pre-training. The goal is to preserve the OCR/document model's page-reading ability while improving Hangul recognition, localization, and strict output-format adherence.
- **Record intermediate steps:** Track loss curves, CER/WER changes, detection F1/IoU, prompt templates, label formats, data-ratio changes, hallucination cases, repetition loops, generated length, control-token generation, checkpoint promotion/rejection, and output-format failures.
- **Escalation criteria:** Stop and ask for review if loss diverges, validation CER/WER regresses, Hangul output collapses, repeated-token generation appears, generated length runs to max tokens, control/image tokens appear in text output, detection boxes become unstable, or the model repeatedly breaks the JSON/markdown/DocTags schema.

## Step 4: Evaluation and Presentation Preparation (Day 9-10)

Use the final results to prove the improvement on Hangul-centered OCR tasks.

- **Final benchmark evaluation:** Evaluate the fine-tuned `ibm-granite/granite-docling-258M` on the Hangul-centered benchmarks from Step 1.
- **Primary metrics:** Use Hangul-containing text-region detection F1/IoU, Hangul CER/WER, mixed-script CER, table-cell OCR accuracy, document-structure score, instruction/output-format adherence rate, latency, and GPU memory.
- **Comparison method:** Label `docling-project/SmolDocling-256M-preview` as the non-Chinese OCR/document baseline and `PaddlePaddle/PaddleOCR-VL-1.6` as the Chinese/top OCR comparison ceiling. Never use PaddleOCR-VL outputs as training data or pseudo-labels.

## Hermes Agent: AI-HUB Authorization Request Workflow


- **Goal:** Prepare and submit authorization requests for AI-HUB datasets needed for Hangul OCR research.
- **URL policy:** Do not store explicit AI-HUB dataset URLs in this repository. Use placeholders such as `<AIHUB_DATASET_PAGE>` and let the human operator provide the active browser page or URL at runtime.
- **Human checkpoints:** Hermes must pause before login, identity verification, terms acceptance, personal-information submission, institutional-information submission, and final request submission.
- **Request purpose:** Use this research purpose consistently: fine-tuning and evaluating a non-Chinese OCR/document model for Hangul text-region detection, Hangul OCR recognition, and mixed Korean/English/number/table document parsing.
- **Data handling:** Do not upload downloaded AI-HUB data to public repositories. Store raw data under `dataset/aihub/raw/` or another private local path, and keep access logs/permission notes under `dataset/aihub/permissions/`.
- **Outputs expected from Hermes:** completed application draft, list of requested datasets, required documents checklist, missing-information report, final submission confirmation metadata, and download/access instructions after approval.
