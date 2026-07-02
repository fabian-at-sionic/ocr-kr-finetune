# Agent Instructions

This repository is in a clean-restart state. Preserve local dataset and model assets unless the user explicitly asks to delete or move them.

The workspace is constrained to a single container with an effective memory/GPU-resource ceiling of **267.7 GB** and a dataset-storage cap of **700 GB** under `/workspace/ocr-bench/dataset`.

Avoid tasks that can exceed current memory/VRAM resources or push dataset storage over 700 GB, including unbounded downloads, large extractions, full materialization of generated crops/tiles, concurrent large-model inference, or full-dataset training without a resource estimate.

For heavy work, check resources first with `free -h`, `nvidia-smi`, and targeted `du` commands, then run bounded shards before scaling.
