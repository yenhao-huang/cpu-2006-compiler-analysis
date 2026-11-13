# CPU2006 transform pass 消融：外部工具重現

所有區塊依序在 **Bash** 執行。只使用 Git、Debian 套件、Clang/LLVM、GCC、GNU coreutils、hyperfine、jq；沒有自製 compiler wrapper、LLVM plugin、Python runner 或分析程式。Shell 的迴圈只列舉檔案、參數及呼叫外部工具。`configs/pipelines.tsv` 是直接傳給 `opt -passes` 的純文字設定，其完整內容見下方。

這是指定 repository 可取得的 CPU2006 子集研究，不是完整 SPEC CPU2006 reportable run。使用官方 train 工作負載：403.gcc 的 `integrate.in`、445.gobmk 的 `arb.tst`、462.libquantum 的 `143 25`。repository 不含這三項完整的官方 output oracle；以獨立 GCC 建置與每一個 LLVM variant 比對輸出。此檢查不能取代 SPEC harness 驗證。

## 1. 取得固定來源與外部工具

環境：Debian 12 x86-64；既有 `gcc`、`binutils`、`git`、`jq`、`taskset`、`make`。CPU 需支援 x86-64-v3。下載套件僅解壓至研究目錄，不需要 root 或改動系統安裝。

```bash
mkdir -p /workspace/compiler_optimization/transform_pass_research
cd /workspace/compiler_optimization/transform_pass_research
export STUDY_ROOT="$PWD"
git clone git@github.com:miyuki/spec-cpu2006-redist.git
git -C spec-cpu2006-redist checkout --detach 39effd74541743ddc74d7b27cbbb315790c56d12
mkdir -p external/debs external/toolchain data logs results configs docs
(
  cd external/debs
  apt-get download clang-14 libclang-cpp14 libllvm14 libclang-common-14-dev \
    llvm-14-linker-tools libclang1-14 llvm-14 llvm-14-runtime \
    libpfm4 libz3-4 libcurl3-nss hyperfine time datamash sysstat
  for pkg in *.deb; do dpkg-deb -x "$pkg" ../toolchain; done
)
export PATH="$STUDY_ROOT/external/toolchain/usr/bin:$PATH"
export LD_LIBRARY_PATH="$STUDY_ROOT/external/toolchain/usr/lib/x86_64-linux-gnu"
clang-14 --version
opt-14 --version
hyperfine --version
gcc --version
sha256sum external/debs/*.deb > logs/toolchain-packages.sha256
```

本次 LLVM 14.0.6（Debian `1:14.0.6-12`）、hyperfine 1.15.0、GNU time 1.9。apt 候選套件日後可能變動；原始 `.deb` 與 SHA-256 保留在 `external/debs`、`logs/toolchain-packages.sha256`。嚴格相同環境請使用本次保留的套件，並執行 `sha256sum -c logs/toolchain-packages.sha256`。

## 2. 產生共同的未最佳化 bitcode

`-O3 -Xclang -disable-llvm-passes` 只設定前端行為，停用 LLVM middle-end 最佳化。不使用 `-O0` 的 optnone/noinline，也避免 `-O1` 產生 `llvm.loop.unroll.disable`。每個 variant 從同一個 `raw.bc` 開始。跨 translation-unit 的 `llvm-link` 允許 whole-program inlining；並非標準 SPEC base 的逐檔編譯設定。

