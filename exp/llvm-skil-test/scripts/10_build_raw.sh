#!/usr/bin/env bash
# Step 1: source -> per-TU bitcode -> merged raw.bc (no middle-end passes).
# Also builds an independent GCC -O2 oracle for output checking, and prepares
# each workload's working directory/input.
# RAW=raw.tbaa STRICT_ALIASING=1 builds the analysis-driven variant without
# -fno-strict-aliasing (enables TBAA); oracle/work dirs are then left untouched.
source "$(dirname "$0")/env.sh"
RAW=${RAW:-raw}
if [[ ${STRICT_ALIASING:-0} == 1 ]]; then
  FE_FLAGS=("${FE_FLAGS[@]/-fno-strict-aliasing/-fstrict-aliasing}")
fi
mkdir -p "$DATA" "$EXP_ROOT/logs"
gcc() { [[ $RAW == raw ]] && command gcc "$@" || true; }

fe() { # fe <outdir> <extra flags...> -- <sources...>
  local out=$1; shift; mkdir -p "$out"; ( cd "$out" && "$CLANG" "${FE_FLAGS[@]}" "$@" -emit-llvm -c ); }

build_one() {
  local b=$1 d="$DATA/$1"; rm -rf "$d/$RAW.tu"; mkdir -p "$d/$RAW.tu" "$d/work"
  case $b in
  462.libquantum)
    fe "$d/$RAW.tu" -std=gnu89 "$SPEC"/modified/462.libquantum/src/*.c
    gcc -std=gnu89 -O2 -fno-strict-aliasing -fcommon -ffp-contract=off -march=x86-64-v3 \
      -DSPEC_CPU -DSPEC_CPU_LINUX -DSPEC_CPU_LP64 "$SPEC"/modified/462.libquantum/src/*.c -lm -o "$d/oracle" ;;
  403.gcc)
    local s="$SPEC/modified/403.gcc/src"
    fe "$d/$RAW.tu" -std=gnu89 -DPOSIX -DSPEC_CPU_HAVE_BOOL -I"$s" "$s"/*.c
    gcc -std=gnu89 -O2 -fno-strict-aliasing -fcommon -ffp-contract=off -march=x86-64-v3 \
      -DSPEC_CPU -DSPEC_CPU_LINUX -DSPEC_CPU_LP64 -DPOSIX -DSPEC_CPU_HAVE_BOOL -I"$s" "$s"/*.c -lm -o "$d/oracle" ;;
  445.gobmk)
    local s="$SPEC/modified/445.gobmk/src" inc=()
    for x in include engine interface patterns sgf utils; do inc+=(-I"$s/$x"); done
    for x in engine interface patterns sgf utils; do
      fe "$d/$RAW.tu/$x" -std=gnu89 -DHAVE_CONFIG_H -DWANT_STDC_PROTO "${inc[@]}" "$s/$x"/*.c; done
    gcc -std=gnu89 -O2 -fno-strict-aliasing -fcommon -ffp-contract=off -march=x86-64-v3 \
      -DSPEC_CPU -DSPEC_CPU_LINUX -DSPEC_CPU_LP64 -DHAVE_CONFIG_H -DWANT_STDC_PROTO "${inc[@]}" \
      "$s"/{engine,interface,patterns,sgf,utils}/*.c -lm -o "$d/oracle" ;;
  456.hmmer)
    local s="$SPEC/modified/456.hmmer/src"
    fe "$d/$RAW.tu" -std=gnu89 -I"$s" "$s"/*.c
    gcc -std=gnu89 -O2 -fno-strict-aliasing -fcommon -ffp-contract=off -march=x86-64-v3 \
      -DSPEC_CPU -DSPEC_CPU_LINUX -DSPEC_CPU_LP64 -I"$s" "$s"/*.c -lm -o "$d/oracle"
    [[ $RAW == raw ]] && cp "$SPEC/modified/456.hmmer/Docs/datasets/ig.hmm" "$d/work/ig.orig" || true ;;
  401.bzip2)
    local s="$SPEC/original/401.bzip2/bzip2-1.0.3"
    local f=(blocksort.c huffman.c crctable.c randtable.c compress.c decompress.c bzlib.c bzip2.c)
    fe "$d/$RAW.tu" -D_FILE_OFFSET_BITS=64 "${f[@]/#/$s/}"
    gcc -O2 -fno-strict-aliasing -fcommon -ffp-contract=off -march=x86-64-v3 -D_FILE_OFFSET_BITS=64 \
      "${f[@]/#/$s/}" -o "$d/oracle"
    [[ $RAW == raw ]] && for i in $(seq 1 32); do cat "$s"/sample{1,2,3}.ref; done > "$d/work/input.ref" || true ;;
  esac
  find "$d/$RAW.tu" -name '*.bc' | sort | xargs "$LINK" -o "$d/$RAW.bc"
  "${LLVM_DIS:-llvm-dis}" "$d/$RAW.bc" -o "$d/$RAW.ll"
  # The frontend must not have blocked optimisation (optnone / unroll.disable).
  if grep -qE '^attributes.* optnone|llvm.loop.unroll.disable' "$d/$RAW.ll"; then
    echo "WARN: $b raw.ll contains optnone/unroll.disable" >&2; fi
  sha256sum "$d/$RAW.bc"
}

for b in "${@:-${BENCHES[@]}}"; do
  echo "== $b"; build_one "$b" > "$EXP_ROOT/logs/$b.$RAW.log" 2>&1 || { echo "FAIL $b (see logs/$b.$RAW.log)"; tail -5 "$EXP_ROOT/logs/$b.$RAW.log"; }
  tail -1 "$EXP_ROOT/logs/$b.$RAW.log"
done
