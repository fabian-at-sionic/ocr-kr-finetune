# Non-AIHub Training Plan

Resource warning: read `warning.md` before training, preprocessing, extraction, or large evaluation jobs. Memory/VRAM ceiling is 267.7 GB. Dataset storage cap is normally 700 GB under `<PROJECT_ROOT>/dataset`, except when the user explicitly grants a temporary override.

## 2026-07-01 Strategy Revision After KORIE 50K Failure

The completed Stage 1 50K LoRA (`runs/train/stage1_lora_50k_balanced_textonly_v3/final_adapter`) produced catastrophic repetition on the KORIE receipt-field OCR benchmark: `0.00%` exact match, `2529.08%` CER, and `345.65%` WER. Predictions repeatedly emitted fragments such as `amoto...` and `iginal...` until the generation limit.

This invalidates the previous assumption that a longer Stage 1 run is automatically better. From this point forward, **training loss and completion status are not sufficient evidence of progress**. A checkpoint is usable only after it passes an evaluation gate.

Hard rule:

```text
No multi-hour training run may continue or be used as a parent adapter unless the candidate checkpoint passes a bounded evaluation gate for CER/WER, exact match, repetition rate, generated length, and output-format validity.
```

Immediate consequence:

- Do not treat the Stage 1 50K final adapter as the default best adapter.
- Evaluate Stage 1 checkpoint-3000, Stage 1 final_adapter, retained Stage 1 interrupted adapters, and Stage 2A checkpoints before selecting any parent checkpoint.
- If Stage 2A is still running from the suspect 50K final adapter, stop safely at the next checkpoint or save `interrupted_adapter`, then run checkpoint-gated evaluation before resuming.

## Position In The Overall SOTA Strategy

Training can be split into two stages without hurting the SOTA goal:

```text
Stage 1: Non-AIHub recognition/bootstrap training
Stage 2: AIHub detection/document/outdoor specialization training
```

This does not conflict with the SOTA objective only if Stage 1 is treated as a gated foundation step, not the final result and not automatically valid because it ran longer. Stage 1 may improve Korean OCR behavior, Hangul transcription, decoding stability, and prompt/format reliability, but it can also degrade generation if unchecked. Stage 2 is still required for the final SOTA claim on Hangul text-region detection and real-world/document OCR.

Current limitation:

```text
The non-AIHub data is recognition-heavy.
It does not provide enough bbox/layout/outdoor detection supervision by itself.
```

Therefore Stage 1 can improve:

```text
Hangul recognition
Korean text transcription
long/narrow crop robustness
basic OCR prompt following
```

Stage 1 cannot fully prove:

```text
Hangul detection F1 / IoU
outdoor sign detection SOTA
document/form layout SOTA
table-cell localization SOTA
```

Those require AIHub or another bbox/layout dataset.

## Stage 1 Data

Use only the current non-AIHub training manifests:

```text
dataset/hangul_recognition/prepared/manifests/train_clean_synthetic_recognition.jsonl
dataset/hangul_recognition/prepared/manifests/train_real_cropped_recognition.jsonl
dataset/hangul_recognition/prepared/manifests/train_current_all.jsonl
```

Do not train on:

```text
dataset/hangul_recognition/prepared/manifests/eval_frozen_baseline.jsonl
dataset/hangul_recognition/baseline_testing/prepared/
Jiwon validation parquet
AbdullahRian 500 baseline sample rows
AIHub 105 while download is incomplete
```

Current counts:

```text
Jiwon-Kang train:              200,000 rows
AbdullahRian non-baseline:     255,500 rows
Combined Stage 1 training:     455,500 rows
Frozen baseline eval:            1,000 rows
```

Raw backing data:

```text
Jiwon-Kang:       about 12 GB
AbdullahRian:     about 19 GB
Total backing:    about 31 GB
Manifest files:   about 683 MB
```

## Buckets Used In Stage 1

### Bucket 01: Clean Synthetic Hangul Recognition

Manifest:

```text
dataset/hangul_recognition/prepared/manifests/train_clean_synthetic_recognition.jsonl
```

Purpose:

```text
Clean OCR warmup
Hangul character/syllable recognition
Simple Korean transcription behavior
Prompt/response stabilization
```

Task:

```text
image -> exact Korean text
```

Storage dtype:

```text
parquet_embedded_image
```

### Bucket 02: Real Cropped Korean Recognition

Manifest:

```text
dataset/hangul_recognition/prepared/manifests/train_real_cropped_recognition.jsonl
```

Purpose:

```text
Real image-text OCR
Noisier Korean crops
Non-square text images
Recognition robustness beyond synthetic data
```

Task:

```text
cropped or strip-like image -> exact Korean text
```

Storage dtype:

```text
tar_member_pair
```

### Bucket 03: Extreme Aspect-Ratio Text Strips

Current status:

