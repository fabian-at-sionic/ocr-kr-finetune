#!/usr/bin/env bash
set -euo pipefail

ROOT="/workspace/ocr-bench"
TARGET="$ROOT/dataset/aihub_88_public_admin_ocr"
MANIFEST="$TARGET/manifest.json"
WORKROOT="$TARGET/.parallel"
DATASET_KEY="88"
BASE_URL="https://api.aihub.or.kr/down/0.6/${DATASET_KEY}.do"
CURL_COMMON=(--silent --show-error --location --fail --http1.1 --connect-timeout 30 --speed-time 180 --speed-limit 1024)
PARALLEL="${AIHUB_PARALLEL:-3}"
FILE_RETRY_DELAY="${AIHUB_FILE_RETRY_DELAY:-10}"

mkdir -p "$TARGET" "$WORKROOT"

API_KEY="$(sed -n 's/^AIHUB_API_KEY[[:space:]]*=[[:space:]]*//p' "$ROOT/.env" | tr -d ' "')"
if [[ -z "$API_KEY" ]]; then
  echo "AIHUB_API_KEY was not found in $ROOT/.env" >&2
  exit 1
fi

file_complete() {
  local name="$1"
  local expected="$2"
  python3 - "$TARGET" "$name" "$expected" <<'PY2'
import sys
from pathlib import Path

target = Path(sys.argv[1])
name = sys.argv[2]
expected = int(sys.argv[3])
stack = [target]
while stack:
    current = stack.pop()
    for path in current.iterdir():
        if ".partial" in path.parts or ".parallel" in path.parts:
            continue
        if path.is_dir():
            stack.append(path)
        elif path.name == name and path.stat().st_size >= expected:
            raise SystemExit(0)
raise SystemExit(1)
PY2
}

merge_parts() {
  local extract_dir="$1"
  python3 - "$extract_dir" <<'PY2'
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
groups = {}
for path in root.rglob("*"):
    if not path.is_file():
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
    print(f"merged {output.relative_to(root)}", flush=True)
PY2
}

move_result() {
  local extract_dir="$1"
  local file_name="$2"
  local expected="$3"
  python3 - "$extract_dir" "$TARGET" "$file_name" "$expected" <<'PY2'
import shutil
import sys
from pathlib import Path

extract = Path(sys.argv[1])
target = Path(sys.argv[2])
name = sys.argv[3]
expected = int(sys.argv[4])

matches = [p for p in extract.rglob("*") if p.is_file() and p.name == name and p.stat().st_size >= expected]
if not matches:
    raise SystemExit(f"merged file not found or too small: {name}")
source = matches[0]
dest = target / source.relative_to(extract)
dest.parent.mkdir(parents=True, exist_ok=True)
if dest.exists() and dest.stat().st_size >= expected:
    print(f"already present {dest.relative_to(target)}", flush=True)
else:
    tmp = dest.with_name(dest.name + ".move_tmp")
    if tmp.exists():
        tmp.unlink()
    shutil.move(str(source), str(tmp))
    tmp.replace(dest)
    print(f"stored {dest.relative_to(target)}", flush=True)
PY2
}

download_one() {
  local file_sn="$1"
  local file_size="$2"
  local file_name="$3"

  if file_complete "$file_name" "$file_size"; then
    echo "skip complete fileSn=$file_sn name=$file_name"
    return 0
  fi

  local workdir="$WORKROOT/$file_sn"
  local tar_path="$workdir/download.tar"
  local extract_dir="$workdir/extract"
  local download_url="${BASE_URL}?fileSn=${file_sn}"
  mkdir -p "$workdir"

  echo "download start fileSn=$file_sn size=$file_size name=$file_name"
  if [[ -s "$tar_path" ]]; then
    set +e
    curl "${CURL_COMMON[@]}" --continue-at - \
      --output "$tar_path" \
      --header "apikey:${API_KEY}" \
      "$download_url"
    local curl_status=$?
    set -e
    if [[ "$curl_status" -eq 33 ]]; then
      echo "server rejected resume for fileSn=$file_sn; restarting this file from byte 0"
      rm -f "$tar_path"
      curl "${CURL_COMMON[@]}" --retry 10 --retry-delay 10 --retry-all-errors \
        --output "$tar_path" \
        --header "apikey:${API_KEY}" \
        "$download_url"
    elif [[ "$curl_status" -ne 0 ]]; then
      return "$curl_status"
    fi
  else
    curl "${CURL_COMMON[@]}" --retry 10 --retry-delay 10 --retry-all-errors \
      --output "$tar_path" \
      --header "apikey:${API_KEY}" \
      "$download_url"
  fi

  echo "extract fileSn=$file_sn"
  rm -rf "$extract_dir"
  mkdir -p "$extract_dir"
  tar -xf "$tar_path" -C "$extract_dir"
  merge_parts "$extract_dir"
  move_result "$extract_dir" "$file_name" "$file_size"

  if ! file_complete "$file_name" "$file_size"; then
    echo "downloaded file did not validate: fileSn=$file_sn name=$file_name expected=$file_size" >&2
    return 1
  fi

  rm -rf "$workdir"
  echo "complete fileSn=$file_sn name=$file_name"
}

if [[ "${1:-}" == "--one" ]]; then
  shift
  download_one "$@"
  exit $?
fi

missing_files() {
  jq -r '.list | sort_by(.fileSize | tonumber)[] | [.fileSn, .fileSize, .streFileNm] | @tsv' "$MANIFEST" |
  while IFS=$'	' read -r file_sn file_size file_name; do
    if file_complete "$file_name" "$file_size"; then
      echo "skip complete fileSn=$file_sn name=$file_name" >&2
    else
      printf '%s	%s	%s
' "$file_sn" "$file_size" "$file_name"
    fi
  done
}

if [[ "$PARALLEL" -le 1 ]]; then
  while true; do
    had_missing=0
    had_failure=0
    while IFS=$'	' read -r file_sn file_size file_name; do
      had_missing=1
      if ! download_one "$file_sn" "$file_size" "$file_name"; then
        had_failure=1
        echo "defer retry fileSn=$file_sn in ${FILE_RETRY_DELAY}s name=$file_name" >&2
        sleep "$FILE_RETRY_DELAY"
      fi
    done < <(missing_files)

    if [[ "$had_missing" -eq 0 ]]; then
      break
    fi
    if [[ "$had_failure" -eq 1 ]]; then
      echo "retrying remaining missing files in ${FILE_RETRY_DELAY}s" >&2
      sleep "$FILE_RETRY_DELAY"
    fi
  done
else
  missing_files | xargs -r -P "$PARALLEL" -n 3 bash "$0" --one
fi

echo "all files complete"
