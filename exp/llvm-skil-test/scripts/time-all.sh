#!/usr/bin/env bash
# Serial timing of all benchmarks (never concurrent). Fortran workloads add no-FMA native variants.
set -euo pipefail
cd "$(dirname "$0")/.."
base=full,full_control,o3,o2,os,o3_native,lto,lto_native
date -u +'start %FT%TZ' > logs/timing.txt; uptime >> logs/timing.txt
for b in $(grep -v '^#' configs/benchmarks.tsv | cut -f1); do
  case $b in 436.cactusADM|465.tonto|481.wrf) v=$base,o3_native_nofma,lto_native_nofma;; *) v=$base;; esac
  scripts/time.sh "$b" 7 "$v" >> logs/timing.txt
done
date -u +'end %FT%TZ' >> logs/timing.txt; uptime >> logs/timing.txt