```text
manifest placeholder exists but is empty
```

Reason:

```text
Filling it requires scanning image dimensions inside 255,500 tar entries.
Do this later as a bounded preprocessing pass, preferably after AIHub download finishes or during idle time.
```

Stage 1 can still train without it by using Bucket 02. The hard subset can be added in a later Stage 1.1.

## Recommended Stage 1 Mixture

Initial mixture:

```text
50% Bucket 01: clean synthetic recognition
50% Bucket 02: real cropped recognition
```

After extreme-aspect manifest exists:

```text
45% Bucket 01: clean synthetic recognition
45% Bucket 02: real cropped recognition
10% Bucket 03: extreme aspect-ratio strips
```

Do not oversample one source exclusively. Jiwon teaches clean Korean rendering; AbdullahRian teaches messier crop behavior.

## Model And Method

Fine-tuning target:

```text
model/ibm-granite/granite-docling-258M
```

Recommended first method:

```text
LoRA / QLoRA supervised fine-tuning
```

Train first on recognition prompts only. Do not introduce bbox JSON until AIHub detection labels are ready.

Prompt for Stage 1:

```text
Extract all Korean/Hangul text from the image exactly as written.
```

Target:

```text
plain text transcript
```

Avoid using the current heavier prompt for training:

```text
Convert this page to docling.
```

That prompt is useful for document conversion but too broad for this recognition-bootstrap stage.

## Stage 1 Validation And Mandatory Eval Gate

The KORIE 50K failure showed that loss curves and completed epochs are not enough. Stage 1 validation is mandatory before any checkpoint is used for Stage 2.

Create a small internal dev manifest from train-allowed rows only:

```text
dataset/hangul_recognition/prepared/manifests/dev_internal_recognition.jsonl
```

Suggested size:

```text
2,000-5,000 Jiwon train rows
2,000-5,000 Abdullah non-baseline rows
```

Use this for:

```text
checkpoint selection
early stopping
learning-rate checks
prompt sanity checks
format stability
repetition-loop detection
generated-length sanity checks
```

A Stage 1 checkpoint may seed Stage 2 only if it passes all of these gates on a bounded dev/eval shard:

```text
repetition-loop rate is near zero
no multimodal/control special-token generation
CER/WER improves over base or the previous accepted checkpoint
exact match does not collapse on easy samples
average generated length is close to target length, not max-token length
sample predictions are readable Korean/numeric OCR, not repeated Latin fragments
```

Do not use the frozen baseline eval set for iterative decisions.

Frozen eval can be run occasionally, but do not tune repeatedly against it.

## Stage 1 Metrics

Primary metrics:

```text
CER: character error rate
exact match rate
empty-output rate
repetition-loop rate
latency per image
GPU memory
```

Do not claim detection SOTA from Stage 1. Stage 1 has no detection F1 because the current manifests do not contain bounding boxes.

## Stage 1 Success Criteria

Stage 1 is useful only if evaluation shows:

```text
lower CER than zero-shot Granite or the previous accepted checkpoint on bounded dev/eval shards
near-zero repeated-token outputs
near-zero control-token outputs such as <image> or fake image tokens
lower empty-output rate
stable Korean transcription
no collapse on synthetic, real cropped, numeric, or receipt-like inputs
```

Stage 1 should produce:

```text
LoRA/adapter checkpoint
training logs
internal dev metrics
frozen baseline comparison
known failure cases for Stage 2
```

## Stage 2 Handoff To AIHub

When AIHub 105 is fully downloaded and labels are verified, create these manifests:

```text
dataset/hangul_recognition/prepared/manifests/train_aihub105_outdoor_detection.jsonl
dataset/hangul_recognition/prepared/manifests/train_aihub105_region_ocr.jsonl
dataset/hangul_recognition/prepared/manifests/test_aihub105_official_validation.jsonl
```

Then continue from the **best evaluated Stage 1 checkpoint**, not necessarily the latest or final adapter, into Stage 2:

```text
accepted Stage 1 checkpoint + AIHub bbox/region OCR training
```

Do not continue Stage 2 from a checkpoint that has failed the repetition/generation eval gate.

Stage 2 should add:

```text
bbox JSON outputs
region OCR from bboxes
outdoor/signboard detection
book-cover text detection
hard negatives and background regions
small text robustness
```

Final SOTA claim should be based on Stage 2, not Stage 1 alone.

## Why This Does Not Hurt SOTA

Splitting training is acceptable because it is curriculum learning:

```text
first learn Korean OCR recognition reliably
then learn where Korean text is in real scenes/documents
```

The risk would be stopping after Stage 1 and claiming detection SOTA. We should not do that.

Stage 1 is a bootstrap only after it passes evaluation. Stage 2 is the SOTA-critical phase, but it must start from an accepted checkpoint, not from a longer-but-degraded adapter.
