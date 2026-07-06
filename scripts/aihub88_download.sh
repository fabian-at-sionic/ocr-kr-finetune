#!/usr/bin/env bash
set -euo pipefail

ROOT="/workspace/ocr-bench"
TARGET="$ROOT/dataset/aihub_88_public_admin_ocr"
MANIFEST="$TARGET/manifest.json"
PARTIAL="$TARGET/.partial"
STATE="$TARGET/.download_state"
DATASET_KEY="88"
BASE_URL="https://api.aihub.or.kr/down/0.6/${DATASET_KEY}.do"

mkdir -p "$TARGET" "$PARTIAL"

API_KEY="$(sed -n 's/^AIHUB_API_KEY[[:space:]]*=[[:space:]]*//p' "$ROOT/.env" | tr -d ' "')"
if [[ -z "$API_KEY" ]]; then
  echo "AIHUB_API_KEY was not found in $ROOT/.env" >&2
  exit 1
fi

if [[ ! -s "$MANIFEST" ]]; then
  if [[ -s /tmp/s3list.json ]]; then
    cp /tmp/s3list.json "$MANIFEST"
  else
    echo "Manifest is missing: $MANIFEST" >&2
    exit 1
  fi
fi

completed_bytes() {
  python3 - "$MANIFEST" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path

manifest = Path(sys.argv[1])
target = Path(sys.argv[2])
items = json.loads(manifest.read_text())["list"]
files_by_name = {}
for p in target.rglob("*"):
    if ".partial" in p.parts:
        continue
    if p.is_file():
        files_by_name.setdefault(p.name, []).append(p)

total = 0
for item in items:
    name = item["streFileNm"]
    expected = int(item["fileSize"])
    if any(p.stat().st_size >= expected for p in files_by_name.get(name, [])):
        total += expected
print(total)
PY
}

if [[ ! -s "$STATE" ]]; then
  printf 'start_epoch=%s\ninitial_bytes=%s\n' "$(date +%s)" "$(completed_bytes)" > "$STATE"
fi

merge_parts() {
  python3 - "$TARGET" <<'PY'
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
groups = {}
for path in root.rglob("*"):
    if ".partial" in path.parts or not path.is_file():
        continue
    match = re.match(r"^(?P<base>.+)\.part(?P<num>[0-9]+)$", path.name)
    if not match:
        continue
    key = path.with_name(match.group("base"))
    groups.setdefault(key, []).append((int(match.group("num")), path))

for output, parts in groups.items():
    parts.sort(key=lambda x: x[0])
    tmp = output.with_name(output.name + ".merge_tmp")
    with tmp.open("wb") as out:
        for _, part in parts:
            with part.open("rb") as src:
                while True:
                    chunk = src.read(16 * 1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
    tmp.replace(output)
    for _, part in parts:
        part.unlink()
    print(f"Merged {output.relative_to(root)}")
PY
}

file_complete() {
  local name="$1"
  local expected="$2"
  python3 - "$TARGET" "$name" "$expected" <<'PY'
import sys
from pathlib import Path

target = Path(sys.argv[1])
name = sys.argv[2]
expected = int(sys.argv[3])
stack = [target]
while stack:
    current = stack.pop()
    for path in current.iterdir():
        if ".partial" in path.parts:
            continue
        if path.is_dir():
            stack.append(path)
        elif path.name == name and path.stat().st_size >= expected:
            raise SystemExit(0)
raise SystemExit(1)
PY
}

cd "$TARGET"

jq -r '.list | sort_by(.fileSize | tonumber)[] | [.fileSn, .fileSize, .streFileNm] | @tsv' "$MANIFEST" |
while IFS=$'\t' read -r file_sn file_size file_name; do
  if file_complete "$file_name" "$file_size"; then
    rm -f "$PARTIAL/${file_sn}.download.tar"
    echo "skip complete fileSn=$file_sn name=$file_name"
    continue
  fi

  tar_path="$PARTIAL/${file_sn}.download.tar"
  echo "download start fileSn=$file_sn size=$file_size name=$file_name"
  download_url="${BASE_URL}?fileSn=${file_sn}"
  if [[ -s "$tar_path" ]]; then
    set +e
    curl --location --continue-at - --fail --retry 10 --retry-delay 10 --retry-all-errors \
      --output "$tar_path" \
      --header "apikey:${API_KEY}" \
      "$download_url"
    curl_status=$?
    set -e
    if [[ "$curl_status" -eq 33 ]]; then
      echo "server rejected resume for fileSn=$file_sn; restarting this file from byte 0"
      rm -f "$tar_path"
      curl --location --fail --retry 10 --retry-delay 10 --retry-all-errors \
        --output "$tar_path" \
        --header "apikey:${API_KEY}" \
        "$download_url"
    elif [[ "$curl_status" -ne 0 ]]; then
      exit "$curl_status"
    fi
  else
    curl --location --fail --retry 10 --retry-delay 10 --retry-all-errors \
      --output "$tar_path" \
      --header "apikey:${API_KEY}" \
      "$download_url"
  fi

  echo "extract fileSn=$file_sn"
  tar -xf "$tar_path" -C "$TARGET"
  merge_parts

  if ! file_complete "$file_name" "$file_size"; then
    echo "downloaded file did not validate: fileSn=$file_sn name=$file_name expected=$file_size" >&2
    exit 1
  fi

  rm -f "$tar_path"
  echo "complete fileSn=$file_sn name=$file_name"
done

echo "all files complete"
