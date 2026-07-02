# MODEL.md

> Resource warning: before executing tasks from this document, read `warning.md`. The project is constrained to a single container with an effective 267.7 GB memory/GPU-resource ceiling and a 700 GB dataset-storage cap under `<PROJECT_ROOT>/dataset`; avoid unbounded downloads, extraction, tiling, concurrent VLM inference, or training jobs that may exceed these limits.


This file defines the models to download for the Korean/Hangul OCR benchmark and fine-tuning run.

## Project Thesis

The project is about **fine-tuning non-Chinese OCR/document models so they can better detect and recognize Hangul text**, then comparing them against famous Chinese OCR systems such as PaddleOCR-VL.

The fine-tuning target should be OCR-first or document-conversion-first, but it must also pass the lineage audit. A model is not acceptable just because the publisher is non-Chinese or the model card says OCR.

## Key Training Terms

- **Pre-training:** the large foundation-model creation stage. A model learns broad language, vision, and image-text representations from massive general datasets. We are not doing this.
- **Instruction tuning:** post-training on prompt/response examples so a model follows instructions and output schemas.
- **Task fine-tuning:** our project stage. We start from a rule-compliant OCR/document model and adapt it to Hangul text-region detection, Hangul recognition, table/form extraction, and strict markdown/JSON outputs.

This is fine-tuning, not pre-training. The goal is not to teach Korean from zero. The goal is to improve visual OCR behavior for Hangul in document images.

## Model Roles

- **Fine-tuning target:** the non-Chinese OCR/document model we adapt on Korean/Hangul OCR data.
- **Baseline/control:** a non-Chinese OCR/document model run as-is to measure whether our fine-tuning improves performance.
- **Chinese/top comparison ceiling:** a strong Chinese OCR model run as-is. This is not a training target.
- **Excluded OCR models:** OCR models that look attractive but fail the lineage or stack audit.

## Non-Chinese Lineage Rule

Do not exclude a model merely because it supports Chinese (`zh`) or multilingual OCR. Multilingual capability is allowed.

Exclude a model from fine-tuning if its foundation/base lineage or required model stack is Chinese-origin or Chinese-controlled, for example `Qwen`, `PaddlePaddle`, `PaddleOCR`, `ERNIE`, `DeepSeek`, `GLM`, `Baidu`, or `Zhipu`.

The audit must inspect the model card, `config.json`, `text_config`, `vision_config`, `base_model` tags, required inference package, and paper/model acknowledgements when available.

## OCR-Focused Model Scout After Lineage Audit

| Candidate | Size | OCR/document focus | Lineage / stack audit | Decision |
|---|---:|---:|---|---|
| `ibm-granite/granite-docling-258M` | 258M | yes, document conversion/OCR/layout/table | IBM model; config uses `Idefics3ForConditionalGeneration`; text stack is `LlamaForCausalLM` / Granite 165M; vision encoder is `siglip2-base-patch16-512`. No Qwen/Paddle/ERNIE stack found in config. | **Use as main fine-tuning target** |
| `docling-project/SmolDocling-256M-preview` | 256M | yes, document conversion/OCR/layout/table | Docling/IBM-HF model; base model is `HuggingFaceTB/SmolVLM-256M-Instruct`; config uses Idefics3/Llama-family text stack. Successor is Granite Docling. | baseline/control |
| `microsoft/trocr-large-printed` | large OCR recognizer | recognition only | Transformer OCR recognizer, useful for cropped text-line recognition; not full document layout/OCR. No Qwen/Paddle stack in HF tags. | optional recognition-only baseline |
| `google/gemma-3-12b-it` | 12B | no, general VLM | Non-Chinese general VLM, but not OCR-first. | fallback only, not main thesis |
| `lightonai/LightOnOCR-2-1B-base` | 1B | yes | Fails audit: `config.json` has `text_config.architectures: Qwen3ForCausalLM` and `text_config.model_type: qwen3`. | excluded from fine-tuning target |
| `lightonai/LightOnOCR-2-1B-bbox-base` | 1B | yes | Same family as LightOnOCR base; presumed same Qwen3 text stack unless separately proven otherwise. | excluded unless config proves non-Qwen |
| `allenai/olmOCR-2-7B-1025` | 7B | yes | Model card states it is fine-tuned from `Qwen2.5-VL-7B-Instruct`. | excluded |
| `nanonets/Nanonets-OCR2-3B` | 3B | yes | HF tags show base model `Qwen/Qwen2.5-VL-3B-Instruct`. | excluded |
| `datalab-to/chandra-ocr-2` / `datalab-to/surya-ocr-2` | OCR | yes | HF tags show `qwen3_5`. | excluded |
| `PaddlePaddle/PaddleOCR-VL-1.6` | 1B-class | yes | Chinese PaddleOCR/PaddlePaddle stack. | comparison only |

