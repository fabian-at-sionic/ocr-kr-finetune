# Dataset Buckets

This file defines the current logical dataset buckets for Hangul OCR fine-tuning and evaluation. Raw datasets should stay in their source directories; buckets should be implemented with manifests or symlinks later, not by duplicating large image files.

Resource warning: read `warning.md` before downloads, extraction, tiling, preprocessing, training, or baseline evaluation. Memory/VRAM ceiling is 267.7 GB. Dataset storage cap is normally 700 GB under `<PROJECT_ROOT>/dataset`, with any temporary override requiring explicit user approval.


## 2026-07-01 Evaluation-Gated Bucket Policy

The Stage 1 50K final adapter failed badly on KORIE receipt-field OCR with repetition loops and catastrophic CER/WER. Therefore buckets are no longer only sampling groups; they are also evaluation-control boundaries.

Hard rules:

```text
No checkpoint is promoted because it trained longer.
No Stage 2 run should continue from an unvalidated Stage 1 adapter.
No final adapter should be selected without CER/WER, exact match, repetition rate, generated-length, and format-validity checks.
```

The Stage 1 50K final adapter is **suspect** until compared against checkpoint-3000, retained interrupted adapters, base model, and Stage 2A checkpoints on bounded eval shards. Prefer the best evaluated checkpoint, not the latest checkpoint.

## Core Rule

Data used for baseline or final evaluation must not be reused for training, validation, prompt tuning, hard-negative mining, checkpoint selection, or postprocessing design.

Current frozen baseline/eval data:

```text
dataset/hangul_recognition/baseline_testing/prepared/
```

Current strict train candidates before AIHub completion:

```text
Jiwon-Kang train split: 200,000 examples
AbdullahRian non-baseline rows: about 255,500 examples
```

## Bucket 00: Frozen Baseline Evaluation

Purpose:

- Stable baseline comparison across Granite Docling, SmolDocling, and PaddleOCR-VL.
- Quick CER/exact-match sanity benchmark.
- Never used for training.

Allocated data:

```text
dataset/hangul_recognition/baseline_testing/prepared/manifests/baseline_eval.jsonl
```

Composition:

```text
500 Jiwon-Kang validation images
500 AbdullahRian sampled images
1,000 total materialized eval images
```

Use:

```text
final/baseline eval only
```

Do not use for:

```text
training
validation/dev
prompt tuning
sampling-ratio tuning
hard-negative mining
checkpoint choice
```

## Bucket 01: Clean Synthetic Hangul Recognition

Purpose:

- Warm up the model on clean Korean OCR.
- Improve Hangul character/syllable recognition.
- Teach simple OCR prompt/response behavior.
- Stabilize Korean transcription before harder real data.

Allocated data:

```text
dataset/hangul_recognition/training/Jiwon-Kang_OCR-Synthetic-Rendered-Korean-200K/data/train-*.parquet
```

Count:

```text
200,000 train examples
```

Use:

```text
training only
```

Exclude:

```text
dataset/hangul_recognition/training/Jiwon-Kang_OCR-Synthetic-Rendered-Korean-200K/data/validation-00000-of-00001.parquet
any rows referenced by baseline_testing/prepared/manifests/jiwon_kang_validation.jsonl
```

Primary task format:

```text
image -> exact Korean text
```

Suggested manifest:

```text
dataset/hangul_recognition/prepared/manifests/train_clean_synthetic_recognition.jsonl
```

## Bucket 02: Real Cropped Korean Recognition

Purpose:

- Train OCR on real Korean image/text pairs.
- Cover non-square text images and noisy real crops.
- Improve robustness beyond synthetic rendered samples.

Allocated data:

```text
dataset/hangul_recognition/training/AbdullahRian_Korean_OCR_Img_text_pair/ocr-shard-*.tar
```

Count:

```text
256,000 indexed pairs total
about 255,500 train candidates after excluding the 500 baseline sample rows
```

