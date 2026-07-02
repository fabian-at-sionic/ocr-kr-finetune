# KORIE 50K LoRA Rerun Attempt

Date: 2026-07-01

## Request

Rerun the KORIE OCR benchmark using the completed 50K Stage 1 LoRA adapter and summarize the results in a new progress note.

Requested adapter:

```text
<PROJECT_ROOT>/runs/train/stage1_lora_50k_balanced_textonly_v3/final_adapter
```

## Status

Blocked: the KORIE benchmark could not be rerun from the current workspace state because the KORIE dataset files and prior KORIE runner are no longer present.

No new KORIE metrics were produced.

## Resource Preflight

The repository warning was read before attempting evaluation.

Resource state before the attempted rerun:

- System memory: 87 GiB used, about 1.9 TiB available.
- GPU: NVIDIA B300, 0 MiB VRAM in use, 0% utilization, no running GPU processes.
- The machine had enough free GPU and system memory to run a single Granite/Docling LoRA evaluation job.

## What Exists

The 50K LoRA adapter exists:

```text
<PROJECT_ROOT>/runs/train/stage1_lora_50k_balanced_textonly_v3/final_adapter/adapter_model.safetensors
```

Additional related adapter files were found under the same completed run:

```text
<PROJECT_ROOT>/runs/train/stage1_lora_50k_balanced_textonly_v3/checkpoint-3000/adapter_model.safetensors
```

## What Is Missing

The previous KORIE summary is the only KORIE artifact currently present:

```text
<PROJECT_ROOT>/progress/2026-07-01_korie_four_model_benchmark_summary.md
```

No KORIE dataset files, KORIE manifests, KORIE prediction artifacts, KORIE metrics JSON files, or `scripts/run_korie_granite_ocr_test.py` runner are present in the workspace.

The prior summary states that the detailed prediction artifacts and temporary KORIE files were deleted after that benchmark run.

## Previous KORIE Baseline For Context

The previous KORIE benchmark used:

- Dataset: KORIE OCR test split
- Evaluation unit: cropped receipt field images
- Sample count: 1,786
- Metrics: exact match, CER, WER

Prior results from the saved summary:

| Rank by CER | Model | Samples | Errors | Exact Match | CER | WER |
|---:|---|---:|---:|---:|---:|---:|
| 1 | PaddleOCR GPU Korean PP-OCRv5 | 1,786 | 0 | 54.31% | 15.96% | 48.28% |
| 2 | PaddleOCR-VL-1.6-0.9B | 1,786 | 0 | 47.70% | 63.70% | 66.68% |
| 3 | IBM Granite/Docling 10k LoRA | 1,786 | 0 | 20.66% | 69.43% | 125.60% |
| 4 | Base Granite/Docling | 1,786 | 0 | 0.95% | 141.33% | 158.92% |

The requested 50K LoRA result cannot be compared until the KORIE test split or an equivalent manifest is restored.

## Commands/Checks Performed

Checked resource state:

```bash
free -h
nvidia-smi
```

Searched for KORIE scripts, data, and artifacts:

```bash
rg -n "korie|adapter|lora|run_korie|KORIE" scripts progress dataset -g '!dataset/hangul_recognition/prepared/manifests/train_*.jsonl'
find <PROJECT_ROOT>/scripts -maxdepth 1 -type f -printf '%f\n'
find <PROJECT_ROOT> -path '*/.git/*' -prune -o -iname '*korie*' -printf '%y %p\n'
find <PROJECT_ROOT>/dataset <PROJECT_ROOT>/runs -path '*/.git/*' -prune -o -iname '*receipt*' -printf '%y %p\n'
find <PROJECT_ROOT>/dataset <PROJECT_ROOT>/runs -path '*/.git/*' -prune -o -iname '*영수증*' -printf '%y %p\n'
find <PROJECT_ROOT>/runs -type f -name adapter_model.safetensors -printf '%p %s bytes\n'
```

## Next Step Needed

To rerun the benchmark, restore or provide one of the following:

1. The KORIE OCR test split files plus a manifest with image paths and ground-truth text.
2. The deleted temporary KORIE benchmark directory from the prior run.
3. The original source/download procedure for the KORIE OCR test split, so a new manifest can be rebuilt.

After the KORIE data is restored, the 50K adapter can be evaluated with Granite/Docling plus PEFT adapter loading, using the same CER/WER/exact-match metrics as the previous benchmark.
