# Training Handoff Instructions

These instructions supersede the earlier overnight 50K Stage 1 handoff. The Stage 1 50K final adapter completed, but KORIE evaluation exposed severe generation collapse. Do not run more long training from this document without the evaluation gate below.

## Current Incident

The completed adapter:

```text
<PROJECT_ROOT>/runs/train/stage1_lora_50k_balanced_textonly_v3/final_adapter
```

failed on KORIE receipt-field OCR:

```text
Exact match: 0.00%
CER: 2529.08%
WER: 345.65%
Failure mode: repeated fragments such as amoto... and iginal...
```

This means the adapter is not automatically a good Stage 1 parent, even though it finished training. Loss and runtime are not enough.

## Required First Action

Before continuing Stage 2A or Stage 2B, evaluate candidate adapters/checkpoints and select the best one.

Candidates to compare if present:

```text
base Granite/Docling model
runs/train/stage1_lora_50k_balanced_textonly_v3/checkpoint-3000
runs/train/stage1_lora_50k_balanced_textonly_v3/final_adapter
runs/kept_checkpoints/stage1_lora_50k_balanced_bs16_textonly_20260701/interrupted_adapter
runs/kept_checkpoints/stage1_lora_50k_balanced_bs20_textonly_20260701/interrupted_adapter
runs/kept_checkpoints/stage1_lora_50k_balanced_bs24_textonly_20260701/interrupted_adapter
runs/kept_checkpoints/stage2a_aihub91_region_50k_from_stage1_50k_v3_bs16_ga2_512_20260701T0745Z/checkpoint-100
runs/kept_checkpoints/stage2a_aihub91_region_50k_from_stage1_50k_v3_bs16_ga2_512_20260701T0745Z/checkpoint-200
runs/kept_checkpoints/stage2a_aihub91_region_50k_from_stage1_50k_v3_bs16_ga2_512_20260701T0745Z/checkpoint-300
runs/kept_checkpoints/stage2a_aihub91_region_50k_from_stage1_50k_v3_bs16_ga2_512_20260701T0745Z/interrupted_adapter
```

Use bounded eval shards, not the full frozen baseline for iteration:

```text
AIHub 91 printed region validation sample
small KORIE sample
small internal non-AIHub dev sample if available
```

Report for each candidate:

```text
CER
WER
exact match
blank rate
repetition-loop rate
average generated length / target length
control-token generation count
sample predictions
GPU memory and latency
```

## Promotion Gate

A checkpoint may be used as a parent for further training only if:

```text
repetition-loop rate is near zero
no generated image/control special tokens
CER/WER is better than base or previous accepted checkpoint on the relevant eval shard
exact match does not collapse on easy samples
outputs stop naturally instead of running to max_new_tokens
sample predictions are readable OCR outputs
```

If no checkpoint passes, do not continue Stage 2A from the failed 50K final adapter. Rebuild a smaller Stage 1 with evaluation every 100-250 steps, or start a controlled AIHub-only scratch experiment and label it as scratch.

## Stage 2A Policy

Stage 2A means:

```text
AIHub 91 printed word/region OCR
manifest: dataset/aihub/processed/manifests/aihub91_printed_train_region_ocr.jsonl
```

If Stage 2A is still running from the suspect 50K final adapter, stop safely at the next checkpoint or save `interrupted_adapter`. Do not delete any checkpoint.

Resume Stage 2A only from the best evaluated parent checkpoint.

## Stage 2B Policy

Stage 2B means:

```text
AIHub 91 printed full-page/page-tile detection + structured OCR
```

Only smoke/schema tests may run until a Stage 2A checkpoint is accepted. Full Stage 2B should continue from the best Stage 2A checkpoint, not from the unvalidated 50K final adapter.

## Hard Exclusions

Never train on:

```text
dataset/hangul_recognition/prepared/manifests/eval_frozen_baseline.jsonl
AIHub 91 validation splits
KORIE test split
PaddleOCR-VL predictions
```

## Operational Rules

- Save checkpoints every 100-250 steps for long runs.
- Write progress notes after failures and after checkpoint selection.
- Use unique output directories under `runs/kept_checkpoints/` for important runs.
- Do not clean `runs/train` or `runs/kept_checkpoints` while training/evaluation decisions depend on them.
- Do not launch another multi-hour run based only on training loss.
