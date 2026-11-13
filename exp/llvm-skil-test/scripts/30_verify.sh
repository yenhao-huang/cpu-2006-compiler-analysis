#!/usr/bin/env bash
# Step 3: correctness. Each variant's checked output must be byte-identical to the
# independent GCC -O2 oracle (bzip2 additionally round-trips the compressed stream).
# Writes results/correctness.tsv and results/code-size.tsv.
source "$(dirname "$0")/env.sh"; source "$(dirname "$0")/workloads.sh"
out="$EXP_ROOT/results"; mkdir -p "$out"
printf 'benchmark\tvariant\toutput_sha256\tmatches_oracle\n' > "$out/correctness.tsv"
printf 'benchmark\tvariant\ttext_bytes\telf_sha256\n' > "$out/code-size.tsv"
fail=0
for b in "${@:-${BENCHES[@]}}"; do
  d="$DATA/$b"
  ref=$(bash -c "$(timed_cmd "$b" "$d/oracle")" 2>/dev/null | sha256sum | cut -c1-64)
  printf '%s\toracle\t%s\tref\n' "$b" "$ref" >> "$out/correctness.tsv"
  for x in "$d"/bin/*; do
    v=$(basename "$x")
    h=$(bash -c "$(timed_cmd "$b" "$x")" 2>/dev/null | sha256sum | cut -c1-64)
    ok=no; [[ $h == "$ref" ]] && ok=yes
    if [[ $b == 401.bzip2 && $ok == yes ]]; then   # decompress round-trip too
      cmp -s <("$x" -3 -c < "$d/work/input.ref" | "$x" -d -c) "$d/work/input.ref" || ok=no
    fi
    [[ $ok == yes ]] || { fail=1; echo "MISMATCH $b $v" >&2; }
    printf '%s\t%s\t%s\t%s\n' "$b" "$v" "$h" "$ok" >> "$out/correctness.tsv"
    text=$(size -A "$x" | awk '$1==".text"{print $2}')
    printf '%s\t%s\t%s\t%s\n' "$b" "$v" "$text" "$(sha256sum "$x" | cut -c1-64)" >> "$out/code-size.tsv"
  done
done
cut -f1,2,4 "$out/correctness.tsv"
exit $fail
