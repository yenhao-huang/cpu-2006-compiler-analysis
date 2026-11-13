#!/usr/bin/env bash
# Differential correctness: run one variant on the same workload used for timing
# and print a signature. A variant passes when its signature equals full's
# (full was validated against native builds / known solutions by the original study).
# Usage: scripts/check.sh <bench> <variant>
set -uo pipefail
source "$(dirname "$0")/env.sh"
bench=$1 variant=$2
exe="$EXP_ROOT/build/$bench/$variant"
tmp="$EXP_ROOT/build/$bench/check"; mkdir -p "$tmp"
o="$tmp/$variant"
S="$STUDY_ROOT"; X="$S/data/expansion/$bench/work"
h() { sha256sum | cut -c1-16; }
case "$bench" in
  400.perlbench) cd "$S/data/expansion/400.perlbench/source"
    "$exe" t/op/regexp.t > "$o.out" 2>&1
    ok=$(grep -c '^ok' "$o.out"); bad=$(grep -c '^not ok' "$o.out")
    echo "ok=$ok notok=$bad $(h < "$o.out")";;
  401.bzip2) cd "$X"
    "$exe" -3 < input.ref > "$o.bz2"
    "$exe" -d < "$o.bz2" | cmp -s - input.ref && rt=roundtrip-ok || rt=roundtrip-FAIL
    echo "$rt $(h < "$o.bz2")"; rm -f "$o.bz2";;
  403.gcc) cd "$S"
    "$exe" spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o "$o.s" 2>/dev/null
    echo "$(h < "$o.s")";;
  435.gromacs) cd "$X"
    "$exe" -s water.tpr -deffnm "chk_$variant" > /dev/null 2>&1
    echo "$(h < "chk_$variant.gro")"; rm -f chk_"$variant".* "#chk_$variant"*;;
  436.cactusADM) cd "$X"
    find test_Bench -maxdepth 1 -type f -delete
    "$exe" test_Bench.par > /dev/null 2>&1
    echo "files=$(ls test_Bench | wc -l) $( (cd test_Bench && sha256sum * ) | h)";;
  445.gobmk) cd "$S/spec-cpu2006-redist/modified/445.gobmk/data/all/input"
    "$exe" --quiet --mode gtp < "$S/spec-cpu2006-redist/modified/445.gobmk/data/train/input/arb.tst" | h;;
  454.calculix) cd "$S/data/expansion/454.calculix"
    "$exe" 0 stdout 20 20 20 0 64 10101 1 0 0 0 100 0 0 1 > "$o.out" 2>&1; st=$?
    err=$(grep -o 'maxabs error[^0-9]*[0-9.eE+-]*' "$o.out" | head -1 | grep -o '[0-9.]*[eE][+-][0-9]*\|[0-9]\.[0-9]*$')
    awk -v e="$err" -v s="$st" 'BEGIN{ if (s==1 && e!="" && e+0<=1e-8) print "residual-ok"; else print "residual-FAIL status=" s " err=" e }';;
  456.hmmer) cd "$X"; rm -f ig.hmm.new
    "$exe" --fixed 500 --num 10000 --seed 1 ig.hmm | h;;
  462.libquantum) cd "$S"; "$exe" 143 25 | h;;
  465.tonto) cd "$X"; rm -f stdout 'h2o.density_matrix,restricted'
    "$exe" < stdin > /dev/null 2>&1; cp stdout "$o.stdout"
    echo "$(grep -m1 -o 'SCF energy[^-]*-[0-9.]*' stdout | tr -s ' ') $(h < stdout)";;
  481.wrf) cd "$X"; rm -f wrfout_d01_0001-01-01_00:00:00
    ( ulimit -s unlimited; "$exe" > "$o.stdout" 2>&1 )
    echo "steps=$(grep -c 'em_t_2' "$o.stdout") $(h < wrfout_d01_0001-01-01_00:00:00)";;
  482.sphinx3) cd "$S/data/expansion/482.sphinx3/source"
    "$exe" ../an4x20.ctl model/lm/an4 model/lm/an4/args.an4.test > "$o.stdout" 2> "$o.stderr"
    cat "$o.stdout" "$o.stderr" | grep -E 'FWDXCT|PARTIAL HYP' | sed -E 's/\(.*s\)//' > "$o.hyp"
    echo "lines=$(wc -l < "$o.hyp") $(h < "$o.hyp")";;
  483.xalanc) cd "$X"
    "$exe" -o "$o.xml" birds5000.xml birds.xsl
    cmp -s "$o.xml" oracle5000.xml && echo oracle-match || echo "oracle-MISMATCH"; rm -f "$o.xml";;
esac