## Download Only These Three

### 1. Main Fine-Tuning Target: Granite Docling 258M

- Hugging Face ID: `ibm-granite/granite-docling-258M`
- Role: primary OCR/document fine-tuning target
- Train on our Korean/Hangul data: yes, via task fine-tuning or LoRA/QLoRA
- Why: OCR/document-conversion model with layout, table, full-page OCR, and DocTags/markdown-style outputs; passes the current non-Chinese stack audit better than larger OCR models that are Qwen-based.
- Caveat: this is much smaller than PaddleOCR-VL and LightOnOCR. The research story should be framed as **rule-compliant non-Chinese OCR adaptation**, not guaranteed absolute SOTA from model size alone.

Download:

```bash
huggingface-cli download ibm-granite/granite-docling-258M \
  --local-dir models/ibm-granite/granite-docling-258M \
  --local-dir-use-symlinks False
```

### 2. Non-Chinese Baseline: SmolDocling 256M Preview

- Hugging Face ID: `docling-project/SmolDocling-256M-preview`
- Role: baseline/control
- Train on our Korean/Hangul data: no, run as-is
- Why: predecessor to Granite Docling, document-conversion model with OCR, layout/localization, table recognition, and bounding-box-aware instructions. Useful to show whether Granite Docling fine-tuning improves over a related non-Chinese baseline.

Download:

```bash
huggingface-cli download docling-project/SmolDocling-256M-preview \
  --local-dir models/docling-project/SmolDocling-256M-preview \
  --local-dir-use-symlinks False
```

### 3. Best Chinese/Top OCR Comparison: PaddleOCR-VL 1.6

- Hugging Face ID: `PaddlePaddle/PaddleOCR-VL-1.6`
- Role: Chinese/top comparison ceiling
- Train on our Korean/Hangul data: no, inference-only comparison
- Why: strong OCR/document parsing model to catch up against.
- Strict rule: do not fine-tune it, do not use it as an implementation reference, and do not use its predictions as training labels.

Download model weights:

```bash
huggingface-cli download PaddlePaddle/PaddleOCR-VL-1.6 \
  --local-dir models/PaddlePaddle/PaddleOCR-VL-1.6 \
  --local-dir-use-symlinks False
```

Install official inference package:

```bash
python -m pip install paddlepaddle-gpu==3.2.1 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
python -m pip install -U "paddleocr[doc-parser]>=3.6.0"
```

Example inference:

```bash
paddleocr doc_parser -i input.png --pipeline_version v1.6
```

## Optional Recognition-Only Baseline

If cropped Hangul text-line recognition becomes a separate subtask, add `microsoft/trocr-large-printed` as a recognition-only baseline. It should not replace Granite Docling as the full-page document/OCR target because it does not handle document layout by itself.

## Experiment Matrix

| Model | Role | Train on our data? | Use in final comparison? |
|---|---:|---:|---:|
| `ibm-granite/granite-docling-258M` | OCR/document fine-tuning target | yes | yes |
| `docling-project/SmolDocling-256M-preview` | non-Chinese OCR/document baseline | no | yes |
| `PaddlePaddle/PaddleOCR-VL-1.6` | Chinese/top OCR comparison ceiling | no | yes, clearly labeled |
| `microsoft/trocr-large-printed` | optional recognition-only baseline | no by default | optional appendix |
| `google/gemma-3-12b-it` | general VLM fallback | only if OCR/document targets fail | optional appendix only |

## Required Metrics

Run all models on the same held-out evaluation splits.

- Hangul-containing text-region detection F1 / IoU, if boxes are available
- Hangul-only CER
- mixed Korean/English/number CER
- table-cell OCR accuracy
- document-structure score, if the model emits layout/markdown/DocTags-like structure
- instruction/output-format adherence rate
- latency and GPU memory per page

## Operational Rules

- Keep downloaded models under `models/`.
- Keep raw outputs under `runs/<model_id>/<dataset>/<timestamp>/`.
- Fine-tune only `ibm-granite/granite-docling-258M` unless the lineage audit is updated with a better non-Chinese OCR target.
- Do task fine-tuning only; do not attempt foundation pre-training.
- Never train on predictions from `PaddlePaddle/PaddleOCR-VL-1.6`.
- Always label PaddleOCR-VL results as `Chinese/top OCR comparison ceiling`, not as a non-Chinese baseline.

## Local Model Storage Note

The current downloaded model directory is `model/`, not `models/`:

- `model/ibm-granite/granite-docling-258M`
- `model/PaddlePaddle/PaddleOCR-VL-1.6`

Future scripts should accept `MODEL_ROOT=model` or read the model root from configuration instead of hardcoding `models/`.

## Hermes Agent Note

