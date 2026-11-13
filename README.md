# cpu-2006-compiler-analysis

本研究從 [`miyuki/spec-cpu2006-redist`](https://github.com/miyuki/spec-cpu2006-redist) 萃取程式與工作量，將原始碼轉成 LLVM IR，對八種 transform pass 做消融，再比較執行時間與程式碼大小。

已評測 repo 全部 **13 個編號目錄、每項 12 組配置、156 個執行檔**，取得 **1716 個有效計時樣本**，並完成 117 項 pass 檢查。[完整結果](docs/Result.md) 包含效益、退步案例與量測噪音。

```mermaid
flowchart LR
    A[固定版本的 SPEC 來源] --> B[選取程式與固定輸入]
    B --> C[Clang / Flang 產生 bitcode]
    C --> D[llvm-link 合併 raw.bc]
    D --> E[opt 套用 full 或消融 pipeline]
    E --> F[llc 與 linker 產生執行檔]
    F --> G[輸出正確性與 pass 檢查]
    G --> H[固定 CPU 的配對計時]
    H --> I[jq / datamash 統計與分析]
```

本 repo 保存文件、配置、計時 JSON 與分析證據。`data/` 和 `external/` 在本機依下列流程產生，不上傳；閱讀結果或重新分析既有 JSON 不需要這兩個目錄。

## 1. 取得固定版本的來源

```bash
git clone --recurse-submodules https://github.com/yenhao-huang/cpu-2006-compiler-analysis.git
cd cpu-2006-compiler-analysis
export STUDY_ROOT="$PWD"
git -C spec-cpu2006-redist rev-parse HEAD
```

來源 submodule 固定於 `39effd74541743ddc74d7b27cbbb315790c56d12`。若已 clone 但未取得來源，執行 `git submodule update --init --recursive`。

原 repo 的 `original/` 提供 upstream 程式、範例與資料，`modified/` 提供部分 CPU2006 修改版。我們保留原 clone，在 `data/` 建立工作副本和產物。此處的「萃取」包含兩件事：選出可建置的來源及對應工作量，再從編譯結果取得 LLVM bitcode；不是把所有目錄當成一個程式編譯。

## 2. 選取程式與固定輸入

| 項目 | 實際選取的程式 | 本次工作量 |
|---|---|---|
| 400.perlbench | original Perl 5.8.7 miniperl | regexp.t 的 947 個 TAP cases，每個樣本執行 20 次 |
| 401.bzip2 | original bzip2 1.0.3 | sample1/2/3.ref 串接 32 次，level 3 |
| 403.gcc | modified gcc | train integrate.in |
| 435.gromacs | original Gromacs 3.1 mdrun | water tutorial，216 水分子、5000 steps、固定 seed |
| 436.cactusADM | modified BenchADM | 原 test_Bench.par，3×3×200、100 steps |
| 445.gobmk | modified gobmk | train arb.tst |
| 454.calculix | original SPOOLES 2.2 testGrid driver | 原 driver 產生已知解的 20³ 系統 |
| 456.hmmer | modified HMMER 校準程式 | ig.hmm、fixed 500、num 10000、seed 1 |
| 462.libquantum | modified libquantum | 命令列參數 143 25 |
| 465.tonto | modified Tonto | 原手冊 H2O RHF DZP 範例 |
| 481.wrf | modified WRF + original ideal generator | hill2d_x，202×3×41、60 steps |
| 482.sphinx3 | original Sphinx livepretend | 原 AN4 Pittsburgh 音訊，在同一進程辨識 20 次 |
| 483.xalanc | original Xalan 1.8 + Xerces 2.5 | birds.xml records 重複 5000 次，原 birds.xsl |

固定輸入、參數、亂數 seed 與工作目錄後，所有配置執行同一工作量。[all-workloads.tsv](configs/all-workloads.tsv) 保存最終命令；[Expansion-Reproduce.md](docs/Expansion-Reproduce.md) 說明如何複製範例、擴增資料及執行原始資料產生器。

`454.calculix` 目錄實際提供 SPOOLES 庫與 driver，因此測的是該元件。這套研究涵蓋所選 repo 的 13 項，不是完整官方 SPEC CPU2006 套件，也不產生官方 SPEC 分數。

## 3. 從原始碼萃取 LLVM IR

本次環境為 Linux x86-64。C/C++ 主要使用 Clang/LLVM 14.0.6，Cactus、Tonto、WRF 使用 Clang/LLVM/Flang 19.1.7；另需 binutils、GCC、make、CMake、hyperfine、jq、GNU datamash、taskset。工具準備見 [重現入口](docs/Reproduce.md) 與 [LLVM14 套件取得命令](docs/phase1/Reproduce.md#1-取得固定來源與外部工具)。下列範例假設所需工具已在 PATH。

### 方法 A：直接從 C/C++ 產生 bitcode

以 libquantum 為完整範例。以下命令在 repo 根目錄以 Bash 執行，產物放到獨立的 `data/readme-example/`，不覆寫已發表的計時結果。

```bash
set -euo pipefail
export STUDY_ROOT="$PWD"
export EXAMPLE_ROOT="$STUDY_ROOT/data/readme-example"
mkdir -p "$EXAMPLE_ROOT"/{raw,bin,logs,results,timing}
(
  cd "$EXAMPLE_ROOT/raw"
  clang-14 -std=gnu89 -O3 -Xclang -disable-llvm-passes \
    -fno-strict-aliasing -fcommon -ffp-contract=off -march=x86-64-v3 \
    -DSPEC_CPU -DSPEC_CPU_LINUX -DSPEC_CPU_LP64 \
    -emit-llvm -c \
    "$STUDY_ROOT/spec-cpu2006-redist/modified/462.libquantum/src/"*.c
  llvm-link-14 ./*.bc -o ../raw.bc
)
llvm-dis-14 "$EXAMPLE_ROOT/raw.bc" -o "$EXAMPLE_ROOT/raw.ll"
sha256sum "$EXAMPLE_ROOT/raw.bc"
```

`-emit-llvm` 讓各個 translation unit 輸出 `.bc`；`llvm-link` 合併成共同的 `raw.bc`，讓跨檔案 inlining 成為可能。這不同於一般逐檔編譯的設定。

`-O3 -Xclang -disable-llvm-passes` 設定前端行為但停用 LLVM middle-end passes，避免前端先跑完本研究要比較的最佳化。也要檢查 IR 的 `optnone`、`noinline`、`llvm.loop.unroll.disable` 等標記，確認沒有意外封鎖最佳化；Xalan 的編譯器合成例外終止 helper 保留原本 noinline 屬性。

### 方法 B：從原 configure/make 的 object 萃取

Perl、Gromacs、Sphinx、Xerces/Xalan 有既有建置系統，需讓原系統處理生成檔與相依關係。編譯時使用 `-O3 -Xclang -disable-llvm-passes -fembed-bitcode=all`，將 bitcode 放進 object 的 `.llvmbc` section。以下是命令形式，物件列表與實際路徑見 [完整建置說明](docs/Expansion-Reproduce.md)：

```text
ar x libexample.a
objcopy --dump-section .llvmbc=example.bc example.o
llvm-link-14 example.bc other.bc ... -o raw.bc
```

只合併實際連結所需的物件，避免重複符號。例如 Perl 使用 `opmini.o` 時，必須排除 archive 中提供重複函式的 `op.o`。不同子目錄的同名來源檔也要保留目錄結構，避免 bitcode 被覆蓋。

### 方法 C：Fortran 與混合語言

Fortran 使用 `flang-new-19 -O0 -emit-llvm -c`；C 部分用相同版本的 Clang。Tonto／WRF 透過 [CMake 設定](configs) 排定 module 相依，再由 `llvm-link-19` 合併。此處已檢查 Flang 產物沒有整體 optnone/noinline；不能把 Clang 的 O0 屬性行為直接套用到 Flang。

不同 LLVM major version 的 IR 不混用。同一 benchmark 的所有配置固定前端、raw.bc、ISA 與後端；跨語言的前端 lowering 不視為相同。

## 4. 建立完整 pipeline 與消融配置

[LLVM14 pipeline](configs/pipelines.tsv) 與 [LLVM19 pipeline](configs/pipelines-llvm19.tsv) 明列每個配置實際執行的 passes。消融從 full 刪掉目標 pass 的**所有顯式出現**，其餘順序不變。

| 配置 | 用途 |
|---|---|
| `baseline` | middle-end 僅執行 verify，保留共同前端與後端 |
| `full` | 完整的研究 pipeline |
| `no_inline` | 移除 Inlining |
| `no_unroll` | 移除 Loop unrolling |
| `no_loop_vectorize` | 移除 Loop vectorizer |
| `no_slp` | 移除 SLP vectorizer |
| `no_mem2reg` | 移除 mem2reg |
| `no_licm` | 移除 LICM |
| `no_dce` | 移除 DCE |
| `no_simplifycfg` | 移除 SimplifyCFG |
| `no_vectors` | 同時移除兩種 vectorizer，觀察交互作用 |
| `o3` | 標準 `default<O3>`，作為實務對照 |

這是指定 pipeline 的消融，不是從 default<O3> 刪除某一 pass。InstCombine、其他 pass 及後端仍可能做語意相近的轉換。LLVM19 的顯式 InstCombine 全部統一設定 `max-iterations=100`，處理 Cactus 的 fixpoint 問題，並保留 verifier。

接續 libquantum 範例，每個配置從同一份 raw.bc 出發；`opt` 改 IR，`llc` 產生機器碼，Clang 最後連結：

```bash
while IFS=$'\t' read -r variant pipeline; do
  opt-14 -passes="$pipeline" -debug-pass-manager \
    "$EXAMPLE_ROOT/raw.bc" -o "$EXAMPLE_ROOT/$variant.opt.bc" \
    2> "$EXAMPLE_ROOT/logs/$variant.passes.log"
  llc-14 -O=2 -filetype=obj -relocation-model=pic \
    "$EXAMPLE_ROOT/$variant.opt.bc" -o "$EXAMPLE_ROOT/$variant.o"
  clang-14 "$EXAMPLE_ROOT/$variant.o" -lm -o "$EXAMPLE_ROOT/bin/$variant"
done < configs/pipelines.tsv
```

## 5. 驗證輸出、pass 與程式碼大小

先確認計算結果，再比較速度。libquantum 使用獨立 GCC 建置作為輸出對照：

```bash
gcc -std=gnu89 -O2 -fno-strict-aliasing -fcommon \
  -ffp-contract=off -march=x86-64-v3 \
  -DSPEC_CPU -DSPEC_CPU_LINUX -DSPEC_CPU_LP64 \
  spec-cpu2006-redist/modified/462.libquantum/src/*.c \
  -lm -o "$EXAMPLE_ROOT/bin/oracle"
"$EXAMPLE_ROOT/bin/oracle" 143 25 > "$EXAMPLE_ROOT/results/oracle.out"
while IFS=$'\t' read -r variant pipeline; do
  "$EXAMPLE_ROOT/bin/$variant" 143 25 > "$EXAMPLE_ROOT/results/$variant.out"
  cmp "$EXAMPLE_ROOT/results/oracle.out" "$EXAMPLE_ROOT/results/$variant.out"
  size -A "$EXAMPLE_ROOT/bin/$variant" > "$EXAMPLE_ROOT/results/$variant.size.txt"
done < configs/pipelines.tsv
```

其他程式使用原測試、黃金檔、已知解殘差或數值／輸出比較。例如 Perl 檢查 TAP、bzip2 比對壓縮與解壓結果、WRF 比對完整 NetCDF、Xalan 比對完整 XML。不能僅因 exit code 為 0 就認定正確；SPOOLES 原 driver 的成功狀態反而是 1，計時命令已明確正規化。

再從 `-debug-pass-manager` 紀錄檢查被消融的 pass 確實沒有執行。例如：

```bash
grep -q 'Running pass: PromotePass on' "$EXAMPLE_ROOT/logs/full.passes.log"
if grep -q 'Running pass: PromotePass on' "$EXAMPLE_ROOT/logs/no_mem2reg.passes.log"; then
  printf 'ERROR: no_mem2reg still ran PromotePass\n' >&2
  exit 1
fi
```

機器碼大小以 `.text` section 比較，見 [code-size.tsv](results/all-tasks/code-size.tsv)。另外比較完整 ELF 的雜湊；若 full 與消融版逐位元組相同，就不能把計時差歸因於該 pass。

## 6. 固定輸入並做配對計時

正式流程固定 CPU 2，先暖機，再將 full 與一個 variant 相鄰執行；每輪隨機排列配置與配對內順序，保存實際順序。每項有 12 個 initial 診斷樣本，以及五輪配對；每輪還有一對 full 與其逐位元組副本 full_control，用來觀察噪音。

每項有效樣本數為 `12 + 5 × (11 + 1) × 2 = 132`，13 項合計 1716；暖機另計，主效果只用 paired 樣本。編譯與計時分開，不並行執行 benchmark；輸出清理放在 hyperfine 的 prepare 階段。

以下只是 libquantum 的**一對命令範例**，不能代替五輪正式實驗。CPU 編號須在自己的可用 affinity 範圍內；正式重現所有項目的暖機、清理與隨機化命令見 [完整計時流程](docs/Expansion-Reproduce.md#完整計時命令建置與正確性檢查全部完成後才執行)。

```bash
hyperfine --warmup 1 --runs 1 --parameter-list variant full,no_mem2reg \
  --export-json "$EXAMPLE_ROOT/timing/example-pair.json" \
  "taskset -c 2 '$EXAMPLE_ROOT/bin/{variant}' 143 25 > /dev/null"
```

## 7. 從原始 JSON 萃取比值並分析

每對 JSON 各有自己的 full 與 variant 時間。先算 `T_variant / T_full`，再取同一項配置五對比值的幾何平均；不用不同時段的 full 平均值當共同分母。

下面可直接對 repo 已保存的 13 項 JSON 執行，只需要 jq、GNU datamash 與 coreutils，**不需要重新編譯或下載 data**。輸出寫入暫存目錄，保留已發表結果：

```bash
analysis_dir=$(mktemp -d)
printf 'benchmark\tvariant\tpair\tratio\teffect_pct\tfull_s\tvariant_s\n' \
  > "$analysis_dir/paired-ratios.tsv"
while IFS=$'\t' read -r bench cwd command; do
  jq -r --arg bench "$bench" \
    '(.results[]|select(.parameters.variant=="full")|.times[0]) as $full |
     .results[]|select(.parameters.variant!="full")|
     [$bench,.parameters.variant,input_filename,(.times[0]/$full),
      (100*(.times[0]/$full-1)),$full,.times[0]]|@tsv' \
    results/expansion/timing/"$bench"/[1-5]-*.json \
    >> "$analysis_dir/paired-ratios.tsv"
done < configs/all-workloads.tsv
printf 'benchmark\tvariant\tn_pairs\tgeomean_ratio\tmedian_ratio\tmin_ratio\tmax_ratio\tmean_effect_pct\tsd_effect_pct\n' \
  > "$analysis_dir/paired-summary.tsv"
tail -n +2 "$analysis_dir/paired-ratios.tsv" | datamash -s -g 1,2 \
  count 4 geomean 4 median 4 min 4 max 4 mean 5 sstdev 5 \
  >> "$analysis_dir/paired-summary.tsv"
printf 'Analysis saved to %s\n' "$analysis_dir"
```

報告中的速度變化為：

```text
速度變化 (%) = 100 × (geomean(T_without / T_full) − 1)
程式碼大小變化 (%) = 100 × (full_text / without_text − 1)
```

正的速度變化表示加上該 pass 後較快，負值表示較慢。五對的 min/max 是觀察範圍，不是信賴區間；保留離群值並對照 full_control。不同 pass 的百分比不能相加。

| 工作量 | Pass | 本次速度變化 |
|---|---|---:|
| WRF | Loop vectorizer | +71.25% |
| WRF | LICM | +38.64% |
| Xalan | Inlining | +176.07% |
| bzip2 | mem2reg | +56.72% |
| Sphinx | SLP vectorizer | +8.94% |
| SPOOLES | SLP vectorizer | −11.28% |

這些例子顯示同一類最佳化可有正反效果。小幅效果需考慮噪音；Cactus 約 29 ms 的短工作量尤其容易受啟動與排程影響。八項程式的 DCE 消融產生相同完整 ELF，報告將其標為 `≡`，不當作速度改善。

## 8. 找到完整證據與重現細節

| 內容 | 位置 |
|---|---|
| 13 項效能、大小與限制分析 | [docs/Result.md](docs/Result.md) |
| 全套重現入口、工具與驗證順序 | [docs/Reproduce.md](docs/Reproduce.md) |
| gcc／gobmk／libquantum 的建置命令 | [docs/phase1/Reproduce.md](docs/phase1/Reproduce.md) |
| 其餘十項來源萃取、相容性修正與輸入產生 | [docs/Expansion-Reproduce.md](docs/Expansion-Reproduce.md) |
| LLVM14／19 的完整 pass pipeline | [configs/](configs) |
| 793 個 JSON 與量測順序 | [results/expansion/timing/](results/expansion/timing) |
| 每對時間比值、摘要、程式碼大小、ELF 身分與 pass audit | [results/all-tasks/](results/all-tasks) |

歷史文件與工作量 TSV 保留原根路徑 `/workspace/compiler_optimization/transform_pass_research`；重跑時須替換為自己的研究目錄。那些文件中的「本機已保留套件／產物」描述原實驗主機，新 clone 須依建置步驟產生。SHA-256 清單是產物證據，對本機產物的校驗要在重建後執行。

只使用既有外部工具與 shell 編排，沒有自製 benchmark runner、compiler wrapper 或 LLVM plugin。最終主表採用新階段的 1716 個樣本，第一階段 664 個舊樣本保留作歷史證據而不混用。`data/`、工具鏈、大型 compiler traces 與大型 XML／NetCDF 驗證輸出留在本機。
