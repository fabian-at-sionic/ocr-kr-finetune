# Stage 1 10K Smoke Run

Date: 2026-06-30

## Purpose

This was a bounded Stage 1 non-AIHub smoke run for IBM Granite/Docling 258M. The goal was not final SOTA quality. The goal was to prove that the local manifest, image loading, prompt formatting, LoRA setup, GPU training path, and final adapter save all work before scaling.

The frozen baseline evaluation data was not used for training.

## Dataset

Manifest:

```text
dataset/hangul_recognition/prepared/manifests/train_stage1_smoke_10k_balanced.jsonl
```

Allocation:

| Bucket | Source | Count | Usage |
| --- | --- | ---: | --- |
| bucket_01_clean_synthetic_hangul_recognition | Jiwon-Kang synthetic rendered Korean OCR train split | 5,000 | train only |
| bucket_02_real_cropped_korean_recognition | AbdullahRian Korean OCR image/text pairs, excluding baseline rows | 5,000 | train only |
| Total | Non-AIHub Stage 1 smoke manifest | 10,000 | train only |

## Training Command

```bash
<PROJECT_ROOT>/.venv-granite-eval/bin/python -u <PROJECT_ROOT>/scripts/train_stage1_lora.py \
  --manifest <PROJECT_ROOT>/dataset/hangul_recognition/prepared/manifests/train_stage1_smoke_10k_balanced.jsonl \
  --out <PROJECT_ROOT>/runs/train/stage1_lora_10k_smoke_textonly \
  --batch-size 16 \
  --grad-accum 1 \
  --epochs 1 \
  --lr 2e-4 \
  --log-every 25 \
  --save-every 10000 \
  --max-answer-chars 160
```

## Configuration

| Setting | Value |
| --- | --- |
| Base model | `<PROJECT_ROOT>/model/ibm-granite/granite-docling-258M` |
| Device | CUDA |
| Examples | 10,000 |
| Batch size | 16 |
| Gradient accumulation | 1 |
| Epochs | 1 |
| Update steps | 625 |
| Learning rate | 2e-4 |
| Warmup ratio | 0.03 |
| Max answer chars | 160 |
| Save cadence | final adapter only |
| Log cadence | 25 steps |
| LoRA scope | text-model LoRA only |

## Results

Output adapter:

```text
<PROJECT_ROOT>/runs/train/stage1_lora_10k_smoke_textonly/final_adapter
```

Key files:

| File | Size |
| --- | ---: |
| `final_adapter/adapter_model.safetensors` | 19,597,680 bytes |
| `final_adapter/tokenizer.json` | 7,153,498 bytes |
| `train_log.jsonl` | 2,972 bytes |
| Total run output | about 26 MB |

Final status:

| Metric | Value |
| --- | ---: |
| Final step | 625 / 625 |
| Final logged loss | 9.0042 |
| Total elapsed training time | 4,833.6 seconds |
| Total elapsed training time | about 80.6 minutes |
| Average wall time per update | about 7.7 seconds |

The run completed without OOM and saved the final LoRA adapter successfully.

## Observations

- Batch size 16 fit after restricting LoRA to text-model modules.
- VRAM rose as high as roughly 175 GB on heavier batches during monitoring, still below the 267.7 GB container ceiling.
- GPU utilization was bursty when sampled directly, but the step log continued advancing and the run completed. The likely bottleneck is mixed CPU/GPU work: image loading from parquet/tar sources, processor collation, and eager VLM attention.
- The first loss spike at step 25 was transient. Loss stabilized mostly around 8-10 after the early warmup phase.
- This run was launched with `--log-every 25`, so exact 10-step reports were not available. Future monitored runs should use `--log-every 10`.


## 2026-07-01 Supersession Notice

The "Next Training Step" recommendation below is historical and must not be followed as-is. A later Stage 1 50K final adapter failed KORIE receipt-field OCR with severe repetition (`0.00%` exact match, `2529.08%` CER, `345.65%` WER). The current strategy is checkpoint-gated training, not automatic scale-up.

Before any checkpoint is used as a parent adapter, evaluate it for CER/WER, exact match, repetition-loop rate, generated-length sanity, and output-format validity. Prefer the best evaluated checkpoint, not the latest or longest-trained checkpoint.

See:

```text
progress/2026-07-01_training_strategy_revision_after_korie_failure.md
nonaihub_training_plan.md
train_instruction.md
```

## Historical Next Training Step

Do not jump directly to full Stage 1 training. The next training process should be a medium Stage 1 scale-up on non-AIHub data while AIHub continues downloading:

1. Build a balanced 50K or 100K Stage 1 manifest from the existing non-AIHub training-only manifests.
2. Keep the frozen baseline evaluation manifest excluded.
3. Use the same text-only LoRA settings that completed this smoke run.
4. Launch with `--log-every 10` for progress reports every 10 steps.
5. Save one final adapter, plus optionally one mid-run checkpoint if the run is expected to exceed 4 hours.
6. After the run, evaluate on a small internal dev split first, not the frozen baseline.

Recommended immediate scale-up:

```text
50K balanced non-AIHub Stage 1 run, 1 epoch, batch size 16, text-only LoRA, max answer chars 160, log every 10 steps.
```

Rationale: 50K is large enough to test whether the loss trend and data pipeline remain stable beyond the 10K smoke run, while still bounded enough to stop before spending a full day on Stage 1 data that will later be dominated by AIHub outdoor detection data.

Avoid full 455.5K non-AIHub training until the AIHub download/extraction state is known, because final SOTA should be driven by the AIHub outdoor detection/region OCR data rather than overfitting the model to the Stage 1 recognition-only distribution.