```bash
cd "$STUDY_ROOT"
mkdir -p data/{403.gcc,445.gobmk,462.libquantum}/raw
(
  cd data/462.libquantum/raw
  clang-14 -std=gnu89 -O3 -Xclang -disable-llvm-passes \
    -fno-strict-aliasing -fcommon -ffp-contract=off -march=x86-64-v3 \
    -DSPEC_CPU -DSPEC_CPU_LINUX -DSPEC_CPU_LP64 -emit-llvm -c \
    ../../../spec-cpu2006-redist/modified/462.libquantum/src/*.c \
    > ../../../logs/libquantum-frontend.log 2>&1
  llvm-link-14 ./*.bc -o ../raw.bc
)
(
  cd data/403.gcc/raw
  clang-14 -std=gnu89 -O3 -Xclang -disable-llvm-passes \
    -fno-strict-aliasing -fcommon -ffp-contract=off -march=x86-64-v3 \
    -DSPEC_CPU -DSPEC_CPU_LINUX -DSPEC_CPU_LP64 -DPOSIX -DSPEC_CPU_HAVE_BOOL \
    -I../../../spec-cpu2006-redist/modified/403.gcc/src -emit-llvm -c \
    ../../../spec-cpu2006-redist/modified/403.gcc/src/*.c \
    > ../../../logs/gcc-frontend.log 2>&1
  llvm-link-14 ./*.bc -o ../raw.bc
)
(
  gobmk_src="$STUDY_ROOT/spec-cpu2006-redist/modified/445.gobmk/src"
  for srcdir in engine interface patterns sgf utils; do
    mkdir -p "$STUDY_ROOT/data/445.gobmk/raw/$srcdir"
    cd "$STUDY_ROOT/data/445.gobmk/raw/$srcdir"
    clang-14 -std=gnu89 -O3 -Xclang -disable-llvm-passes \
      -fno-strict-aliasing -fcommon -ffp-contract=off -march=x86-64-v3 \
      -DSPEC_CPU -DSPEC_CPU_LINUX -DSPEC_CPU_LP64 -DHAVE_CONFIG_H -DWANT_STDC_PROTO \
      -I"$gobmk_src/include" -I"$gobmk_src/engine" -I"$gobmk_src/interface" \
      -I"$gobmk_src/patterns" -I"$gobmk_src/sgf" -I"$gobmk_src/utils" \
      -emit-llvm -c "$gobmk_src/$srcdir/"*.c \
      > "$STUDY_ROOT/logs/gobmk-$srcdir-frontend.log" 2>&1
  done
  cd "$STUDY_ROOT"
  llvm-link-14 data/445.gobmk/raw/{engine,interface,patterns,sgf,utils}/*.bc \
    -o data/445.gobmk/raw.bc
)
for bench in 403.gcc 445.gobmk 462.libquantum; do
  llvm-dis-14 "data/$bench/raw.bc" -o "data/$bench/raw.ll"
  sha256sum "data/$bench/raw.bc"
  # 沒有匹配才是預期結果；grep exit 1 代表沒有出現禁止最佳化的標記。
  grep -E '^attributes.* (optnone|noinline)( |})|^![0-9]+ = .*llvm.loop.unroll.disable' "data/$bench/raw.ll" || true
done
sha256sum data/*/raw.bc > results/raw-bitcode.sha256
sha256sum spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in \
  spec-cpu2006-redist/modified/445.gobmk/data/train/input/arb.tst > results/inputs.sha256
```

## 3. 明列所有 pipeline 並建置

消融刪除完整 pipeline 中該 pass 的所有顯式出現，其餘順序不變。`no_vectors` 同時刪除 Loop 與 SLP vectorizer。`baseline` 僅驗證 IR；`o3` 是標準 middle-end `default<O3>` 對照，兩者都保留與 full 相同的 `llc -O=2` backend。

