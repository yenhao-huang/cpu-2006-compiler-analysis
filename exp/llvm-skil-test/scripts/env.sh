# Source from anywhere: sets STUDY_ROOT / EXP_ROOT and the two local LLVM toolchains.
EXP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STUDY_ROOT="$(cd "$EXP_ROOT/../.." && pwd)"
export EXP_ROOT STUDY_ROOT
export PATH="$STUDY_ROOT/external/toolchain19/usr/bin:$STUDY_ROOT/external/toolchain/usr/bin:$PATH"
export LD_LIBRARY_PATH="$STUDY_ROOT/external/toolchain19/usr/lib/x86_64-linux-gnu:$STUDY_ROOT/external/toolchain/usr/lib/x86_64-linux-gnu"
