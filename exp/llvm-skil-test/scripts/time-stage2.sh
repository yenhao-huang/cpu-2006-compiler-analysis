#!/usr/bin/env bash
# Stage 2: tuning knobs on top of strict LTO+native (bit-exact variants only), 10 rounds.
set -euo pipefail
cd "$(dirname "$0")/.."
export TIMING_DIR=timing-stage2
date -u +'start %FT%TZ' > logs/timing-stage2.txt; uptime >> logs/timing-stage2.txt
for b in $(grep -v '^#' configs/benchmarks.tsv | cut -f1); do
  case $b in 436.cactusADM|465.tonto|481.wrf) s=_nofma;; *) s=;; esac
  scripts/time.sh "$b" 10 "full,o3,o2,o3_native$s,lto_native$s,lto_inl,lto_noslp,lto_unroll" >> logs/timing-stage2.txt
done
date -u +'end %FT%TZ' >> logs/timing-stage2.txt; uptime >> logs/timing-stage2.txt
