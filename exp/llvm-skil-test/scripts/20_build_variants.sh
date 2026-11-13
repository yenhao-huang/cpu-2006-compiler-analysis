#!/usr/bin/env bash
# Step 2: raw.bc -> opt (variant pipeline) -> llc -O=2 -> link.  Every variant of a
# benchmark starts from the same raw.bc (the *_tbaa / best_* variants from raw.tbaa.bc, see 10_build_raw.sh).  "native" variants retarget the IR
# function attributes from x86-64-v3 to the host CPU before opt (the vectoriser
# cost model reads target-cpu from the function, so llc -mcpu alone is not enough).
# PGO variants: instrumented build -> training run (different input) -> profile use.
# Usage: 20_build_variants.sh [bench...]   (VARIANTS="o3 lto" to restrict)
source "$(dirname "$0")/env.sh"; source "$(dirname "$0")/workloads.sh"
HOST_CPU="$("$CLANG" -march=native -### -x c /dev/null 2>&1 | sed -n 's/.*"-target-cpu" "\([^"]*\)".*/\1/p')"
LINKLIBS=(-lm)

retarget() { # <dir> <raw> : <raw>.bc -> <raw>.native.bc
  local d=$1 r=$2
  [[ -f "$d/$r.native.bc" && "$d/$r.native.bc" -nt "$d/$r.bc" ]] && return
  sed -e "s/\"target-cpu\"=\"x86-64-v3\"/\"target-cpu\"=\"$HOST_CPU\"/g" \
      -e "s/\"tune-cpu\"=\"generic\"/\"tune-cpu\"=\"$HOST_CPU\"/g" "$d/$r.ll" > "$d/$r.native.ll"
  "${LLVM_AS:-llvm-as}" "$d/$r.native.ll" -o "$d/$r.native.bc"
}

build_variant() { # bench name target raw extra pipeline
  local b=$1 v=$2 tgt=$3 raw=$4 extra=$5 pipe=$6 d="$DATA/$1" log="$EXP_ROOT/logs/$1"
  mkdir -p "$d/bin" "$log"
  local in="$d/$raw.bc" mcpu=x86-64-v3 popt=() iflags=(-internalize-public-api-list=main) xflags=()
  if [[ $extra != - ]]; then read -ra xflags <<< "$extra"; fi
  if [[ $tgt == native ]]; then retarget "$d" "$raw"; in="$d/$raw.native.bc"; mcpu=$HOST_CPU; fi
  if [[ $v == *pgo* ]]; then
    local pd="$d/pgo-$v"; rm -rf "$pd"; mkdir -p "$pd"
    "$OPT" -passes="lto-pre-link<O3>" "${xflags[@]}" -pgo-kind=pgo-instr-gen-pipeline \
      -profile-file="$pd/%p.profraw" "$in" -o "$pd/instr.bc"
    "$LLC" -O=2 -mcpu="$mcpu" -filetype=obj -relocation-model=pic "$pd/instr.bc" -o "$pd/instr.o"
    "$CLANG" -fprofile-generate "$pd/instr.o" "${LINKLIBS[@]}" -o "$pd/instr"
    bash -c "$(train_cmd "$b" "$pd/instr")"
    "$PROFDATA" merge -o "$pd/merged.profdata" "$pd"/*.profraw
    popt=(-pgo-kind=pgo-instr-use-pipeline -profile-file="$pd/merged.profdata")
  fi
  "$OPT" -passes="$pipe" "${iflags[@]}" "${xflags[@]}" "${popt[@]}" \
    -pass-remarks-output="$log/$v.remarks.yaml" -stats \
    "$in" -o "$d/$v.opt.bc" 2> "$log/$v.opt.log"
  "$LLC" -O=2 -mcpu="$mcpu" -filetype=obj -relocation-model=pic "$d/$v.opt.bc" -o "$d/$v.o"
  "$CLANG" "$d/$v.o" "${LINKLIBS[@]}" -o "$d/bin/$v"
}

sel=" ${VARIANTS:-} "
for b in "${@:-${BENCHES[@]}}"; do
  while IFS=$'\t' read -r v tier tgt raw extra pipe; do
    [[ -z $v || $v == \#* ]] && continue
    [[ "$sel" != "  " && "$sel" != *" $v "* ]] && continue
    mkdir -p "$EXP_ROOT/logs/$b"; t0=$(date +%s)
    if build_variant "$b" "$v" "$tgt" "$raw" "$extra" "$pipe" > "$EXP_ROOT/logs/$b/$v.build.log" 2>&1; then
      printf '%-15s %-15s ok  (%ss)\n' "$b" "$v" $(( $(date +%s) - t0 ))
    else
      printf '%-15s %-15s FAIL\n' "$b" "$v"; tail -5 "$EXP_ROOT/logs/$b/$v.build.log"
    fi
  done < "$EXP_ROOT/configs/variants.tsv"
done
