#!/usr/bin/env bash
# Stage 3: independent confirmation of the per-benchmark tuned choice (12 fresh rounds).
set -euo pipefail
cd "$(dirname "$0")/.."
export TIMING_DIR=timing-confirm
date -u +'start %FT%TZ' > logs/timing-confirm.txt; uptime >> logs/timing-confirm.txt
for b in $(grep -v '^#' configs/benchmarks.tsv | cut -f1); do
  scripts/time.sh "$b" 12 "full,o3,lto_inl,tuned" >> logs/timing-confirm.txt
done
date -u +'end %FT%TZ' >> logs/timing-confirm.txt; uptime >> logs/timing-confirm.txt
