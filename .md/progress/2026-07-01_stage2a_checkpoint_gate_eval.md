# Stage 2A Checkpoint-Gated Evaluation

Date: 2026-07-01

## Stop State

Stage 2A AIHub91 region training was halted safely after latest logged step 340/1563.

Preserved outputs:

- runs/kept_checkpoints/stage2a_aihub91_region_50k_from_stage1_50k_v3_bs16_ga2_512_20260701T0745Z/checkpoint-100
- runs/kept_checkpoints/stage2a_aihub91_region_50k_from_stage1_50k_v3_bs16_ga2_512_20260701T0745Z/checkpoint-200
- runs/kept_checkpoints/stage2a_aihub91_region_50k_from_stage1_50k_v3_bs16_ga2_512_20260701T0745Z/checkpoint-300
- runs/kept_checkpoints/stage2a_aihub91_region_50k_from_stage1_50k_v3_bs16_ga2_512_20260701T0745Z/interrupted_adapter

No checkpoint or output directory was deleted.

## Evaluation Setup

Script:

- scripts/evaluate_checkpoint_gate_ocr.py

Output:

- runs/eval/checkpoint_gate_stage2a_20260701T0935Z/metrics.json

Samples:

- AIHub91 region validation: 20 samples from dataset/aihub/processed/manifests/aihub91_printed_val_region_ocr.jsonl
- KORIE: 20 samples from dataset/external/KORIE/ocr_test_manifest_smoke20.jsonl

Generation:

- max_new_tokens: 96
- batch_size: 4
- special image/control tokens suppressed during generation

## Results

| Adapter | AIHub CER | AIHub Exact | AIHub Rep | AIHub Blank | AIHub Avg Len | KORIE CER | KORIE Exact | KORIE Rep | KORIE Blank | KORIE Avg Len |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| stage1_checkpoint_3000 | 70.7593 | 0.00% | 100.00% | 0.00% | 382.30 | 41.4677 | 0.00% | 100.00% | 0.00% | 385.70 |
| stage1_final_adapter | 72.1204 | 0.00% | 100.00% | 0.00% | 389.65 | 39.9247 | 0.00% | 100.00% | 0.00% | 371.35 |
| stage2a_checkpoint_100 | 1.0000 | 0.00% | 0.00% | 100.00% | 0.00 | 1.0000 | 0.00% | 0.00% | 100.00% | 0.00 |
| stage2a_checkpoint_200 | 40.3333 | 0.00% | 90.00% | 0.00% | 217.90 | 25.3656 | 0.00% | 90.00% | 0.00% | 236.45 |
| stage2a_checkpoint_300 | 2.6944 | 0.00% | 15.00% | 45.00% | 11.40 | 1.1882 | 0.00% | 0.00% | 90.00% | 2.05 |
| stage2a_interrupted_adapter | 2.5833 | 0.00% | 15.00% | 5.00% | 12.45 | 2.2151 | 0.00% | 25.00% | 45.00% | 15.00 |

## Sample Failure Patterns

Stage 1 checkpoint-3000 and final adapter still show severe repeated Latin/control-like text such as `amotoamoto...`.

Stage 2A checkpoint-100 collapses to blank output.

Stage 2A checkpoint-200 reintroduces repetition, with outputs containing repeated `assistant`, `user`, and punctuation fragments.

Stage 2A checkpoint-300 reduces repetition but is mostly blank on KORIE.

Stage 2A interrupted_adapter is less blank on AIHub than checkpoint-300 but emits replacement characters and has worse KORIE repetition.

## Recommendation

Do not resume long Stage 2A training yet.

If a scheduled checkpoint must be selected, checkpoint-300 is the least bad durable checkpoint among checkpoint-100/200/300 by combined CER and repetition behavior. It is still not a good OCR checkpoint because exact match is 0.00% and KORIE blank rate is 90.00% on this small sample.

The interrupted adapter is not recommended as a continuation point because it is not a scheduled checkpoint and shows replacement-character degeneration plus higher KORIE repetition.

The current evidence points to a broken or unstable adapter lineage rather than a simple need for more Stage 2A steps.