Use:

```text
training only, after excluding baseline sample rows
```

Exclude:

```text
all rows referenced by baseline_testing/prepared/manifests/abdullahrian_sample.jsonl
all rows included in baseline_testing/prepared/manifests/baseline_eval.jsonl
```

Primary task format:

```text
cropped or strip-like image -> exact Korean text
```

Suggested manifest:

```text
dataset/hangul_recognition/prepared/manifests/train_real_cropped_recognition.jsonl
```

## Bucket 03: Extreme Aspect-Ratio Text Strips

Purpose:

- Handle very wide, short Korean text strips.
- Reduce repetition loops and decoding instability on subtitle-like images.
- Improve robustness where standard OCR/VLM preprocessing often struggles.

Allocated data:

```text
subset of AbdullahRian_Korean_OCR_Img_text_pair
```

Selection rule:

```text
aspect_ratio > 5 as broad bucket
aspect_ratio > 20 as hard subset
```

Use:

```text
training only, after excluding baseline rows
```

Primary task format:

```text
wide text strip -> exact Korean text
```

Suggested manifest:

```text
dataset/hangul_recognition/prepared/manifests/train_extreme_aspect_text_strips.jsonl
```

## Bucket 04: Internal Development Recognition

Purpose:

- Fast development checks during training.
- Prompt comparison, schema checks, checkpoint selection, and early stopping.
- Must be separate from frozen baseline/final test data.

Allocated data:

```text
small sampled split from Bucket 01 and Bucket 02 training-only rows
```

Suggested size:

```text
1,000-5,000 Jiwon train rows
1,000-5,000 Abdullah non-baseline rows
```

Use:

```text
validation/dev only
```

Do not report as final benchmark.

Suggested manifest:

```text
dataset/hangul_recognition/prepared/manifests/dev_internal_recognition.jsonl
```

## Bucket 05: AIHub 105 Outdoor Hangul Detection In Progress

Purpose:

- Add the missing detection side of the project.
- Train and evaluate Hangul-containing text-region detection in natural/outdoor scenes.
- Provide bbox/transcript supervision for signboards and book covers if labels match the advertised structure.

Current active download path:

```text
dataset/hangul_recognition/training/AIHub_105_outdoor_real_hangul_images/
```

Earlier failed test path, not data:

```text
dataset/hangul_recognition/training/aihub_105_outdoor_hangul/
```

Expected allocation after download/extraction:

Training only:

```text
1.Training/[원천]Training_간판_*.zip
1.Training/[원천]Training_책표지*.zip
1.Training/[라벨]Training.zip
1.Training/원천데이터_230216_add/TS1.zip
1.Training/라벨링데이터_230216_add/TL1.zip
```

Heldout/final test only:

```text
2.Validation/[원천]Validation_간판*.zip
2.Validation/[원천]Validation_책표지.zip
2.Validation/[라벨]Validation.zip
2.Validation/원천데이터_230216_add/VS1.zip
2.Validation/라벨링데이터_230216_add/VL1.zip
```

Sub-buckets after extraction:

```text
bucket_outdoor_sign_horizontal      # 가로형간판
bucket_outdoor_sign_vertical        # 세로형간판
bucket_outdoor_sign_projecting      # 돌출간판
bucket_outdoor_sign_indoor          # 실내간판, 실내안내판
bucket_outdoor_sign_pole_window     # 지주이용간판, 창문이용광고물
bucket_outdoor_banner               # 현수막
bucket_book_cover                   # 책표지
```

Primary task formats:

```text
full image -> Hangul-containing bbox JSON
bbox crop -> transcript
full image -> all visible Korean text
negative/background region -> []
```

Suggested manifests:

```text
dataset/hangul_recognition/prepared/manifests/train_aihub105_outdoor_detection.jsonl
dataset/hangul_recognition/prepared/manifests/train_aihub105_region_ocr.jsonl
dataset/hangul_recognition/prepared/manifests/test_aihub105_official_validation.jsonl
```

