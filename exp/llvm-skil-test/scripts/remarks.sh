#!/usr/bin/env bash
# Skill step "Optimization Remarks": rerun opt with -pass-remarks-output for
# full / o3 / lto_native and count Passed/Missed remarks per pass.
# Usage: scripts/remarks.sh <bench>   -> prints TSV rows: bench variant pass kind count
set -euo pipefail
source "$(dirname "$0")/env.sh"
bench=$1
IFS=$'\t' read -r _ raw_dir v _ _ < <(awk -F'\t' -v b="$bench" '$1==b' "$EXP_ROOT/configs/benchmarks.tsv")
pf="$STUDY_ROOT/configs/pipelines.tsv"; [ "$v" = 19 ] && pf="$STUDY_ROOT/configs/pipelines-llvm19.tsv"
d="$EXP_ROOT/build/$bench/remarks"; mkdir -p "$d"
filter='^(inline|loop-vectorize|slp-vectorizer|licm|loop-unroll|gvn)$'
run() { # variant pipeline input extra...
  local var=$1 pipe=$2 in=$3; shift 3
  opt-$v -passes="$pipe" "$@" -pass-remarks-output="$d/$var.yaml" -pass-remarks-filter="$filter" \
    "$in" -o /dev/null 2>/dev/null
  awk -v b="$bench" -v var="$var" '
    /^--- !/ { kind=substr($2,2) }
    /^Pass:/  { n[$2 "\t" kind]++ }
    END { for (k in n) print b "\t" var "\t" k "\t" n[k] }' "$d/$var.yaml" | sort
  rm -f "$d/$var.yaml"
}
run full "$(awk -F'\t' '$1=="full"{print $2}' "$pf")" "$STUDY_ROOT/$raw_dir/raw.bc"
run o3 'default<O3>' "$STUDY_ROOT/$raw_dir/raw.bc"
run lto_native 'lto-pre-link<O3>,internalize,lto<O3>' "$EXP_ROOT/build/$bench/raw.native.bc" -internalize-public-api-list=main,_QQmain
