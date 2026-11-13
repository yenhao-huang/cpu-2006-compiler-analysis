#!/usr/bin/env bash
# Step 5: noise-free profile. Callgrind instruction counts (Ir) for every variant,
# plus a per-function hot list. Instruction count is not time (it ignores cache
# misses, branch mispredictions and SIMD width) but it is deterministic, which
# matters on a shared 2-vCPU cloud host where wall time is noisy.
# Usage: JOBS=2 50_callgrind.sh [bench...]
source "$(dirname "$0")/env.sh"; source "$(dirname "$0")/workloads.sh"
JOBS=${JOBS:-2}
cg="$EXP_ROOT/results/callgrind"; mkdir -p "$cg"
jobs_list=()
for b in "${@:-${BENCHES[@]}}"; do
  for x in "$DATA/$b"/bin/*; do
    # valgrind cannot execute AVX-512, so host-CPU ("native") variants are timed only
    [[ $x == *native* ]] && continue
    jobs_list+=("$b $(basename "$x")")
  done
done
run_one() {
  local b=$1 v=$2 f="$cg/$1.$2.out"
  [[ -s $f ]] && return
  local cmd; cmd=$(timed_cmd "$b" "$DATA/$b/bin/$v")
  # run valgrind on the binary itself, keeping the cd / redirections of the workload
  cmd=${cmd//"'$DATA/$b/bin/$v'"/valgrind --tool=callgrind --callgrind-out-file="'$f.tmp'" "'$DATA/$b/bin/$v'"}
  bash -c "$cmd" > /dev/null 2> "$cg/$b.$v.log" && mv "$f.tmp" "$f"
}
export -f run_one timed_cmd; export DATA SPEC cg
printf '%s\n' "${jobs_list[@]}" | xargs -P "$JOBS" -L1 bash -c 'run_one $0 $1'
printf 'benchmark\tvariant\tIr\n' > "$EXP_ROOT/results/instr-counts.tsv"
for f in "$cg"/*.out; do
  n=$(basename "$f" .out); b=${n%.*}; v=${n##*.}
  ir=$(callgrind_annotate "$f" 2>/dev/null | awk '/PROGRAM TOTALS/{gsub(",","",$1); print $1; exit}')
  printf '%s\t%s\t%s\n' "$b" "$v" "$ir" >> "$EXP_ROOT/results/instr-counts.tsv"
  callgrind_annotate --threshold=90 "$f" 2>/dev/null | sed -n '/file:function/,$p' | head -25 > "$cg/$n.hot.txt" || true
done
{ head -1 "$EXP_ROOT/results/instr-counts.tsv"; tail -n +2 "$EXP_ROOT/results/instr-counts.tsv" | sort; } > "$cg/.tmp" && mv "$cg/.tmp" "$EXP_ROOT/results/instr-counts.tsv"
cat "$EXP_ROOT/results/instr-counts.tsv"
