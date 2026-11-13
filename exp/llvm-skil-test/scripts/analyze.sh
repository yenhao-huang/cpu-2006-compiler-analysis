#!/usr/bin/env bash
# Paired analysis: within each round, ratio = T_variant / T_ref (ref = full and o3).
# speedup% = 100*(1/geomean(ratio) - 1): positive = variant faster than ref.
set -euo pipefail
source "$(dirname "$0")/env.sh"
R="$EXP_ROOT/results"
T=${1:-timing}   # timing dir under results/: timing (stage 1) or timing-stage2
P="$R/$T"        # output prefix
printf 'bench\tvariant\tref\tround\tratio\tt_variant\tt_ref\n' > "$P-paired-ratios.tsv"
for d in "$R"/"$T"/*/; do
  bench=$(basename "$d")
  for ref in full o3; do
    for f in "$d"/round*.json; do
      jq -r --arg b "$bench" --arg ref "$ref" --arg rd "$(basename "$f" .json)" '
        (.results[]|select(.parameters.variant==$ref)|.times[0]) as $t |
        .results[]|select(.parameters.variant!=$ref)|
        [$b,.parameters.variant,$ref,$rd,(.times[0]/$t),.times[0],$t]|@tsv' "$f"
    done
  done
done >> "$P-paired-ratios.tsv"
printf 'bench\tvariant\tref\tn\tgeomean_ratio\tmedian_ratio\tmin_ratio\tmax_ratio\tmedian_t_variant\n' > "$P-paired-summary.tsv"
tail -n +2 "$P-paired-ratios.tsv" | datamash -s -g 1,2,3 count 5 geomean 5 median 5 min 5 max 5 median 6 >> "$P-paired-summary.tsv"
# .text size of every built binary
printf 'bench\tvariant\ttext_bytes\n' > "$R/code-size.tsv"
for b in "$EXP_ROOT"/build/*/; do
  for v in full o3 o2 os o3_native lto lto_native o3_native_nofma lto_native_nofma lto_inl lto_noslp lto_unroll lto_inl_noslp lto_inl_unroll tuned; do
    [ -x "$b/$v" ] || continue
    printf '%s\t%s\t%s\n' "$(basename "$b")" "$v" "$(size -A "$b/$v" | awk '$1==".text"{print $2}')"
  done
done >> "$R/code-size.tsv"
echo "wrote $P-paired-summary.tsv"