```bash
cat > configs/pipelines.tsv <<'PIPELINES'
baseline	verify
full	function(mem2reg),cgscc(inline),function(mem2reg,instcombine,simplifycfg,loop-simplify,lcssa,loop(loop-rotate),loop-mssa(licm),loop(indvars),loop-vectorize,slp-vectorizer,loop-unroll<O3>,instcombine,dce,simplifycfg,dce)
no_inline	function(mem2reg),function(mem2reg,instcombine,simplifycfg,loop-simplify,lcssa,loop(loop-rotate),loop-mssa(licm),loop(indvars),loop-vectorize,slp-vectorizer,loop-unroll<O3>,instcombine,dce,simplifycfg,dce)
no_unroll	function(mem2reg),cgscc(inline),function(mem2reg,instcombine,simplifycfg,loop-simplify,lcssa,loop(loop-rotate),loop-mssa(licm),loop(indvars),loop-vectorize,slp-vectorizer,instcombine,dce,simplifycfg,dce)
no_loop_vectorize	function(mem2reg),cgscc(inline),function(mem2reg,instcombine,simplifycfg,loop-simplify,lcssa,loop(loop-rotate),loop-mssa(licm),loop(indvars),slp-vectorizer,loop-unroll<O3>,instcombine,dce,simplifycfg,dce)
no_slp	function(mem2reg),cgscc(inline),function(mem2reg,instcombine,simplifycfg,loop-simplify,lcssa,loop(loop-rotate),loop-mssa(licm),loop(indvars),loop-vectorize,loop-unroll<O3>,instcombine,dce,simplifycfg,dce)
no_mem2reg	cgscc(inline),function(instcombine,simplifycfg,loop-simplify,lcssa,loop(loop-rotate),loop-mssa(licm),loop(indvars),loop-vectorize,slp-vectorizer,loop-unroll<O3>,instcombine,dce,simplifycfg,dce)
no_licm	function(mem2reg),cgscc(inline),function(mem2reg,instcombine,simplifycfg,loop-simplify,lcssa,loop(loop-rotate),loop(indvars),loop-vectorize,slp-vectorizer,loop-unroll<O3>,instcombine,dce,simplifycfg,dce)
no_dce	function(mem2reg),cgscc(inline),function(mem2reg,instcombine,simplifycfg,loop-simplify,lcssa,loop(loop-rotate),loop-mssa(licm),loop(indvars),loop-vectorize,slp-vectorizer,loop-unroll<O3>,instcombine,simplifycfg)
no_simplifycfg	function(mem2reg),cgscc(inline),function(mem2reg,instcombine,loop-simplify,lcssa,loop(loop-rotate),loop-mssa(licm),loop(indvars),loop-vectorize,slp-vectorizer,loop-unroll<O3>,instcombine,dce,dce)
no_vectors	function(mem2reg),cgscc(inline),function(mem2reg,instcombine,simplifycfg,loop-simplify,lcssa,loop(loop-rotate),loop-mssa(licm),loop(indvars),loop-unroll<O3>,instcombine,dce,simplifycfg,dce)
o3	default<O3>
PIPELINES
set -eu
for bench in 462.libquantum 403.gcc 445.gobmk; do
  mkdir -p "logs/$bench" "results/$bench"
  while IFS="$(printf '\t')" read -r variant pipeline; do
    opt-14 -passes="$pipeline" -debug-pass-manager \
      -pass-remarks-output="logs/$bench/$variant.remarks.yaml" \
      -pass-remarks='.*' -pass-remarks-missed='.*' -pass-remarks-analysis='.*' \
      "data/$bench/raw.bc" -o "data/$bench/$variant.opt.bc" \
      2> "logs/$bench/$variant.passes.log"
    llc-14 -O=2 -filetype=obj -relocation-model=pic \
      "data/$bench/$variant.opt.bc" -o "data/$bench/$variant.o" \
      2> "logs/$bench/$variant.llc.log"
    clang-14 "data/$bench/$variant.o" -lm -o "data/$bench/$variant" \
      2> "logs/$bench/$variant.link.log"
    size "data/$bench/$variant" > "results/$bench/$variant.size.txt"
    sha256sum "data/$bench/$variant" > "results/$bench/$variant.sha256"
  done < configs/pipelines.tsv
done
```

## 4. 獨立 GCC 正確性對照

```bash
mkdir -p data/oracle
for bench in 462.libquantum 403.gcc; do
  gcc -std=gnu89 -O2 -fno-strict-aliasing -fcommon -ffp-contract=off -march=x86-64-v3 \
    -DSPEC_CPU -DSPEC_CPU_LINUX -DSPEC_CPU_LP64 -DPOSIX -DSPEC_CPU_HAVE_BOOL \
    -I"spec-cpu2006-redist/modified/$bench/src" \
    "spec-cpu2006-redist/modified/$bench/src/"*.c -lm -o "data/oracle/$bench" \
    > "logs/$bench/gcc-oracle-build.log" 2>&1
done
gcc -std=gnu89 -O2 -fno-strict-aliasing -fcommon -ffp-contract=off -march=x86-64-v3 \
  -DSPEC_CPU -DSPEC_CPU_LINUX -DSPEC_CPU_LP64 -DHAVE_CONFIG_H -DWANT_STDC_PROTO \
  -Ispec-cpu2006-redist/modified/445.gobmk/src/include \
  -Ispec-cpu2006-redist/modified/445.gobmk/src/engine \
  -Ispec-cpu2006-redist/modified/445.gobmk/src/interface \
  -Ispec-cpu2006-redist/modified/445.gobmk/src/patterns \
  -Ispec-cpu2006-redist/modified/445.gobmk/src/sgf \
  -Ispec-cpu2006-redist/modified/445.gobmk/src/utils \
  spec-cpu2006-redist/modified/445.gobmk/src/{engine,interface,patterns,sgf,utils}/*.c \
  -lm -o data/oracle/445.gobmk > logs/445.gobmk/gcc-oracle-build.log 2>&1
```

下面的 `cmp` 必須全部成功；在量測前執行，不能只檢查 exit code。

