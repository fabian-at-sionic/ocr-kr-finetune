# Hangul Recognition Download Status

Manifest used: `<PROJECT_ROOT>/.json/DOWNLOAD_hangul_recognition.json`

## Completed public downloads

- `Jiwon-Kang/OCR-Synthetic-Rendered-Korean-200K`
  - Local path: `<PROJECT_ROOT>/dataset/hangul_recognition/training/Jiwon-Kang_OCR-Synthetic-Rendered-Korean-200K`
  - Downloaded files: 7 train Parquet shards and 1 validation Parquet shard
  - Current local size: about 12G

- `AbdullahRian/Korean.OCR.Img.text.pair`
  - Local path: `<PROJECT_ROOT>/dataset/hangul_recognition/training/AbdullahRian_Korean_OCR_Img_text_pair`
  - Downloaded files: 128 `ocr-shard-*.tar` shards
  - Current local size: about 19G

## Metadata-only public clones

These Hugging Face repos were cloned with LFS smudge disabled, so their Git metadata and LFS pointers are present, but the large dataset blobs are not fully downloaded.

- `jeina/korean_ocr_public`
  - Local path: `<PROJECT_ROOT>/dataset/hangul_recognition/training/jeina_korean_ocr_public`
  - Current local size: about 941K

- `hyeongyeolryu/korean_outdoor_ocr`
  - Local path: `<PROJECT_ROOT>/dataset/hangul_recognition/training/hyeongyeolryu_korean_outdoor_ocr`
  - Current local size: about 1.2M

- `jeina/korean_ocr_public_3`
  - Local path: `<PROJECT_ROOT>/dataset/hangul_recognition/training/jeina_korean_ocr_public_3`
  - Current local size: about 1020K

## Partial public clone

- `jeina/korean_ocr_public_2`
  - Local path: `<PROJECT_ROOT>/dataset/hangul_recognition/training/jeina_korean_ocr_public_2`
  - Current local size: about 7.5G
  - Note: the initial full LFS clone was interrupted after it remained quiet for several minutes. The repo is present, but the ZIP files are still LFS pointer-sized in the working tree. This dataset declares very large LFS files, including multi-GB ZIPs.
