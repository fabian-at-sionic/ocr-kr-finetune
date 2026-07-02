# Stage 1 50K Rebuild Classification

Date: 2026-07-01

## Active Run Classification

This run is **Stage 1** by the project terminology:

- Stage 1 = non-AIHub Korean OCR adaptation using Jiwon/AbdullahRian manifests.
- Stage 2A = AIHub 91 printed word/region OCR using .
- Stage 2B = AIHub 91 full-page detection/structured OCR.

The active run is not Stage 2A and not Stage 2B.

## Active Command

trainable params: 4,884,480 || all params: 262,401,600 || trainable%: 1.8615

## Data And Adapter Source

- Manifest: 
- Output directory: 
- Adapter source path: none. This is Stage 1, so it starts from base model  and creates a new LoRA adapter.
- Rows come from AIHub 91: no.
- Row sources: 25K Jiwon-Kang clean synthetic Korean OCR + 25K AbdullahRian real cropped Korean OCR.
- Frozen baseline rows: excluded by manifest summary.

## Latest Observed Progress

Latest logged step at time of this note: 60/2500, 2.40% complete.

No interrupt condition was met: the manifest is correct for Stage 1, the data is not frozen baseline data, this is not a Stage 2A run that should start from the 50K Stage 1 adapter, and the output path is unique under .