```bash
cd "$STUDY_ROOT"
taskset -c 2 data/oracle/403.gcc \
  spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in \
  -o results/403.gcc/oracle.s > results/403.gcc/oracle.stdout 2> logs/403.gcc/oracle.stderr
taskset -c 2 data/oracle/462.libquantum 143 25 > results/462.libquantum/oracle.out
(
  cd spec-cpu2006-redist/modified/445.gobmk/data/all/input
  taskset -c 2 "$STUDY_ROOT/data/oracle/445.gobmk" --quiet --mode gtp \
    < "$STUDY_ROOT/spec-cpu2006-redist/modified/445.gobmk/data/train/input/arb.tst" \
    > "$STUDY_ROOT/results/445.gobmk/oracle.out" 2> "$STUDY_ROOT/logs/445.gobmk/oracle.stderr"
)
: > results/correctness.txt
while IFS="$(printf '\t')" read -r variant pipeline; do
  taskset -c 2 "data/403.gcc/$variant" \
    spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in \
    -o "results/403.gcc/$variant.s" \
    > "results/403.gcc/$variant.stdout" 2> "logs/403.gcc/$variant.stderr"
  cmp results/403.gcc/oracle.s "results/403.gcc/$variant.s"
  cmp results/403.gcc/oracle.stdout "results/403.gcc/$variant.stdout"
  taskset -c 2 "data/462.libquantum/$variant" 143 25 \
    > "results/462.libquantum/$variant.out" 2> "logs/462.libquantum/$variant.stderr"
  cmp results/462.libquantum/oracle.out "results/462.libquantum/$variant.out"
  (
    cd spec-cpu2006-redist/modified/445.gobmk/data/all/input
    taskset -c 2 "$STUDY_ROOT/data/445.gobmk/$variant" --quiet --mode gtp \
      < "$STUDY_ROOT/spec-cpu2006-redist/modified/445.gobmk/data/train/input/arb.tst" \
      > "$STUDY_ROOT/results/445.gobmk/$variant.out" \
      2> "$STUDY_ROOT/logs/445.gobmk/$variant.stderr"
  )
  cmp results/445.gobmk/oracle.out "results/445.gobmk/$variant.out"
  printf '%s: 403.gcc,445.gobmk,462.libquantum PASS\n' "$variant" >> results/correctness.txt
done < configs/pipelines.tsv
cat results/correctness.txt
```

## 5. Pass audit、code size 與硬體紀錄

下列 assert 檢查移除的 pass 確實不在執行紀錄中。這只約束 LLVM IR named pass：其他 passes 內部的簡化、LICM 自身的記憶體提升與 backend machine passes 仍可能產生相似效果。

```bash
cd "$STUDY_ROOT"
printf 'no_inline InlinerPass\nno_unroll LoopUnrollPass\nno_loop_vectorize LoopVectorizePass\nno_slp SLPVectorizerPass\nno_mem2reg PromotePass\nno_licm LICMPass\nno_dce DCEPass\nno_simplifycfg SimplifyCFGPass\n' > configs/audit.txt
: > results/pass-audit.txt
printf 'benchmark\tvariant\ttext_bytes\n' > results/code-size.tsv
for bench in 403.gcc 445.gobmk 462.libquantum; do
  while read -r variant pass; do
    grep -q "Running pass: $pass on" "logs/$bench/full.passes.log"
    if grep -q "Running pass: $pass on" "logs/$bench/$variant.passes.log"; then
      printf 'FAIL: %s %s\n' "$bench" "$variant"
      exit 1
    fi
    printf '%s %s PASS\n' "$bench" "$variant" >> results/pass-audit.txt
  done < configs/audit.txt
  if grep -Eq 'Running pass: (LoopVectorizePass|SLPVectorizerPass) on' "logs/$bench/no_vectors.passes.log"; then exit 1; fi
  while IFS="$(printf '\t')" read -r variant pipeline; do
    objcopy --dump-section ".text=data/$bench/$variant.text.bin" "data/$bench/$variant"
    size -A "data/$bench/$variant" > "results/$bench/$variant.sections.txt"
    sha256sum "data/$bench/$variant.text.bin" > "results/$bench/$variant.text.sha256"
    sha256sum -c "results/$bench/$variant.sha256" > /dev/null
    printf '%s\t%s\t' "$bench" "$variant" >> results/code-size.tsv
    stat -c '%s' "data/$bench/$variant.text.bin" >> results/code-size.tsv
  done < configs/pipelines.tsv
done
{
  TZ=Asia/Taipei date -Iseconds
  date -u -Iseconds
  uname -a
  lscpu
  gcc --version
  clang-14 --version
  opt-14 --version
  hyperfine --version
  cat /proc/self/status | grep Cpus_allowed_list
  cat /sys/devices/system/cpu/cpu2/topology/thread_siblings_list
  cat /sys/devices/system/cpu/cpu2/cpufreq/scaling_governor
  cat /sys/devices/system/cpu/intel_pstate/no_turbo
  uptime
  git -C spec-cpu2006-redist rev-parse HEAD
  git -C spec-cpu2006-redist status --short
} > logs/environment.txt
mpstat -P ALL 2 3 > logs/cpu-load-diagnostic.txt
cat /sys/fs/cgroup/cpu.max /sys/fs/cgroup/cpu.stat > logs/cgroup-cpu.txt
```

