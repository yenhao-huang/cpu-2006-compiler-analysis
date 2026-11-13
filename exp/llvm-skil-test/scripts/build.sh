#!/usr/bin/env bash
# Build one (benchmark, variant) from the repo's shared raw.bc.
# Usage: scripts/build.sh <bench> <variant>
set -euo pipefail
source "$(dirname "$0")/env.sh"
bench=$1 variant=$2
IFS=$'\t' read -r _ raw_dir v driver link_flags < <(awk -F'\t' -v b="$bench" '$1==b' "$EXP_ROOT/configs/benchmarks.tsv")
out="$EXP_ROOT/build/$bench"; log="$EXP_ROOT/logs/build/$bench"; mkdir -p "$out" "$log"
case "$variant" in
  full|o3) cp "$STUDY_ROOT/$raw_dir/$variant" "$out/$variant"; exit 0;;
  full_control) cp "$STUDY_ROOT/$raw_dir/full" "$out/full_control"; exit 0;;
esac
IFS=$'\t' read -r _ pipeline ir _ opt_extra < <(awk -F'\t' -v x="$variant" '$1==x' "$EXP_ROOT/configs/variants.tsv")
input="$STUDY_ROOT/$raw_dir/raw.bc"
# strict_native: native ISA, but no FMA for LLVM19/Flang workloads (bit-exact output)
if [ "$ir" = strict_native ]; then ir=native; [ "$v" = 19 ] && ir=native_nofma; fi
if [ "$ir" = native_nofma ]; then
  # Same ISA but no FMA for Flang functions, so `fmul/fadd contract` is not fused
  # and Fortran results stay bit-identical to the x86-64 reference.
  input="$out/raw.native_nofma.bc"
  if [ ! -s "$input" ]; then
    llvm-dis-$v "$STUDY_ROOT/$raw_dir/raw.bc" -o - \
      | sed -E 's/"target-cpu"="x86-64-v3"/"target-cpu"="alderlake"/g; s/"target-cpu"="x86-64"/"target-cpu"="alderlake" "target-features"="-fma"/g' \
      | llvm-as-$v -o "$input.$variant.tmp" && mv "$input.$variant.tmp" "$input"
  fi
elif [ "$ir" = native ]; then
  # Retarget every function to the measurement CPU (i7-14700K = Raptor Lake;
  # LLVM 14 has no raptorlake name, alderlake has the identical ISA).
  input="$out/raw.native.bc"
  if [ ! -s "$input" ]; then
    llvm-dis-$v "$STUDY_ROOT/$raw_dir/raw.bc" -o - \
      | sed -E 's/"target-cpu"="x86-64(-v3)?"/"target-cpu"="alderlake"/g' \
      | llvm-as-$v -o "$input.$variant.tmp" && mv "$input.$variant.tmp" "$input"
  fi
fi
extra=()
# shellcheck disable=SC2206
[ -n "${opt_extra:-}" ] && extra+=($opt_extra)
case "$pipeline" in *internalize*) extra+=(-internalize-public-api-list=main,_QQmain);; esac
opt-$v -passes="$pipeline" "${extra[@]}" "$input" -o "$out/$variant.opt.bc" 2> "$log/$variant.opt.log"
llc-$v -O=2 -filetype=obj -relocation-model=pic "$out/$variant.opt.bc" -o "$out/$variant.o" 2> "$log/$variant.llc.log"
# shellcheck disable=SC2086
$driver "$out/$variant.o" $link_flags -o "$out/$variant" 2> "$log/$variant.link.log"
echo "built $bench/$variant"
