---
dataset_info:
  features:
  - name: image
    dtype: image
  - name: question
    dtype: string
  - name: answer
    dtype: string
  - name: source_dataset
    dtype: string
  - name: source_split
    dtype: string
  - name: source_index
    dtype: int64
  - name: render_text
    dtype: string
  - name: template
    dtype: string
  - name: width
    dtype: int64
  - name: height
    dtype: int64
  splits:
  - name: train
    num_bytes: 6365695974.0
    num_examples: 200000
  - name: validation
    num_bytes: 15884681.0
    num_examples: 500
  download_size: 6292328755
  dataset_size: 6381580655.0
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
  - split: validation
    path: data/validation-*
---