## 6. 三個亂序區塊的正式計時

建置、輸出驗證和其他本研究工作結束後才開始計時。每個區塊每個 variant 先暖機一次，再量三次；三個區塊共九次有效樣本及三次暖機。用 `shuf` 隨機排列 variant，並保留順序供審核。執行為單工；不可平行跑 benchmark。固定 CPU 2；若換硬體，選擇可用的同一類核心並記錄編號。未關閉系統 Turbo、未保留 SMT sibling，也未停止其他使用者程序，因此微小差異可能受環境影響。

```bash
cd "$STUDY_ROOT"
for round in 1 2 3; do
  for bench in 403.gcc 445.gobmk 462.libquantum; do
    cut -f1 configs/pipelines.tsv | shuf > "results/$bench/order-$round.txt"
    date -Iseconds > "logs/$bench/round-$round.start"
    uptime >> "logs/$bench/round-$round.start"
    case "$bench" in
      403.gcc)
        hyperfine --warmup 1 --runs 3 \
          --parameter-list variant "$(paste -sd, "results/$bench/order-$round.txt")" \
          --export-json "results/$bench/round-$round.json" \
          --export-markdown "results/$bench/round-$round.md" \
          'taskset -c 2 data/403.gcc/{variant} spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null' \
          > "logs/$bench/round-$round.log" 2>&1
        ;;
      445.gobmk)
        (
          cd spec-cpu2006-redist/modified/445.gobmk/data/all/input
          hyperfine --warmup 1 --runs 3 \
            --parameter-list variant "$(paste -sd, "$STUDY_ROOT/results/$bench/order-$round.txt")" \
            --export-json "$STUDY_ROOT/results/$bench/round-$round.json" \
            --export-markdown "$STUDY_ROOT/results/$bench/round-$round.md" \
            "taskset -c 2 $STUDY_ROOT/data/445.gobmk/{variant} --quiet --mode gtp < $STUDY_ROOT/spec-cpu2006-redist/modified/445.gobmk/data/train/input/arb.tst" \
            > "$STUDY_ROOT/logs/$bench/round-$round.log" 2>&1
        )
        ;;
      462.libquantum)
        hyperfine --warmup 1 --runs 3 \
          --parameter-list variant "$(paste -sd, "results/$bench/order-$round.txt")" \
          --export-json "results/$bench/round-$round.json" \
          --export-markdown "results/$bench/round-$round.md" \
          'taskset -c 2 data/462.libquantum/{variant} 143 25' \
          > "logs/$bench/round-$round.log" 2>&1
        ;;
    esac
  done
done
```

執行本研究時，每個 block 的確切 variant 順序保存在 `results/*/order-*.txt`。若要重播完全相同順序，保留這些檔案並略過 `shuf` 那一行。hyperfine 的 stdout/stderr 導向及計時方法對同一 workload 的所有 variant 一致；`403.gcc` 把產生的組合語言寫入 `/dev/null`，正式計時不包含磁碟檔案寫入。

## 7. 相鄰配對補充量測

整輪亂序仍可能受到時段漂移干擾。本次第一輪 libquantum 的 full 與 byte-identical no_dce 分別約 0.83 / 0.52 秒，因此另以 **五組相鄰 full/variant 配對**作主要邊際效能依據，保留原有三輪作診斷。每一組配對隨機交換 full 與消融版本的執行先後，並隨機排列各 variant；每個命令量一次。這是在前述完整暖機／量測之後追加，所以不再為每個配對加暖機。一次 hyperfine 呼叫只含這兩個相鄰執行，不能把不同 paired JSON 的 full 混在一起當分母。

