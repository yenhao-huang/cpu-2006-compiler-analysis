# Shared settings for exp/llvm-skil-test. Source from any script.
set -euo pipefail
EXP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STUDY_ROOT="$(cd "$EXP_ROOT/../.." && pwd)"
SPEC="$STUDY_ROOT/spec-cpu2006-redist"
DATA="$STUDY_ROOT/data/llvm-skil-test"   # build products stay local (data/ is git-ignored)
LLVM_VER="${LLVM_VER:-18}"
CLANG="clang-$LLVM_VER"; OPT="opt-$LLVM_VER"; LLC="llc-$LLVM_VER"
LINK="llvm-link-$LLVM_VER"; PROFDATA="llvm-profdata-$LLVM_VER"
command -v "$CLANG" >/dev/null || CLANG=clang
command -v "$OPT" >/dev/null || OPT=opt
command -v "$LLC" >/dev/null || LLC=llc
command -v "$LINK" >/dev/null || LINK=llvm-link
command -v "$PROFDATA" >/dev/null || PROFDATA=llvm-profdata
# Same frontend flags as the parent study (docs/Workflow.md §3).
FE_FLAGS=(-O3 -Xclang -disable-llvm-passes -fno-strict-aliasing -fcommon
          -ffp-contract=off -march=x86-64-v3
          -DSPEC_CPU -DSPEC_CPU_LINUX -DSPEC_CPU_LP64)
BENCHES=(401.bzip2 403.gcc 445.gobmk 456.hmmer 462.libquantum)
CPU="${CPU:-1}"   # pinned core for timing
