# Prepared Baseline Evaluation Set

This folder contains normalized OCR evaluation inputs prepared from the datasets under `baseline_testing/`.

Use this manifest for baseline model evaluation:

`<PROJECT_ROOT>/dataset/hangul_recognition/baseline_testing/prepared/manifests/baseline_eval.jsonl`

Each JSONL row has:

- `dataset`: source dataset name
- `split`: evaluation split label
- `sample_id`: stable local sample id
- `image_path`: absolute path to the prepared image file
- `text`: ground-truth OCR text
- `prompt`: default OCR prompt for VLM/document models
- `source`: original source row or tar member metadata

Prepared sample counts:

- `Jiwon-Kang/OCR-Synthetic-Rendered-Korean-200K`: 500 validation samples
- `AbdullahRian/Korean.OCR.Img.text.pair`: 500 sampled image/text pairs
- Combined baseline manifest: 1,000 samples

The AbdullahRian dataset also has a full tar index here:

`<PROJECT_ROOT>/dataset/hangul_recognition/baseline_testing/prepared/manifests/abdullahrian_full_tar_index.jsonl`

That index records every image/text pair inside the downloaded tar shards, without extracting all of them into duplicate files.

To regenerate or resize the prepared set:

```bash
<PROJECT_ROOT>/.venv-baseline-prep/bin/python \
  <PROJECT_ROOT>/dataset/hangul_recognition/baseline_testing/prepare_baseline_eval.py \
  --jiwon-limit 500 \
  --abdullah-limit 500
```

For a larger AbdullahRian baseline sample, increase `--abdullah-limit`. Use `--jiwon-limit 500` for the full current Jiwon validation split.

## Prediction Evaluation

After running a model, write predictions as JSONL:

```jsonl
{"sample_id":"jiwon_validation_000000","prediction":"model OCR text here"}
```

Then score them:

```bash
python3 <PROJECT_ROOT>/dataset/hangul_recognition/baseline_testing/prepared/evaluate_predictions.py \
  --predictions /path/to/predictions.jsonl
```

The evaluator reports overall and per-dataset exact-match rate and CER.