```bash
cd "$STUDY_ROOT"
for round in 1 2 3 4 5; do
  for bench in 403.gcc 445.gobmk 462.libquantum; do
    mkdir -p "results/paired/$bench" "logs/paired/$bench"
    cut -f1 configs/pipelines.tsv | grep -vx full | shuf \
      > "results/paired/$bench/order-$round.txt"
    while read -r variant; do
      pair_order=$(printf '%s\n' full "$variant" | shuf | paste -sd,)
      printf '%s\n' "$pair_order" > "results/paired/$bench/$round-$variant.order.txt"
      case "$bench" in
        403.gcc)
          hyperfine --warmup 0 --runs 1 --parameter-list variant "$pair_order" \
            --export-json "results/paired/$bench/$round-$variant.json" \
            'taskset -c 2 data/403.gcc/{variant} spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null' \
            > "logs/paired/$bench/$round-$variant.log" 2>&1
          ;;
        445.gobmk)
          (
            cd spec-cpu2006-redist/modified/445.gobmk/data/all/input
            hyperfine --warmup 0 --runs 1 --parameter-list variant "$pair_order" \
              --export-json "$STUDY_ROOT/results/paired/$bench/$round-$variant.json" \
              "taskset -c 2 $STUDY_ROOT/data/445.gobmk/{variant} --quiet --mode gtp < $STUDY_ROOT/spec-cpu2006-redist/modified/445.gobmk/data/train/input/arb.tst" \
              > "$STUDY_ROOT/logs/paired/$bench/$round-$variant.log" 2>&1
          )
          ;;
        462.libquantum)
          hyperfine --warmup 0 --runs 1 --parameter-list variant "$pair_order" \
            --export-json "results/paired/$bench/$round-$variant.json" \
            'taskset -c 2 data/462.libquantum/{variant} 143 25' \
            > "logs/paired/$bench/$round-$variant.log" 2>&1
          ;;
      esac
    done < "results/paired/$bench/order-$round.txt"
  done
done
```

若要重播本次配對順序，保留 `results/paired/*/order-*.txt` 與 `*.order.txt`，略過兩個產生順序的命令，並改用 `pair_order=$(cat "results/paired/$bench/$round-$variant.order.txt")`。換一個隨機順序可以重做同樣設計，但不是本次的逐項重播。

gcc 的 DCE 消融仍有 48 bytes 的 `.text` 差異，不能充當嚴格零效果控制。因此最後另外複製 full 執行檔，做五對 byte-identical 控制；這十個時間樣本獨立保存，不混入上述 pass 統計。

```bash
mkdir -p results/null-control/403.gcc logs/null-control/403.gcc
cp data/403.gcc/full data/403.gcc/full_control
cmp data/403.gcc/full data/403.gcc/full_control
sha256sum data/403.gcc/full data/403.gcc/full_control > results/null-control/403.gcc/binaries.sha256
for round in 1 2 3 4 5; do
  pair_order=$(printf '%s\n' full full_control | shuf | paste -sd,)
  printf '%s\n' "$pair_order" > "results/null-control/403.gcc/$round.order.txt"
  hyperfine --warmup 0 --runs 1 --parameter-list variant "$pair_order" \
    --export-json "results/null-control/403.gcc/$round.json" \
    'taskset -c 2 data/403.gcc/{variant} spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null' \
    > "logs/null-control/403.gcc/$round.log" 2>&1
done
jq -r '(.results[]|select(.parameters.variant=="full")|.times[0]) as $full | .results[]|select(.parameters.variant=="full_control")|[input_filename,(.times[0]/$full),(100*(.times[0]/$full-1)),$full,.times[0]]|@tsv' \
  results/null-control/403.gcc/[1-5].json > results/null-control/403.gcc/ratios.tsv
datamash count 2 geomean 2 min 2 max 2 < results/null-control/403.gcc/ratios.tsv \
  > results/null-control/403.gcc/summary.tsv
```

## 8. 使用外部工具彙整，不依賴自製分析程式

`jq` 只展開 hyperfine JSON；GNU datamash 計算九個樣本的平均、樣本標準差、中位數與範圍。單位全部是秒。保留每輪平均，讓讀者檢查跨區塊漂移。不要以最佳一次取代全部樣本。

