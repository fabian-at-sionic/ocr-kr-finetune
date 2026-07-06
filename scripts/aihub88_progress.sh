#!/usr/bin/env bash
set -euo pipefail

ROOT="/workspace/ocr-bench"
TARGET="$ROOT/dataset/aihub_88_public_admin_ocr"
MANIFEST="$TARGET/manifest.json"
STATE="$TARGET/.download_state"

python3 - "$ROOT" "$TARGET" "$MANIFEST" "$STATE" <<'PY'
import json
import os
import subprocess
import sys
import time
from pathlib import Path

root = Path(sys.argv[1])
target = Path(sys.argv[2])
manifest = Path(sys.argv[3])
state = Path(sys.argv[4])

items = json.loads(manifest.read_text())["list"]
total = sum(int(item["fileSize"]) for item in items)

files_by_name = {}
for path in target.rglob("*"):
    if ".partial" in path.parts:
        continue
    if path.is_file():
        files_by_name.setdefault(path.name, []).append(path)

completed = 0
completed_count = 0
for item in items:
    expected = int(item["fileSize"])
    if any(path.stat().st_size >= expected for path in files_by_name.get(item["streFileNm"], [])):
        completed += expected
        completed_count += 1

partial = 0
partial_dir = target / ".partial"
if partial_dir.exists():
    partial += sum(path.stat().st_size for path in partial_dir.glob("*.download.tar") if path.is_file())
parallel_dir = target / ".parallel"
if parallel_dir.exists():
    partial += sum(path.stat().st_size for path in parallel_dir.glob("*/download.tar") if path.is_file())

downloaded = min(total, completed + partial)
remaining = max(0, total - downloaded)

start_epoch = int(time.time())
initial = 0
if state.exists():
    for line in state.read_text().splitlines():
        if line.startswith("start_epoch="):
            start_epoch = int(line.split("=", 1)[1])
        elif line.startswith("initial_bytes="):
            initial = int(line.split("=", 1)[1])

elapsed = max(1, int(time.time()) - start_epoch)
delta = max(0, downloaded - initial)
rate = delta / elapsed
eta_seconds = int(remaining / rate) if rate > 0 and remaining > 0 else None

def human_bytes(value):
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(value)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024

def human_eta(seconds):
    if seconds is None:
        return "unknown"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def du(path):
    if not path.exists():
        return 0
    out = subprocess.check_output(["du", "-sb", str(path)], text=True)
    return int(out.split()[0])

percent = (downloaded / total * 100) if total else 0
print(f"downloaded_bytes={downloaded}")
print(f"total_bytes={total}")
print(f"remaining_bytes={remaining}")
print(f"percent={percent:.2f}")
print(f"completed_files={completed_count}/{len(items)}")
print(f"downloaded_human={human_bytes(downloaded)}")
print(f"total_human={human_bytes(total)}")
print(f"remaining_human={human_bytes(remaining)}")
print(f"eta={human_eta(eta_seconds)}")
print(f"rate_human={human_bytes(rate)}/s")
print(f"repo_storage_human={human_bytes(du(root))}")
print(f"dataset_storage_human={human_bytes(du(root / 'dataset'))}")
PY
