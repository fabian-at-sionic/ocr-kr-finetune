# Stage 1 LoRA 50K balanced text-only v3 complete

Date: 2026-07-01

## Result

- Status: complete
- Final adapter: `<PROJECT_ROOT>/runs/train/stage1_lora_50k_balanced_textonly_v3/final_adapter`
- Retained checkpoint: `<PROJECT_ROOT>/runs/train/stage1_lora_50k_balanced_textonly_v3/checkpoint-3000`
- Output size: 52M
- Last logged step: 3120 / 3125
- Last logged loss: 141.04383659362793
- Last logged elapsed time: 24415.1 seconds
- Final path printed by trainer: `<PROJECT_ROOT>/runs/train/stage1_lora_50k_balanced_textonly_v3/final_adapter`

The trainer completed the full epoch and saved `final_adapter`. The training loop logged every 10 steps, so the last JSON log line captured was step 3120 even though the run completed and saved the final adapter after the final batches.

## Inputs

- Manifest: `<PROJECT_ROOT>/dataset/hangul_recognition/prepared/manifests/train_stage1_smoke_50k_balanced.jsonl`
- Manifest rows checked before launch: 50,000
- Batch size: 16
- Gradient accumulation: 1
- Epochs: 1
- Planned optimizer steps: 3125
- Max answer chars: 160

## Command

```bash
<PROJECT_ROOT>/.venv-granite-eval/bin/python -u <PROJECT_ROOT>/scripts/train_stage1_lora.py \
  --manifest <PROJECT_ROOT>/dataset/hangul_recognition/prepared/manifests/train_stage1_smoke_50k_balanced.jsonl \
  --out <PROJECT_ROOT>/runs/train/stage1_lora_50k_balanced_textonly_v3 \
  --batch-size 16 \
  --grad-accum 1 \
  --epochs 1 \
  --lr 2e-4 \
  --log-every 10 \
  --save-every 500 \
  --max-answer-chars 160
```

## Resource Notes

- Peak observed VRAM during monitoring: 242,844 MiB / 275,040 MiB.
- GPU memory was released after completion; `nvidia-smi` showed 0 MiB in use and no running GPU processes.
- System memory remained well below the 267.7 GB effective ceiling during the monitored run.
- Dataset storage was not rechecked during the final phase per the user instruction to check only if storage exceeded 500 GB or there was reason to suspect it.

## GPU Utilization Finding

The model and tensors were running on CUDA. The training process held about 242.8 GiB of VRAM during the run, and interval sampling caught active GPU bursts including 100% SM / 65% memory-utilization. Single-point `nvidia-smi` samples often showed 0% GPU utilization because the workload was bursty and the CPU-side input pipeline had idle gaps between batches.

The slower component observed during the run was CPU-side data loading and preprocessing/tokenization:

- PIL image load/convert
- parquet/tar-backed sample loading
- processor image preprocessing and tokenization
- dataloader running with `num_workers=0`

Changing that safely would require restarting with input-pipeline changes, so the active run was left uninterrupted.

## Events

- This was a restart of the earlier partial 50K run that stopped at step 2630 because dataset storage exceeded the cap during a concurrent AIHub download/reassembly.
- v3 used `--save-every 500` so checkpoints were available during the run.
- Earlier checkpoints were observed at 500, 1000, 1500, 2000, and 2500. The completed output directory retained checkpoint-3000 and final_adapter.
- Loss entered the same high-loss region seen in the prior partial run, then stayed high through the tail. Training was not interrupted because steps advanced normally and the requested job was to continue through completion.