```bash
cd "$STUDY_ROOT"
printf 'benchmark\tvariant\tn\tmean_s\tsample_sd_s\tmedian_s\tmin_s\tmax_s\n' > results/summary.tsv
printf 'benchmark\tround\tvariant\tmean_s\tstddev_s\n' > results/blocks.tsv
for bench in 403.gcc 445.gobmk 462.libquantum; do
  jq -r --arg bench "$bench" \
    '.results[] | .parameters.variant as $variant | .times[] | [$bench, $variant, .] | @tsv' \
    "results/$bench/round-1.json" "results/$bench/round-2.json" "results/$bench/round-3.json" \
    > "results/$bench/samples.tsv"
  datamash -s -g 1,2 count 3 mean 3 sstdev 3 median 3 min 3 max 3 \
    < "results/$bench/samples.tsv" >> results/summary.tsv
  for round in 1 2 3; do
    jq -r --arg bench "$bench" --arg round "$round" \
      '.results[] | [$bench, $round, .parameters.variant, .mean, .stddev] | @tsv' \
      "results/$bench/round-$round.json" >> results/blocks.tsv
  done
done
cat results/summary.tsv
cat results/blocks.tsv
```

消融效益的計算定義：

- **加入該 pass 的速度提升 (%)**：`100 × (T_without / T_full − 1)`。正值表示 full 較快；負值表示該 pass 在這個 pipeline／輸入下造成退步。
- **加入該 pass 的時間下降 (%)**：`100 × (1 − T_full / T_without)`；這與上一個公式不同，不混用。
- **code size 變化 (%)**：`100 × (text_full / text_without − 1)`；以 ELF `.text` section 位元組計算，不以整個 ELF 檔案大小代替指令碼。
- 各區塊也各自計算 `T_without / T_full`，觀察方向是否一致。這是敏感度檢查，不是信賴區間或顯著性檢定。
- 比較向量化交互作用時，對照 `full`、`no_loop_vectorize`、`no_slp`、`no_vectors`；單項百分比不可直接相加。

以下只用 GNU awk 對現成摘要做欄位運算，輸出可檢查的 ratio 表：

```bash
awk -F '\t' 'BEGIN {OFS="\t"; print "benchmark","variant","speedup_full_percent"} NR==FNR {if ($2=="full") full[$1]=$4; next} FNR>1 {print $1,$2,100*($4/full[$1]-1)}' \
  results/summary.tsv results/summary.tsv > results/effects.tsv
awk -F '\t' 'BEGIN {OFS="\t"; print "benchmark","round","variant","speedup_full_percent"} NR==FNR {if ($3=="full") full[$1,$2]=$4; next} FNR>1 {print $1,$2,$3,100*($4/full[$1,$2]-1)}' \
  results/blocks.tsv results/blocks.tsv > results/block-effects.tsv
cat results/effects.tsv
cat results/block-effects.tsv
awk -F '\t' 'BEGIN {OFS="\t"; print "benchmark","variant","text_full_growth_percent"} NR==FNR {if ($2=="full") full[$1]=$3; next} FNR>1 {print $1,$2,100*(full[$1]/$3-1)}' \
  results/code-size.tsv results/code-size.tsv > results/code-size-effects.tsv
cat results/code-size-effects.tsv
```

配對資料以每個 JSON 自己的 full 作分母，再由 GNU datamash 計算五組 ratio 的幾何平均、中位數與範圍。主要 effect = `100 × (geomean(T_without/T_full) − 1)`；min/max 是五組的觀察範圍，不是信賴區間。

```bash
printf 'benchmark\tvariant\tn_pairs\tgeomean_ratio\tmedian_ratio\tmin_ratio\tmax_ratio\tmean_effect_pct\tsd_effect_pct\n' > results/paired-summary.tsv
for bench in 403.gcc 445.gobmk 462.libquantum; do
  jq -r --arg bench "$bench" \
    '(.results[] | select(.parameters.variant=="full") | .times[0]) as $full | .results[] | select(.parameters.variant!="full") | [$bench,.parameters.variant,(.times[0]/$full),(100*(.times[0]/$full-1)),$full,.times[0],input_filename] | @tsv' \
    "results/paired/$bench/"*.json > "results/paired/$bench/ratios.tsv"
  datamash -s -g 1,2 count 3 geomean 3 median 3 min 3 max 3 mean 4 sstdev 4 \
    < "results/paired/$bench/ratios.tsv" >> results/paired-summary.tsv
done
awk -F '\t' 'BEGIN {OFS="\t"; print "benchmark","variant","n_pairs","paired_geomean_effect_pct","min_effect_pct","max_effect_pct"} NR>1 {print $1,$2,$3,100*($4-1),100*($6-1),100*($7-1)}' \
  results/paired-summary.tsv > results/paired-effects.tsv
cat results/paired-effects.tsv
printf 'benchmark\tn_full\tmean_s\tsample_sd_s\tmedian_s\tmin_s\tmax_s\n' > results/paired-full-times.tsv
cat results/paired/{403.gcc,445.gobmk,462.libquantum}/ratios.tsv | \
  datamash -s -g 1 count 5 mean 5 sstdev 5 median 5 min 5 max 5 >> results/paired-full-times.tsv
printf 'benchmark\tvariant\tn\tmean_s\tsample_sd_s\tmedian_s\tmin_s\tmax_s\n' > results/paired-variant-times.tsv
cat results/paired/{403.gcc,445.gobmk,462.libquantum}/ratios.tsv | \
  datamash -s -g 1,2 count 6 mean 6 sstdev 6 median 6 min 6 max 6 >> results/paired-variant-times.tsv
```

