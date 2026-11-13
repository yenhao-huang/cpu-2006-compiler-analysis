# 全 repo 實驗：建置、驗證與外部工具重現

接續 phase1/Reproduce.md 的工具與 pipeline。研究根目錄 `$STUDY_ROOT` 為 `/workspace/compiler_optimization/transform_pass_research`。新增十項資料及工作副本在 data/expansion，log 在 logs/expansion；原三項執行檔保留在 data。原 clone 不修改。只用外部工具與原程式，CMakeLists 是標準建置設定。正式工作量以 configs/all-workloads.tsv 為準；文中的短輸入 pilot 只用於解釋工作量選擇。

## 工具

C/C++ 使用 external/toolchain 的 LLVM 14。Fortran 與混合程式使用 external/toolchain19 的 LLVM/Clang/Flang 19.1.7，Debian .deb 位於 external/debs19，以 dpkg-deb -x 解壓，不改系統安裝。啟用時 PATH 指向對應 usr/bin，LD_LIBRARY_PATH 包含兩個 toolchain 的 usr/lib/x86_64-linux-gnu。

C 原始 IR 的共同 flags：`-std=gnu89 -O3 -Xclang -disable-llvm-passes -fno-strict-aliasing -fcommon -ffp-contract=off -march=x86-64-v3 -emit-llvm -c`。原 build 系統用 `-fembed-bitcode=all` 替代 `-emit-llvm`，再以 objcopy 擷取 `.llvmbc`。Fortran 使用 `flang-new-19 -O0 -emit-llvm -c`；probe 確認沒有 optnone/noinline。不同語言前端不可視為相同 lowering。

## 已確認的工作負載

| 目錄 | 實際程式與資料 | 正確性依據 |
|---|---|---|
| 400.perlbench | upstream Perl 5.8.7 miniperl，t/op/regexp.t | 原測試 947 個 TAP cases |
| 401.bzip2 | upstream bzip2 1.0.3，sample1/2/3.ref | 附帶 .bz2 黃金檔及解壓還原 |
| 435.gromacs | upstream Gromacs 3.1 mdrun，water tutorial，216 水分子、5000 steps、seed 1993 | 比對終態座標／數值 |
| 436.cactusADM | modified BenchADM，upstream test_Bench.par | 比對波形數值輸出 |
| 454.calculix | 此目錄實為 SPOOLES 2.2，FrontMtx/drivers/testGrid | 已知解的 maxabs error |
| 456.hmmer | modified hmmcalibrate，Docs/datasets/ig.hmm，固定 seed | 比對校準結果 |
| 465.tonto | modified Tonto，原手冊 H2O SCF 範例 | 完整 SCF 與 MO pair 分解比對 |
| 481.wrf | modified WRF，原附帶 ideal case | 60 steps 診斷與完整 NetCDF 比對 |
| 482.sphinx3 | upstream Sphinx3 0.4.1 livepretend，an4 Pittsburgh raw audio | P I T T S B U R G H 辨識結果 |
| 483.xalanc | upstream Xalan/Xerces，原 XML/XSL 範例 | 全部 53,615,062-byte XML 比對 |

403.gcc、445.gobmk、462.libquantum 的第一階段既有結果保留，詳見 phase1/Reproduce.md。

## 建置紀錄

