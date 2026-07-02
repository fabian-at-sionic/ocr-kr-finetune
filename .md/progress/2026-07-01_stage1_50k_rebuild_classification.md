# Stage 1 50K Rebuild Classification

Date: 2026-07-01

## Stage Terminology

- Stage 1: non-AIHub Korean OCR adaptation using Jiwon/AbdullahRian manifests.
- Stage 2A: AIHub 91 printed word/region OCR using dataset/aihub/processed/manifests/aihub91_printed_train_region_ocr.jsonl.
- Stage 2B: AIHub 91 full-page detection/structured OCR.

## Current Active Run

The current active run is Stage 1. It is not Stage 2A and not Stage 2B.

Exact active command:

<PROJECT_ROOT>/.venv-granite-eval/bin/python -u scripts/train_stage1_lora.py --manifest <PROJECT_ROOT>/dataset/hangul_recognition/prepared/manifests/train_stage1_smoke_50k_balanced.jsonl --out <PROJECT_ROOT>/runs/kept_checkpoints/stage1_lora_50k_balanced_bs16_textonly_20260701 --batch-size 16 --grad-accum 1 --epochs 1 --lr 2e-4 --log-every 10 --save-every 250 --max-answer-chars 160 --num-workers 0

Manifest path: <PROJECT_ROOT>/dataset/hangul_recognition/prepared/manifests/train_stage1_smoke_50k_balanced.jsonl
Output directory: <PROJECT_ROOT>/runs/kept_checkpoints/stage1_lora_50k_balanced_bs16_textonly_20260701
Adapter source path: none. This is Stage 1 and starts from base model <PROJECT_ROOT>/model/ibm-granite/granite-docling-258M.
Rows from AIHub 91: no.
Row sources: 25K Jiwon-Kang clean synthetic Korean OCR and 25K AbdullahRian real cropped Korean OCR.
Frozen baseline rows: excluded by the manifest summary.

## Why Previous Attempts Were Stopped

- stage1_lora_50k_balanced_bs24_textonly_20260701 was stopped because sampled VRAM reached about 264,352 MiB, too close to the effective 267.7 GB ceiling.
- stage1_lora_50k_balanced_bs20_textonly_20260701 was stopped because sampled VRAM reached about 251,926 MiB, also too close to the effective ceiling.
- Both stopped runs saved interrupted_adapter directories, but neither reached the scheduled checkpoint-250 milestone.

The current bs16 run was started because prior Stage 1 evidence showed batch size 16 had materially better VRAM margin.