## 9. 來源與適用邊界

- [指定 redistributable repository 的說明](https://github.com/miyuki/spec-cpu2006-redist/blob/39effd74541743ddc74d7b27cbbb315790c56d12/README)：這是原始與 SPEC 修改來源的可再散布部分，主要供研究參考。
- LLVM test-suite 工作負載定義：[403.gcc](https://github.com/llvm/llvm-test-suite/blob/main/External/SPEC/CINT2006/403.gcc/CMakeLists.txt)、[445.gobmk](https://github.com/llvm/llvm-test-suite/blob/main/External/SPEC/CINT2006/445.gobmk/CMakeLists.txt)、[462.libquantum](https://github.com/llvm/llvm-test-suite/blob/main/External/SPEC/CINT2006/462.libquantum/CMakeLists.txt)。本研究使用的輸入檔與參數已完整固定在上述命令。
- [LLVM 14 opt](https://releases.llvm.org/14.0.0/docs/CommandGuide/opt.html)、[LLVM passes](https://releases.llvm.org/14.0.0/docs/Passes.html)：指定 pass pipeline 與 IR verifier。
- [hyperfine](https://github.com/sharkdp/hyperfine)：計時與原始 JSON 匯出；[GNU datamash](https://www.gnu.org/software/datamash/)：分組統計。

完整 SPEC CPU2006 的 reportable 結果需另外具備完整 suite、官方 ref datasets／expected outputs、harness 與符合 run rules 的配置。本研究不填造缺少項目、不將三個 train workloads 推廣成完整 CPU2006 的效能結論。

## 10. 靜態 IR 診斷

以下計算整個 libquantum module 的靜態指令數；不是執行時 memory traffic，也不能直接跨不同 inlining 配置解讀成每次執行的存取量。

```bash
printf 'variant\talloca\tload\tstore\n' > results/462.libquantum/ir-memory-counts.tsv
for variant in baseline full no_mem2reg no_licm no_inline; do
  llvm-dis-14 "data/462.libquantum/$variant.opt.bc" -o "data/462.libquantum/$variant.opt.ll"
  printf '%s\t' "$variant" >> results/462.libquantum/ir-memory-counts.tsv
  grep -c '= alloca ' "data/462.libquantum/$variant.opt.ll" | tr '\n' '\t' >> results/462.libquantum/ir-memory-counts.tsv
  grep -c '= load ' "data/462.libquantum/$variant.opt.ll" | tr '\n' '\t' >> results/462.libquantum/ir-memory-counts.tsv
  grep -c '^  store ' "data/462.libquantum/$variant.opt.ll" >> results/462.libquantum/ir-memory-counts.tsv
done
cat results/462.libquantum/ir-memory-counts.tsv
for bench in 403.gcc 445.gobmk 462.libquantum; do
  awk '/^---/ {passed=($0=="--- !Passed")} /^Pass:/ {pass=$2} /^Name:/ && passed {count[pass "/" $2]++} END {for (key in count) print key, count[key]}' \
    "logs/$bench/full.remarks.yaml" | sort > "results/$bench/successful-remarks.txt"
done
cmp data/445.gobmk/full data/445.gobmk/no_dce
cmp data/462.libquantum/full data/462.libquantum/no_dce
for variant in full no_dce; do
  nm -S --defined-only "data/403.gcc/$variant" | awk '$3 ~ /^[tT]$/ {print $4,$2}' | sort \
    > "results/403.gcc/$variant.function-sizes.txt"
done
join results/403.gcc/full.function-sizes.txt results/403.gcc/no_dce.function-sizes.txt | \
  awk '$2!=$3' > results/403.gcc/dce-size-differences.txt
```
