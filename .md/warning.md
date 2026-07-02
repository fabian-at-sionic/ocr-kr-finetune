# Container Resource Warning

This project runs inside a single restricted container. Agents must distinguish memory/VRAM limits from dataset storage limits. Agents must assume the effective container memory/VRAM ceiling is **267.7 GB** and the project dataset-storage cap is **700 GB**. Do not start tasks that can exceed either limit.

## Required Before Any Task

Before executing downloads, preprocessing, baseline inference, training, evaluation, extraction, tiling, or large file operations, every agent must read this file and consider the current resource state.

For resource-heavy work, check the relevant limits first:

```bash
free -h
nvidia-smi
du -h --max-depth=2 <PROJECT_ROOT> | sort -hr | head -40
```

## Hard Rules

- Do not run jobs that can exceed the single-container memory/VRAM ceiling of **267.7 GB**.
- Do not let datasets under `<PROJECT_ROOT>/dataset` exceed the project dataset-storage cap of **700 GB**.
- Do not load multiple large OCR/VLM models at the same time unless the current `nvidia-smi` output proves it is safe.
- Do not launch broad AIHub downloads, mass extraction, massive crop/tiling generation, or full-dataset training without estimating memory impact and dataset-storage growth first. Full AIHub downloads are allowed only if the resulting dataset storage remains under **700 GB**.
- Do not materialize all crops/tiles for multi-TB datasets by default. Prefer manifests, streaming, lazy transforms, or bounded caches.
- Do not run PaddleOCR-VL, Granite/Docling baselines, and training jobs concurrently unless explicitly approved after checking resources.
- If a task may exceed the current container, stop and report the expected memory/storage pressure before proceeding.

## Current Known Risk

PaddleOCR-VL baseline inference can use roughly **20 GB VRAM** by itself. Running it alongside multiple Docling/Granite jobs increases GPU memory use quickly. Treat concurrent VLM/OCR inference as resource-heavy.

## Preferred Pattern

1. Inspect resource usage.
2. Estimate peak memory, VRAM, and dataset-storage growth against the **700 GB** dataset cap.
3. Run one bounded job or a small shard first.
4. Confirm outputs and usage.
5. Scale incrementally.


## Dataset Storage Cap

The dataset storage cap is **700 GB** for `<PROJECT_ROOT>/dataset`. This is separate from the **267.7 GB** memory/VRAM ceiling. Before downloading AIHub or other large datasets, estimate compressed and extracted size. Prefer label-first downloads, selected shards, streaming, and bounded caches when full extraction would approach the cap.
