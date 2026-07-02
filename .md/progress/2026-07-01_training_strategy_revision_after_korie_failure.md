# Training Strategy Revision After KORIE 50K Failure

Date: 2026-07-01

## Trigger

The completed Stage 1 50K LoRA adapter failed the KORIE receipt-field OCR benchmark:

```text
Exact match: 0.00%
CER: 2529.08%
WER: 345.65%
Failure mode: repeated fragments such as amoto... and iginal...
```

This means the prior strategy overtrusted training completion and loss curves. The 50K final adapter is not automatically valid as the parent for Stage 2.

## Revised Policy

Training is now checkpoint-gated:

```text
train bounded shard -> evaluate checkpoint -> promote only if generation is sane -> continue
```

A checkpoint is rejected if it shows:

- repeated-token generation,
- generated control/image tokens,
- outputs that run to max token length,
- CER/WER regression versus base or previous accepted checkpoint,
- zero/effectively zero exact match on easy samples,
- invalid JSON/schema for structured tasks.

## Immediate Actions

1. Stop any ongoing Stage 2A run safely at the next checkpoint or save `interrupted_adapter`.
2. Evaluate candidate parent checkpoints:
   - base model,
   - Stage 1 checkpoint-3000,
   - Stage 1 final_adapter,
   - retained Stage 1 interrupted adapters,
   - Stage 2A checkpoints 100/200/300/latest.
3. Select the best checkpoint by bounded eval metrics, not timestamp.
4. Resume Stage 2A only from the accepted checkpoint.
5. Keep Stage 2B limited to smoke/schema work until Stage 2A has an accepted checkpoint.

## Docs Updated

- `nonaihub_training_plan.md`
- `buckets.md`
- `train_instruction.md`
- `MD/TODO.md`

## Non-Negotiable Rule

No future multi-hour training job may be launched solely because a previous run completed or because loss appears acceptable. Evaluation gates come first.
