# Workload definitions. Source after env.sh.
# timed_cmd <bench> <binary>  -> shell command (string) for the timed run; stdout is the
#                                 checked output (same inputs as the parent study, configs/all-workloads.tsv)
# train_cmd <bench> <binary>  -> PGO training run; deliberately a DIFFERENT input
timed_cmd() {
  local b=$1 x=$2 d="$DATA/$1"
  case $b in
  401.bzip2)      echo "cd '$d/work' && '$x' -3 -c < input.ref" ;;
  403.gcc)        echo "cd '$d/work' && '$x' '$SPEC/modified/403.gcc/data/train/input/integrate.in' -o /dev/stdout" ;;
  445.gobmk)      echo "cd '$SPEC/modified/445.gobmk/data/all/input' && '$x' --quiet --mode gtp < '$SPEC/modified/445.gobmk/data/train/input/arb.tst'" ;;
  456.hmmer)      echo "cd '$d/work' && cp ig.orig ig.hmm && '$x' --fixed 500 --num 10000 --seed 1 ig.hmm" ;;
  462.libquantum) echo "'$x' 143 25" ;;
  esac
}
train_cmd() {
  local b=$1 x=$2 d="$DATA/$1"
  case $b in
  401.bzip2)      echo "cat '$SPEC/original/401.bzip2/bzip2-1.0.3/manual.pdf' '$SPEC/original/401.bzip2/bzip2-1.0.3/bzip2.txt' | '$x' -3 -c | '$x' -d -c > /dev/null" ;;
  403.gcc)        echo "cd '$d/work' && '$x' '$SPEC/modified/403.gcc/data/test/input/cccp.in' -o /dev/null" ;;
  445.gobmk)      echo "cd '$SPEC/modified/445.gobmk/data/all/input' && '$x' --quiet --mode gtp < '$SPEC/modified/445.gobmk/data/train/input/arend.tst' > /dev/null" ;;
  456.hmmer)      echo "cd '$d/work' && cp ig.orig ig.hmm && '$x' --fixed 300 --num 3000 --seed 7 ig.hmm > /dev/null" ;;
  462.libquantum) echo "'$x' 33 5 > /dev/null" ;;
  esac
}