## Bucket 06: Pending / Metadata-Only Sources

Purpose:

- Track datasets that exist locally but are not yet usable training data.
- Avoid accidentally counting LFS pointer files as downloaded image data.

Allocated data:

```text
dataset/hangul_recognition/training/jeina_korean_ocr_public
dataset/hangul_recognition/training/jeina_korean_ocr_public_2
dataset/hangul_recognition/training/jeina_korean_ocr_public_3
dataset/hangul_recognition/training/hyeongyeolryu_korean_outdoor_ocr
```

Current status:

```text
metadata-only or partial Git LFS clones
many ZIP files are pointer-sized, not real payloads
```

Use:

```text
not for training yet
```

Move into real buckets only after full data blobs and labels are present.


## Bucket 07: AIHub 91 Printed Form Detection/OCR

Purpose:

- Train/evaluate page-level Korean form text detection and structured OCR.
- Use AIHub 91 printed full-page form images with institution-provided word boxes, char boxes, and transcripts.
- This is Stage 2B data, not Stage 1 data.

Allocated data:

```text
dataset/aihub/raw/91_hangul_ocr
```

Use:

```text
AIHub 91 Training_인쇄체: training only
AIHub 91 validation_인쇄체: heldout AIHub dev/test only
```

Primary task format:

```text
full page or page tile -> compact JSON list of word-level bbox + text
```

Do not use char-level full-page JSON until word-level/page-tile smoke tests pass format-validity gates.

## Bucket 08: AIHub 91 Printed Region OCR

Purpose:

- Train Korean OCR on lazy crops from AIHub 91 printed word boxes.
- This is Stage 2A data and is currently the highest-value AIHub specialization bucket.

Suggested manifests:

```text
dataset/aihub/processed/manifests/aihub91_printed_train_region_ocr.jsonl
dataset/aihub/processed/manifests/aihub91_printed_val_region_ocr.jsonl
```

Use:

```text
train manifest: training only
val manifest: evaluation/checkpoint gate only, not training
```

Primary task format:

```text
wordbox crop -> exact text value
```

Stage 2A may continue only from a Stage 1 checkpoint that passes the repetition/generation eval gate.

## Bucket 09: AIHub 91 Handwriting Robustness

Purpose:

- Controlled robustness slice for handwritten Hangul glyphs.
- Do not let handwriting dominate printed/form OCR.

Use:

```text
small capped subset only after printed region/page OCR is stable
```

Suggested cap:

```text
10K-50K samples
```

## Historical First Training Mixture Before AIHub Data Was Ready

```text
50% Bucket 01: clean synthetic recognition
40% Bucket 02: real cropped recognition
10% Bucket 03: extreme aspect-ratio text strips
```

This is recognition-heavy and must be treated as a gated first fine-tuning stage, not a full SOTA detection training set. After the KORIE 50K failure, this mixture must not be scaled or promoted without a bounded eval gate.

## Revised Training Mixture After AIHub 91 Is Ready

```text
Stage 2A: mostly Bucket 08 AIHub 91 printed region OCR, started only from an accepted Stage 1 checkpoint
Stage 2B smoke: Bucket 07 AIHub 91 printed page/tile structured OCR, small schema tests only until Stage 2A is evaluated
Robustness: Bucket 03 and Bucket 09 only after evaluation identifies a specific weakness
```

Do not use AIHub official validation as training. Do not run full Stage 2B from a suspect Stage 1 adapter. Do not mix large handwriting or synthetic data into Stage 2 unless an eval failure justifies it.

## Final Evaluation Policy

Use final reports only from frozen data:

```text
Bucket 00: current baseline eval
AIHub 105 official 2.Validation after download
future source-level heldout datasets
```

Never train on final/eval data, and never use PaddleOCR-VL predictions as training labels.
