#!/usr/bin/env bash
# Interleaved block timing: 1 warm-up round + ROUNDS rounds; each round runs every
# variant once in a fresh random order (order saved). Never run two benches at once.
# Usage: scripts/time.sh <bench> [rounds] [variants-csv]
set -euo pipefail
source "$(dirname "$0")/env.sh"
bench=$1; rounds=${2:-7}
variants=${3:-full,full_control,o3,o2,os,o3_native,lto,lto_native}
IFS=$'\t' read -r _ cwd prepare cmd < <(awk -F'\t' -v b="$bench" '$1==b' "$EXP_ROOT/configs/workloads.tsv")
cmd=${cmd//\{bin\}/$EXP_ROOT/build/$bench}
out="$EXP_ROOT/results/${TIMING_DIR:-timing}/$bench"; mkdir -p "$out"
cd "$STUDY_ROOT/$cwd"
for r in $(seq 0 "$rounds"); do
  order=$(tr , '\n' <<< "$variants" | shuf | paste -sd,)
  name=$([ "$r" = 0 ] && echo warmup || echo "round$r")
  echo "$order" > "$out/$name.order.txt"
  hyperfine --style none --runs 1 --prepare "$prepare" --parameter-list variant "$order" \
    --export-json "$out/$name.json" "$cmd" > /dev/null
done
echo "timed $bench"
