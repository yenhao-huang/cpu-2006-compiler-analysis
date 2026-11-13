#!/usr/bin/env bash
# Step 4: paired wall-clock timing with hyperfine, following the parent study's design:
# every round runs `o3` (the practical reference) adjacent to each variant, in a
# random order, pinned to one core; the per-round ratio T_variant / T_o3 is the
# unit of analysis (no shared denominator across rounds).
# Usage: ROUNDS=5 40_time.sh [bench...]
source "$(dirname "$0")/env.sh"; source "$(dirname "$0")/workloads.sh"
ROUNDS=${ROUNDS:-5}; REF=${REF:-o3}
for b in "${@:-${BENCHES[@]}}"; do
  d="$DATA/$b"; td="$EXP_ROOT/results/timing/$b"; mkdir -p "$td"
  # byte-identical copy of the reference = noise control (parent study's full_control)
  cp -f "$d/bin/$REF" "$d/bin/${REF}_control"
  mapfile -t vs < <(ls "$d/bin" | grep -vx "$REF")
  # warm-up (page cache, input files)
  bash -c "$(timed_cmd "$b" "$d/bin/$REF")" > /dev/null 2>&1
  for r in $(seq 1 "$ROUNDS"); do
    for v in $(printf '%s\n' "${vs[@]}" | shuf); do
      if (( RANDOM % 2 )); then pair="$REF,$v"; else pair="$v,$REF"; fi
      echo "$r $pair" >> "$td/order.txt"
      hyperfine -N --runs 1 --style none \
        --export-json "$td/$r-$v.json" \
        --parameter-list variant "$pair" \
        "taskset -c $CPU bash -c \"$(timed_cmd "$b" "$d/bin/{variant}" | sed 's/"/\\"/g') > /dev/null\"" \
        > /dev/null 2>&1 || echo "hyperfine failed: $b $v round $r" >&2
    done
  done
  echo "timed $b"
done
