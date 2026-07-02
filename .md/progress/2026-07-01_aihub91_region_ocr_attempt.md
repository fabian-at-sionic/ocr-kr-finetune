# AIHub 91 Printed Region OCR Manifest And Training Attempt

Date: 2026-07-01

## Summary

Built bounded AIHub 91 printed region OCR manifests from zip files without extracting images or materializing crops. Started the recommended Stage 2A region OCR run from the completed Stage 1 10K adapter, then stopped it at step 300 because VRAM approached the repo ceiling. Added crop long-edge bounding to the trainer and verified a 40-step bounded smoke run.

## Manifests

- Train: `dataset/aihub/processed/manifests/aihub91_printed_train_region_ocr.jsonl`
- Validation: `dataset/aihub/processed/manifests/aihub91_printed_val_region_ocr.jsonl`
- Summary: `dataset/aihub/processed/manifests/aihub91_printed_region_ocr.summary.json`

Manifest counts:

| Split | Rows | Candidate regions scanned |
| --- | ---: | ---: |
| Training printed | 50,000 | 9,546,600 |
| Validation printed | 5,000 | 1,192,871 |

No images or crops were materialized. Rows lazy-reference the AIHub 91 printed image and label zip members plus word boxes.

## Code Added

- `scripts/build_aihub91_manifests.py`
- `scripts/train_aihub91_region_lora.py`

The trainer continues from a PEFT adapter when `--adapter` is provided and lazy-loads/crops regions from image zip members. After the first full-run attempt, the trainer was updated with `--max-crop-long-edge` to downscale very large region crops before processor input and to save `interrupted_adapter` on `KeyboardInterrupt`.

## Runs

Initial 5-step adapter/crop smoke:

- Output: `runs/train/aihub91_region_lora_50k_textonly_from_stage1_10k_smoke5/final_adapter`
- Completed 5/5 steps.

Unbounded full run attempt:

- Output dir: `runs/train/aihub91_region_lora_50k_textonly_from_stage1_10k`
- Started from: `runs/train/stage1_lora_10k_smoke_textonly/final_adapter`
- Command used batch size 16, 1 epoch, lr 2e-4, log every 10, save every 500, max answer chars 80.
- Stopped manually at step 300/3125 because observed VRAM reached 254,620 MiB, effectively at the 267.7 GB repo ceiling.
- Last logged loss: 0.5069792792201042 at elapsed 2738.0 seconds.
- No adapter checkpoint was available because the first checkpoint was configured for step 500.

Crop-bounded 40-step smoke:

- Output: `runs/train/aihub91_region_lora_50k_textonly_from_stage1_10k_maxedge768_smoke40/final_adapter`
- Command added `--max-crop-long-edge 768`.
- Completed 40/40 steps.
- Last logged loss: 0.7250651903450489 at elapsed 373.0 seconds.
- Observed VRAM still rose to about 240,406 MiB, lower than the stopped attempt but still high enough to prefer a stricter bound for the full run.

## Current Blocker

A separate GPU process appeared after the smoke run:

```text
.venv-granite-eval/bin/python scripts/run_korie_granite_ocr_test.py --batch-size 16 --out runs/benchmark/korie/docling_base_predictions.jsonl --metrics-out runs/benchmark/korie/docling_base_metrics.json
```

It was using about 126,760 MiB VRAM. Per `warning.md` and the handoff, do not run the AIHub trainer concurrently with this process.

## Recommended Next Command

After the KORIE benchmark process exits and GPU memory is clear, restart the AIHub 91 region run with a stricter crop bound and frequent checkpoints:

```bash
<PROJECT_ROOT>/.venv-granite-eval/bin/python -u scripts/train_aihub91_region_lora.py \
  --adapter <PROJECT_ROOT>/runs/train/stage1_lora_10k_smoke_textonly/final_adapter \
  --manifest <PROJECT_ROOT>/dataset/aihub/processed/manifests/aihub91_printed_train_region_ocr.jsonl \
  --out <PROJECT_ROOT>/runs/train/aihub91_region_lora_50k_textonly_from_stage1_10k_maxedge512 \
  --batch-size 16 \
  --grad-accum 1 \
  --epochs 1 \
  --lr 2e-4 \
  --log-every 10 \
  --save-every 250 \
  --max-answer-chars 80 \
  --max-crop-long-edge 512
```

If VRAM still approaches the ceiling, reduce to `--batch-size 8 --grad-accum 2` and keep `--max-crop-long-edge 512`.

## 2026-07-01 Resume Interruption Update

The user asked to resume monitoring the AIHub 91 region OCR run. The task was AIHub 91 printed word/region OCR LoRA training from the Stage 1 adapter using `dataset/aihub/processed/manifests/aihub91_printed_train_region_ocr.jsonl`.

Observed state during resume:

- The maxedge512 run had reached step 270/3125 before interruption, with `checkpoint-250` saved.
- A resume was launched from `checkpoint-250` for the remaining 2,875 steps.
- The resume reached step 70, equivalent to overall step 320/3125 or 10.24% complete, with latest logged loss 0.41400485299527645.
- The resumed process exited with code 143 before its first checkpoint.
- After the exit, `runs/train` was externally reduced to only `stage1_lora_50k_balanced_textonly_v3`, and no `adapter_model.safetensors` remained anywhere under `<PROJECT_ROOT>`.
- GPU is now idle and the AIHub manifests remain intact.

Consequence: there is no usable Stage 1 adapter or AIHub checkpoint left in the workspace, so the AIHub adapter-continuation run cannot be resumed exactly. The next safe choices are either recreate a Stage 1 adapter first, then rerun AIHub Stage 2A, or deliberately start AIHub Stage 2A from the base model and document that it is a scratch adapter run.