- bzip2：編譯 blocksort.c huffman.c crctable.c randtable.c compress.c decompress.c bzlib.c bzip2.c，附加 `-D_FILE_OFFSET_BITS=64`，llvm-link-14 產生 raw.bc。
- HMMER：modified/456.hmmer/src/*.c，附加 `-DSPEC_CPU -DSPEC_CPU_LINUX -DSPEC_CPU_LP64` 及 src include。模型複製到 work 後執行，因 hmmcalibrate 會建立 .new；不在 clone 內跑。
- Perl：工作副本 Configure `-des -Dcc=clang-14 -Dusemymalloc=n -Uusedl -Uuseithreads`，`-Doptimize` 使用上述 embed flags。`make -j2 miniperl libs='-lm -ldl -lcrypt'`。擷取 libperl.a 每個 member，加 miniperlmain.o、opmini.o；**排除 archive 的 op.o**（opmini 已提供同名函式）。連結 -lm -ldl -lcrypt。
- Gromacs：工作副本 `src/kernel/xutils.c` 的局部 fmax 變數改名 gmx_local_fmax，避免現代 libm 同名。configure `--without-fftw --without-x --disable-fortran --disable-x86-asm --disable-cpu-optimization --disable-shared --enable-static`，CC/CFLAGS 使用上述 embed 設定；make -j2。擷取 libmd.a、libgmx.a，加 kernel 的 glaasje gctio init_sh ionize do_gct relax_sh xutils md mdrun genalg .o。設定 GMXLIB 到副本 share/top，用 grompp -f water.mdp -c spc216.gro -p water.top -o water.tpr；mdrun -s water.tpr -deffnm probe。
- Sphinx：configure `--disable-shared --enable-static` 配 embed CFLAGS；make -j2。擷取 libs3decoder.a libs3audio.a libutil.a，加 main_live_pretend.o parse_args_file.o live.o。cwd=source，執行 `livepretend model/lm/an4/an4.ctl model/lm/an4 model/lm/an4/args.an4.test`。
- Cactus：所有 src/*.c 與 src/*/*.c 用 clang-19，SPEC_CPU/SPEC_CPU_LINUX/SPEC_CPU_LP64/CCODE；include src 與 src/include。維持來源子目錄避免同名覆寫。src/*.F 用 flang-new-19 `-O0 -emit-llvm -c -DSPEC_CPU -DSPEC_CPU_LP64 -ffixed-form`。llvm-link-19 合併、flang-new-19 連結 -lm。
- SPOOLES：依原 makefile 的 serial 目錄列表編譯 */src/*.c（不含 MPI、MT），加 FrontMtx/drivers/testGrid.c，llvm-link-14、-lm -lpthread 連結。probe：`o3 0 stdout 12 12 12 0 64 10101 1 0 0 0 100 0 0 1`，upstream 成功 exit=1。
- Tonto：`cmake -S configs/tonto -B data/expansion/465.tonto/build -DCMAKE_Fortran_COMPILER=$STUDY_ROOT/external/toolchain19/usr/bin/flang-new-19`，`cmake --build ... -j2`。使用原本 USE_PRE_AND_POST_CONDITIONS 巨集，否則原程式空 ENSURE 會留下不合法單行 if。llvm-link-19 合併 CMake 的全部 .o（實際為 bitcode）。
- WRF：configs/wrf/CMakeLists.txt 使用原 arch/preamble 的 MAX_DOMAINS_F=21、CONFIG_BUF_LEN=8192，單機 EM core；NetCDF 使用 SPEC_CPU_CASE_FLAG 與 Flang 的符號命名一致。
- Xerces：runConfigure 的老 getopt 無法傳含空白的 -z，因此每個 flag 各用一個 -z；C++98 僅在 make CXX 覆寫，不能放共用 CFLAGS。先前 -j2 有 header copy race，改 -j1。

## 各配置共同後端

```bash
while IFS=$'\t' read -r variant pipeline; do
  opt-$version -passes="$pipeline" -debug-pass-manager "$base/raw.bc" -o "$base/$variant.opt.bc" 2> "$logdir/$variant.passes.log"
  llc-$version -O=2 -filetype=obj -relocation-model=pic "$base/$variant.opt.bc" -o "$base/$variant.o"
  "$driver" "$base/$variant.o" -lm -o "$base/$variant"
done < configs/pipelines.tsv
```

依程式加上述固定外部 link libraries；下方包含完整計時、驗證標準、來源建置與資料生成命令。實測結果見 Result.md。

## 科學程式與 LLVM 19 的已驗證補充

- LLVM 19 的預設 InstCombine 單次迭代在 Cactus 的 IOBasic_WriteInfo 觸發 `did not reach a fixpoint after 1 iterations`。`opt-19 --print-passes` 列出 max-iterations 參數，因此 `configs/pipelines-llvm19.tsv` 把所有顯式 instcombine 改成 `instcombine<max-iterations=100>`，全配置一致，仍保留 fixpoint 與 IR verifier。LLVM 14 不改動。不是忽略編譯器錯誤。
- Tonto 的 modified parser 需要 `atoms= { keys= { label= pos= } ... }`，且 `basis_set_kind= DZP`（大寫，原附帶基底檔使用 O:DZP/H:DZP 格式）；小寫 dzp 是舊檔案，用不同 label 格式。輸入與 basis symlink 在 data/expansion/465.tonto/work。成功產生 SCF energy -76.046397 以及全部 MO pair 分解；錯誤 probe 不算量測。
- WRF CMake 加 `SPEC_CPU_CASE_FLAG`：附帶 NetCDF 的 C/Fortran wrapper 因此輸出 nf_open_ 等符號，與 Flang ABI 一致。重新編譯完整程式。
- WRF 初始資料用原 `dyn_em/module_initialize_hill2d_x.F` 與 `main/ideal.F`，Flang19 `-ffree-form -cpp -O0 -emit-llvm`，同 configs/wrf 的 defines，include modified src、build 的 .mod 與 ideal 產出的 .mod。合併所有 WRF .o **排除 wrf.F90.o**，加入兩個 ideal bitcode，用 default<O3>、llc19、Flang19 連結。這是 repo 的原資料產生器，不是自製 runner。
- WRF case 複製 `original/481.wrf/WRFV2/test/em_hill2d_x/{namelist.input,input_sounding}`；只把 run_hours/end_hour 從 10 改 0、run_minutes/end_minute 改 20，維持 202×3×41 grid、20 秒 timestep。ideal 產生 wrfinput_d01、wrfbdy_d01。執行必須 `ulimit -s unlimited`（預設 8 MiB stack 導致 baseline segfault，無限 stack 成功）；baseline 與 full 的 60 steps、每步 em_t_2 診斷完全相同，至 0001-01-01_00:20:00。所有配置須一致套用此 stack 設定。
- Xerces 最終使用 `-t native`；原可選 IconvGNU backend 無法解析 message XML，故放棄該失敗 probe。現代 Clang 所需 `-include .../xercesc/framework/MemoryManager.hpp`。原 configure 在 O3 後面追加 `-O`，最終 rebuild 用 make `CXXFLAGS=...` 明列全部 flags，最後不存在 O1，避免 loop.unroll.disable。最終 log：xerces-final-make.log。
- Xalan：make CXX 加 `-std=gnu++98 -include cstring -include .../MemoryManager.hpp`；working copy 的 XalanArrayAllocator.hpp 對 `VectorType::value_type(0)` 加 typename。這些是語法／宣告相容性修正；全部配置通過完整 XML 比對。

## 最終輸入與外部工具計時設定

`configs/expansion-workloads.tsv` 每列是 benchmark、相對工作目錄與 hyperfine 命令模板；`{variant}` 由 hyperfine 原生 parameter-list 代入。`configs/expansion-prepare.tsv` 是每次計時前清掉本研究產生的輸出，清除時間不計入 benchmark。不是額外 benchmark runner。

Perl 每個時間樣本是 20 次原附帶 regexp.t（每次 947 cases），包含程序啟動與固定 shell 列舉開銷；其他每樣本一次程式。bzip2 input.ref 是把原 sample1/2/3.ref 順序連接 32 次，共 13,800,960 bytes，壓縮等級 3。HMMER fixed=500,num=10000,seed=1；SPOOLES 20³ nodes,seed=10101,1 RHS。Xalan 的 birds100.xml 是原 TransformToXercesDOM/birds.xml 移除首兩行 XML/Class 標頭與最後 Class 結尾後連接 100 次，再包回一個 Class 根節點；stylesheet 使用原 birds.xsl。輸入 917,156 bytes，原 native Xalan 輸出 1,072,362 bytes，baseline 完整輸出逐 byte 相同。

Xalan raw.bc 包含原 Makefile 的 ALL_OBJECTS、Xerces obj/LINUX 全部 .o、XalanExe.o 與 XalanMsgLib.o。以 `make -s --eval 'print-study-objects: ; @echo $(ALL_OBJECTS)' print-study-objects` 取得原物件列表（該列表相對 xalan/src/xalanc）；使用 objcopy 擷取 .llvmbc、llvm-link-14，再 clang++-14 -lm -lpthread 連結。未把 Xerces 固定成外部未消融 library。

最終資料應保留完整樣本、隨機順序、每個 workload 的 byte-identical full_control。每個 pass 的效益只定義為這個 workload、這個固定 pipeline 下移除該顯式 pass 的差異，不能將各欄相加，也不代表移除了 InstCombine、後端等所有具有相似作用的最佳化。

ISA：C/C++ LLVM14 使用 x86-64-v3 前端。Cactus C 部分也明訂 x86-64-v3；Flang19 與 WRF 的 C 前端保留預設 x86-64 target。所有同一 workload 的 variant 共享同一 raw.bc 與 llc -O=2，不跨不同 compiler/ISA 的 workload 比絕對時間。原始 attribute 稽核保存在 results/expansion/audit，勿把此混合語言實驗描述成全套統一 ISA 的官方 SPEC 測試。

## 建置與輸入的可重播命令

以下是乾淨工作副本的主要建置命令；既有成功產物可直接用後面的完整計時命令重測。不要把失敗 probe 的 log 當作成功 build。環境設定：

```bash
cd /workspace/compiler_optimization/transform_pass_research
export STUDY_ROOT="$PWD"
export PATH="$STUDY_ROOT/external/toolchain19/usr/bin:$STUDY_ROOT/external/toolchain/usr/bin:$PATH"
export LD_LIBRARY_PATH="$STUDY_ROOT/external/toolchain19/usr/lib/x86_64-linux-gnu:$STUDY_ROOT/external/toolchain/usr/lib/x86_64-linux-gnu"
# 用已保留的 LLVM19 deb 重建相同本機工具目錄：
for pkg in external/debs19/*.deb; do dpkg-deb -x "$pkg" external/toolchain19; done
sha256sum -c logs/toolchain19-packages.sha256
```

CMake 設定隨研究保留，兩項都使用 OBJECT library：產物的 .o 副檔名實際是 LLVM bitcode，避免自製 module dependency sorter。

```bash
for pair in '465.tonto tonto' '481.wrf wrf'; do
  read -r bench project <<< "$pair"
  cmake -S "configs/$project" -B "data/expansion/$bench/build" \
    -DCMAKE_Fortran_COMPILER="$STUDY_ROOT/external/toolchain19/usr/bin/flang-new-19" \
    -DCMAKE_C_COMPILER="$STUDY_ROOT/external/toolchain19/usr/bin/clang-19"
  cmake --build "data/expansion/$bench/build" -j2
  llvm-link-19 $(find "data/expansion/$bench/build/CMakeFiles/${project}_ir.dir" -name '*.o') \
    -o "data/expansion/$bench/raw.bc"
done
```

Cactus 的 C 檔自帶 SPEC_CPU 條件下的 thorn define；不把所有檔硬設為同一 thorn。

```bash
src="$STUDY_ROOT/spec-cpu2006-redist/modified/436.cactusADM/src"
mkdir -p data/expansion/436.cactusADM/raw
for file in "$src"/*.c "$src"/*/*.c; do
  relative=${file#"$src/"}
  mkdir -p "data/expansion/436.cactusADM/raw/$(dirname "$relative")"
  clang-19 -std=gnu89 -Wno-error=implicit-function-declaration -Wno-error=int-conversion \
    -O3 -Xclang -disable-llvm-passes -fno-strict-aliasing -fcommon -ffp-contract=off \
    -march=x86-64-v3 -DSPEC_CPU -DSPEC_CPU_LINUX -DSPEC_CPU_LP64 -DCCODE \
    -I"$src/include" -I"$src" -emit-llvm -c "$file" \
    -o "data/expansion/436.cactusADM/raw/${relative%.c}.bc"
done
(
  cd data/expansion/436.cactusADM/raw
  for file in "$src"/*.F; do
    flang-new-19 -O0 -emit-llvm -c -DSPEC_CPU -DSPEC_CPU_LP64 -ffixed-form \
      "$file" -o "$(basename "${file%.F}").bc"
  done
  llvm-link-19 $(find . -name '*.bc') -o ../raw.bc
)
```

由原 configure/make 產生嵌入 IR 的物件後，以 ar/objcopy 提取；例如 Perl 與 Gromacs（上方已列 configure flags 與原物件列表）：

```bash
(
  cd data/expansion/400.perlbench/raw
  ar x ../source/libperl.a
  for obj in *.o; do objcopy --dump-section .llvmbc="${obj%.o}.bc" "$obj"; done
  for obj in miniperlmain opmini; do
    objcopy --dump-section .llvmbc="$obj.bc" "../source/$obj.o"
  done
  llvm-link-14 $(find . -maxdepth 1 -name '*.bc' ! -name op.bc) -o ../raw.bc
)
(
  cd data/expansion/435.gromacs/raw
  for lib in md gmx; do
    mkdir -p "$lib"
    cd "$lib"
    ar x "../../source/src/${lib}lib/.libs/lib$lib.a"
    for obj in *.o; do objcopy --dump-section .llvmbc="${obj%.o}.bc" "$obj"; done
    cd ..
  done
  for obj in glaasje gctio init_sh ionize do_gct relax_sh xutils md mdrun genalg; do
    objcopy --dump-section .llvmbc="$obj.bc" "../source/src/kernel/$obj.o"
  done
  llvm-link-14 *.bc md/*.bc gmx/*.bc -o ../raw.bc
)
```

每一 bench 的 raw.bc 產生後，依語言選 version/driver 並建 12 個配置：

```bash
for bench in 400.perlbench 401.bzip2 435.gromacs 436.cactusADM 454.calculix \
             456.hmmer 465.tonto 481.wrf 482.sphinx3 483.xalanc; do
  version=14
  driver=clang-14
  pipeline_file=configs/pipelines.tsv
  link_flags=(-lm)
  case "$bench" in
    400.perlbench) link_flags+=(-ldl -lcrypt);;
    435.gromacs) link_flags+=(-ldl -lcrypt -lnsl);;
    454.calculix) link_flags+=(-lpthread);;
    482.sphinx3) link_flags+=(-ldl -lcrypt -lnsl);;
    483.xalanc) driver=clang++-14; link_flags+=(-lpthread);;
    436.cactusADM|465.tonto|481.wrf)
      version=19; driver=flang-new-19; pipeline_file=configs/pipelines-llvm19.tsv;;
  esac
  while IFS=$'\t' read -r variant pipeline; do
    base="data/expansion/$bench"
    opt-$version -passes="$pipeline" -debug-pass-manager "$base/raw.bc" \
      -o "$base/$variant.opt.bc" 2> "logs/expansion/$bench/$variant.passes.log"
    llc-$version -O=2 -filetype=obj -relocation-model=pic "$base/$variant.opt.bc" \
      -o "$base/$variant.o"
    "$driver" "$base/$variant.o" "${link_flags[@]}" -o "$base/$variant"
  done < "$pipeline_file"
done
```

Tonto input 完整內容在 data/expansion/465.tonto/work/stdin，WRF 的修改後 namelist 在 data/expansion/481.wrf/work/namelist.input。兩者都是資料，不是自製 benchmark 演算法。其他生成輸入：

```bash
for n in $(seq 1 32); do
  cat spec-cpu2006-redist/original/401.bzip2/bzip2-1.0.3/sample{1,2,3}.ref
done > data/expansion/401.bzip2/work/input.ref
(
  cd data/expansion/435.gromacs/work
  export GMXLIB="$STUDY_ROOT/data/expansion/435.gromacs/source/share/top"
  ../source/src/kernel/grompp -f water.mdp -c spc216.gro -p water.top -o water.tpr
)
{
  printf '<?xml version="1.0" encoding="UTF-8"?>\n<Class>\n'
  for n in $(seq 1 100); do
    sed '1,2d; /<\/Class>/d' \
      data/expansion/483.xalanc/xalan/samples/TransformToXercesDOM/birds.xml
  done
  printf '</Class>\n'
} > data/expansion/483.xalanc/work/birds100.xml
```

## 正確性標準

- Perl：所有配置與原未做 middle-end passes 的 native miniperl 輸出相同，947 個 `ok`、沒有 `not ok`。
- bzip2：原三份 sampleN.ref 以 -N 壓縮，逐 byte 比對 sampleN.bz2；再反向解壓逐 byte 比對 .ref。擴充 input.ref 的正式計時採 -3。
- Gromacs：每個配置跑完整 5000 steps，final .gro 與原 native build 逐 byte 相同。沒有只檢查 exit code。
- Cactus：每個配置的完整 test_Bench 輸出資料夾與 O3 reference 使用 diff -r，所有波形／scalar 檔相同。
- SPOOLES：原 driver 成功傳回 1，以 `status=$?; test "$status" -eq 1` 正規化；每個配置都必須出現 `maxabs error` 且在 [0,1e-8]。這是對原已知解的 residual 檢查，不單靠 exit=1。
- HMMER：固定 seed 的校準 stdout 完整相同，包含 mu/lambda/max。
- Tonto：完整 stdout 檔逐 byte 相同，包含 SCF 收斂與 MO pair energy decomposition，不只檢查進程成功。原 SPEC 修改將 elapsed time 換成 XX，不需要刪除數值列。
- WRF：60 steps 的所有 stdout 診斷以及整個 wrfout NetCDF 逐 byte 相同。初始 ideal generator 的 Fortran STOP 為原正常結束行為，真正成功以產出的資料與完整後續 simulation 驗證。
- Sphinx：原 livepretend 執行檔與每一配置的所有 `FWDXCT:` 分數／對齊結果及 `PARTIAL HYP:` 完全相同。其輸出包含計時與 ps 程序清單，所以不能把整個 stdout/stderr byte cmp 當作語音正確性。
- Xalan：原 native Xalan 產生 oracle.xml，每一配置的完整 XML 逐 byte cmp。

這些是供應的測試、已知解或 differential check；不聲稱取代官方 SPEC harness／獨立的完整數值正確性證明。Fortran 程式的 baseline 與 O3 都由相同 Flang frontend 產生，可能共享前端錯誤。

前端稽核發現 Xalan 的 `__clang_call_terminate` 是唯一帶 noinline 的函式（編譯器合成的例外終止 helper）；保留其原意。其他應用函式沒有整體 optnone/noinline，且 Xerces 最終沒有 O1 的 loop.unroll.disable metadata。

## 完整計時命令（建置與正確性檢查全部完成後才執行）

先為每個配置做一次暖機與一個診斷樣本，再做五輪相鄰 full/variant 配對。每對只用自己 JSON 的 full 時間作分母；每一對及每輪的 variant 次序隨機化並落盤。每輪另外量一次 full/full_control，二者完整 ELF byte-identical。單工執行，不同 benchmark 不平行。硬體／環境見 logs/expansion/environment.txt；使用 CPU 2，仍是共享主機，微小差異需對照 null control 與五對範圍。

```bash
cd "$STUDY_ROOT"
set -e
while IFS=$'\t' read -r bench cwd command; do
  mkdir -p "results/expansion/timing/$bench" "logs/expansion/timing/$bench"
  cp "data/expansion/$bench/full" "data/expansion/$bench/full_control"
  cmp "data/expansion/$bench/full" "data/expansion/$bench/full_control"
  prepare=$(awk -F '\t' -v b="$bench" '$1==b {print $2}' configs/expansion-prepare.tsv)
  cut -f1 configs/pipelines.tsv | shuf > "results/expansion/timing/$bench/warmup.order.txt"
  order=$(paste -sd, "results/expansion/timing/$bench/warmup.order.txt")
  (
    cd "$STUDY_ROOT/$cwd"
    hyperfine --warmup 1 --runs 1 --prepare "$prepare" \
      --parameter-list variant "$order" --export-json "$STUDY_ROOT/results/expansion/timing/$bench/initial.json" \
      "$command" > "$STUDY_ROOT/logs/expansion/timing/$bench/initial.log" 2>&1
  )
done < configs/expansion-workloads.tsv
for round in 1 2 3 4 5; do
  while IFS=$'\t' read -r bench cwd command; do
    prepare=$(awk -F '\t' -v b="$bench" '$1==b {print $2}' configs/expansion-prepare.tsv)
    { cut -f1 configs/pipelines.tsv | grep -vx full; printf 'full_control\n'; } | shuf \
      > "results/expansion/timing/$bench/order-$round.txt"
    while read -r variant; do
      order=$(printf '%s\n' full "$variant" | shuf | paste -sd,)
      printf '%s\n' "$order" > "results/expansion/timing/$bench/$round-$variant.order.txt"
      (
        cd "$STUDY_ROOT/$cwd"
        hyperfine --warmup 0 --runs 1 --prepare "$prepare" \
          --parameter-list variant "$order" \
          --export-json "$STUDY_ROOT/results/expansion/timing/$bench/$round-$variant.json" \
          "$command" > "$STUDY_ROOT/logs/expansion/timing/$bench/$round-$variant.log" 2>&1
      )
    done < "results/expansion/timing/$bench/order-$round.txt"
  done < configs/expansion-workloads.tsv
done
```

一次完整擴充執行為 10×12=120 個 initial 診斷樣本、10×11×5×2=1100 個消融配對樣本，以及 10×5×2=100 個 byte-identical 控制樣本，合計 **1320 個有效時間樣本**；暖機另計。已核對全部 JSON 與 exit_codes。第一階段 664 個樣本不覆寫；原三項另依下方命令重測，最終合計 1716 個新樣本。

全部 13 項計時結束後，只用 jq/datamash 彙整：

```bash
mkdir -p results/all-tasks
printf 'benchmark\tvariant\tpair\tratio\teffect_pct\tfull_s\tvariant_s\n' > results/all-tasks/paired-ratios.tsv
while IFS=$'\t' read -r bench cwd command; do
  jq -r --arg bench "$bench" \
    '(.results[]|select(.parameters.variant=="full")|.times[0]) as $full |
     .results[]|select(.parameters.variant!="full")|
     [$bench,.parameters.variant,input_filename,(.times[0]/$full),
      (100*(.times[0]/$full-1)),$full,.times[0]]|@tsv' \
    results/expansion/timing/"$bench"/[1-5]-*.json >> results/all-tasks/paired-ratios.tsv
done < configs/all-workloads.tsv
printf 'benchmark\tvariant\tn_pairs\tgeomean_ratio\tmedian_ratio\tmin_ratio\tmax_ratio\tmean_effect_pct\tsd_effect_pct\n' \
  > results/all-tasks/paired-summary.tsv
tail -n +2 results/all-tasks/paired-ratios.tsv | datamash -s -g 1,2 \
  count 4 geomean 4 median 4 min 4 max 4 mean 5 sstdev 5 >> results/all-tasks/paired-summary.tsv
```

效益為 `100*(geomean_ratio-1)`。min/max 是五對的觀察範圍，並非信賴區間；正值代表完整 pipeline 較快。initial 是診斷，主分析使用 paired。保留 null-control 行，不把它當成 pass 改善。

Gromacs 3.1 仍使用舊副檔名：grompp 的 `-o water.tpr` 實際產生 `water.tpr.tpb`，mdrun 的 `-s water.tpr` 會自動找到此檔。trajectory/energy 輸出為 `.trj`／`.ene`，prepare 表依實際副檔名清理；其餘 .gro/.log 同上。輸入 checksum 記錄實際 `.tpb` 檔。

### Xalan 正式工作量修訂

100 次 records 的 pilot full 太短，因此正式量測改為 **5000 次相同 records**。最終命令以 configs/expansion-workloads.tsv 為準，讀 birds5000.xml；原生程式 probe 4.28 s、full probe 1.06 s（這些 probe 不列入正式結果）。生成命令先保存一次 records，避免 5000 次重新解析來源：

```bash
sed '1,2d; /<\/Class>/d' \
  data/expansion/483.xalanc/xalan/samples/TransformToXercesDOM/birds.xml \
  > data/expansion/483.xalanc/work/birds.records
{
  printf '<?xml version="1.0" encoding="UTF-8"?>\n<Class>\n'
  for n in $(seq 1 5000); do cat data/expansion/483.xalanc/work/birds.records; done
  printf '</Class>\n'
} > data/expansion/483.xalanc/work/birds5000.xml
```

使用 native Xalan 得 oracle5000.xml，正式的所有配置再比對此較大工作量；小工作量驗證保留為 pilot evidence。這只擴增原資料筆數，沒有改 stylesheet 或撰寫 benchmark 程式。

機器碼身分檢查採 `objcopy -O binary --only-section=.text executable output.text.bin`，再 cmp/hash；相同 `.text` 的 pass removal 不可用時間起伏推論為該 pass 的指令效益。Perl、bzip2、Cactus、SPOOLES、Tonto、Sphinx 在移除 DCE 後 `.text` 完全相同，表示在本 pipeline 與後端之下，顯式 DCE 對這些程式的最終機器碼冗餘，不表示所有形式的死碼刪除都無效。

Sphinx 正式工作量使用原程式支援的多 utterance 控制檔：把原 an4.ctl 連接 20 次存成 data/expansion/482.sphinx3/an4x20.ctl，同一進程依序解碼相同錄音 20 次。此作法攤薄一次性 model initialization，沒有改 decoder；全部 12 個配置的每次 transcript 與 FWDXCT 分數都重新比對 native oracle。正式時間包含原程式的模型讀取、解碼及診斷處理；不聲稱是純解碼 kernel 時間。

### 原三項的同期間重測

第一階段 gcc byte-identical 控制曾出現 -29.48% 時間偏差；為讓全部 13 項主表來自同一量測階段，十項擴充完成後，再用 configs/recheck-workloads.tsv 對 gcc、gobmk、libquantum 做同樣 12 initial + 110 paired + 10 null-control 樣本。執行檔與輸入不改，不平行跑；舊 664 樣本留作歷史證據。最終新階段已完成 **1716** 樣本，主結果使用這批，而不混用舊時段的三項結果。

原三項的重測命令（必須等上方十項結束）：

```bash
while IFS=$'\t' read -r bench cwd command; do
  mkdir -p "results/expansion/timing/$bench" "logs/expansion/timing/$bench"
  cp "data/$bench/full" "data/$bench/full_control"
  cmp "data/$bench/full" "data/$bench/full_control"
  cut -f1 configs/pipelines.tsv | shuf > "results/expansion/timing/$bench/warmup.order.txt"
  order=$(paste -sd, "results/expansion/timing/$bench/warmup.order.txt")
  (
    cd "$STUDY_ROOT/$cwd"
    hyperfine --warmup 1 --runs 1 --prepare true --parameter-list variant "$order" \
      --export-json "$STUDY_ROOT/results/expansion/timing/$bench/initial.json" \
      "$command" > "$STUDY_ROOT/logs/expansion/timing/$bench/initial.log" 2>&1
  )
done < configs/recheck-workloads.tsv
for round in 1 2 3 4 5; do
  while IFS=$'\t' read -r bench cwd command; do
    { cut -f1 configs/pipelines.tsv | grep -vx full; printf 'full_control\n'; } | shuf \
      > "results/expansion/timing/$bench/order-$round.txt"
    while read -r variant; do
      order=$(printf '%s\n' full "$variant" | shuf | paste -sd,)
      printf '%s\n' "$order" > "results/expansion/timing/$bench/$round-$variant.order.txt"
      (
        cd "$STUDY_ROOT/$cwd"
        hyperfine --warmup 0 --runs 1 --prepare true --parameter-list variant "$order" \
          --export-json "$STUDY_ROOT/results/expansion/timing/$bench/$round-$variant.json" \
          "$command" > "$STUDY_ROOT/logs/expansion/timing/$bench/$round-$variant.log" 2>&1
      )
    done < "results/expansion/timing/$bench/order-$round.txt"
  done < configs/recheck-workloads.tsv
done
```

全 13 項摘要使用前面的 jq/datamash 命令，讀取已保存的 configs/all-workloads.tsv（合併 expansion-workloads.tsv 與 recheck-workloads.tsv 後依項目排序）。每個項目各有 61 個 JSON（1 initial + 5×12 pairs）、132 個有效樣本；總共 793 JSON、1716 個有效時間。所有 `exit_codes` 為 0；SPOOLES 的原成功 exit=1 已在命令內明確正規化。

## 原生 build 的完整 configure 命令補充

以下在已依前文建立的乾淨 source 工作副本執行；來源對應為 original/400.perlbench/perl-5.8.7、original/435.gromacs/gromacs-3.1、original/482.sphinx3/sphinx3-0.4.1。`source` 是上述來源的 cp -a 副本，並非 clone 本體。

```bash
embed_flags='-O3 -Xclang -disable-llvm-passes -fembed-bitcode=all -fno-strict-aliasing -fcommon -ffp-contract=off -march=x86-64-v3'
(
  cd data/expansion/400.perlbench/source
  sh Configure -des -Dcc=clang-14 -Dusemymalloc=n -Uusedl -Uuseithreads \
    -Dprefix="$STUDY_ROOT/data/expansion/400.perlbench/install" "-Doptimize=$embed_flags"
  make -j2 miniperl libs='-lm -ldl -lcrypt'
)
(
  cd data/expansion/435.gromacs/source
  sed -i 's/\bfmax\b/gmx_local_fmax/g' src/kernel/xutils.c
  CC=clang-14 CFLAGS="$embed_flags -std=gnu89" bash ./configure \
    --without-fftw --without-x --disable-fortran --disable-x86-asm \
    --disable-cpu-optimization --disable-shared --enable-static
  make -j2
)
(
  cd data/expansion/482.sphinx3/source
  CC=clang-14 CFLAGS="$embed_flags -std=gnu89" bash ./configure --disable-shared --enable-static
  make -j2
)
```

Xerces／Xalan 的原生來源工作副本分別為 original/483.xalanc/xerces-c-src_2_5_0 與 original/483.xalanc/xml-xalan/c。乾淨重建時先放好 header，避免舊 Makefile 的跨目錄 header 相依漏列；這只複製原檔，不改內容。

```bash
export XERCESCROOT="$STUDY_ROOT/data/expansion/483.xalanc/xerces"
export XALANCROOT="$STUDY_ROOT/data/expansion/483.xalanc/xalan"
export LD_LIBRARY_PATH="$STUDY_ROOT/external/toolchain/usr/lib/x86_64-linux-gnu:$XERCESCROOT/lib:$XALANCROOT/lib"
(
  cd "$XERCESCROOT/src/xercesc"
  bash ./runConfigure -p linux -c clang-14 -x clang++-14 -b 64 -m inmem -t native -n fileonly
  mkdir -p "$XERCESCROOT/include/xercesc"
  cp -a "$XERCESCROOT/src/xercesc/." "$XERCESCROOT/include/xercesc/"
  make -j1 CXX="clang++-14 -std=gnu++98 -include $XERCESCROOT/include/xercesc/framework/MemoryManager.hpp" \
    CXXFLAGS='-O3 -Xclang -disable-llvm-passes -fembed-bitcode=all -fno-strict-aliasing -ffp-contract=off -march=x86-64-v3 -fPIC -w -DPROJ_XMLPARSER -DPROJ_XMLUTIL -DPROJ_PARSERS -DPROJ_SAX4C -DPROJ_SAX2 -DPROJ_DOM -DPROJ_VALIDATORS -DXML_USE_NATIVE_TRANSCODER -DXML_USE_INMEM_MESSAGELOADER -DXML_USE_PTHREADS -DXML_BITSTOBUILD_64'
)
(
  cd "$XALANCROOT"
  sed -i 's/theBlockSize, VectorType::value_type(0)/theBlockSize, typename VectorType::value_type(0)/' \
    src/xalanc/PlatformSupport/XalanArrayAllocator.hpp
  bash ./runConfigure -p linux -c clang-14 -x clang++-14 -b 64 -m inmem \
    -z -O3 -z -Xclang -z -disable-llvm-passes -z -fembed-bitcode=all \
    -z -fno-strict-aliasing -z -ffp-contract=off -z -march=x86-64-v3 -z -fPIC
  make -j1 CXX="clang++-14 -std=gnu++98 -include cstring -include $XERCESCROOT/include/xercesc/framework/MemoryManager.hpp"
)
```

Xalan 原 Makefile 會在這些 flags 後追加 -O2，前端有效層級為 O2，但 LLVM middle-end 仍完全停用；Xerces 用明列 CXXFLAGS 保持 O3 前端。兩者都沒有 O1 的 unroll-disable metadata。重做既有工作副本時，先使用原 make clean 以免重用不同 flags 的舊 .o；正式 bitcode 後端仍是共同 llc -O=2。
