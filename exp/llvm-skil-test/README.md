# exp/llvm-skil-test：用 llvm-optimization skill 對 SPEC CPU2006 子集做效能分析與優化

本實驗測試 [gmh5225/awesome-llvm-security](https://github.com/gmh5225/awesome-llvm-security) 的
`llvm-optimization` skill（`.claude/skills/llvm-optimization/SKILL.md`）在這個 repo 的 benchmark 上能帶來什麼：
照 skill 的建議做一輪，再用 skill 教的分析工具（opt remarks、`-stats`）加上 callgrind 找出瓶頸，
推導出下一輪優化，最後和母研究的 `o3` 對照。

結果與解讀見 **[Result.md](Result.md)**。

## 範圍

| 項目 | 本實驗 | 母研究 |
|---|---|---|
| Benchmark | 401.bzip2、403.gcc、445.gobmk、456.hmmer、462.libquantum（純 C） | 13 項 |
| 工作量 | 與母研究 `configs/all-workloads.tsv` 相同的命令與輸入 | 同左 |
| 工具鏈 | LLVM 18.1.3（Ubuntu 套件） | LLVM 14.0.6 / 19.1.7 |
| 機器 | 2 vCPU 雲端 VM（Xeon，Sapphire Rapids），計時固定 CPU 1 | i7-14700K，CPU 2 |
| 前端 | 同母研究：`-O3 -Xclang -disable-llvm-passes -fno-strict-aliasing -fcommon -ffp-contract=off -march=x86-64-v3` | 同左 |
| 後端 | `llc -O=2 -relocation-model=pic` | 同左 |

數值不能直接和母研究的時間比較（機器與 LLVM 版本都不同）；本實驗內部的比較都從同一份 raw.bc 出發。

## 變體（[configs/variants.tsv](configs/variants.tsv)）

| 層級 | 變體 | 內容 |
|---|---|---|
| ref | `baseline`、`full`、`o3` | 母研究的對照；`full` 用母研究 LLVM19 版 pipeline（LLVM14 版在 LLVM18 會觸發 InstCombine fixpoint 中止） |
| skill | `lto` | skill 推薦的 LTO：`lto-pre-link<O3>,internalize,lto<O3>`（等同 `clang -flto` 對已合併模組做的事） |
| extra | `o3_native`、`lto_native` | 把 IR 的 `target-cpu` 從 x86-64-v3 改成主機 CPU（sapphirerapids），讓向量化成本模型與後端都看到 AVX-512 |
| extra | `lto_pgo`、`lto_pgo_native` | LTO + instrumentation PGO；訓練輸入刻意和計時輸入不同（見 [scripts/workloads.sh](scripts/workloads.sh)） |
| analysis | `o3_ldist` | remarks 顯示 hmmer 熱迴圈因 `UnsafeDep` 未向量化並建議 `#pragma clang loop distribute(enable)`；以 `-enable-loop-distribute` 全域開啟，不改原始碼 |
| analysis | `o3_tbaa` | remarks 顯示熱函式的 GVN/LICM 主要卡在 alias（`LoadClobbered`）；前端改用 `-fstrict-aliasing` 產生 raw.tbaa.bc |
| analysis | `best_pgo`、`best_pgo_native` | TBAA + loop distribute + LTO + PGO（+ native） |
| control | `o3_control` | 與 `o3` 逐位元組相同的副本，用來估計量測噪音 |

## 重現

```bash
git submodule update --init --depth 1          # spec-cpu2006-redist
sudo apt-get install -y clang-18 llvm-18 lld-18 libclang-rt-18-dev hyperfine valgrind
cd exp/llvm-skil-test
./scripts/10_build_raw.sh                                  # raw.bc + GCC -O2 oracle + 輸入
RAW=raw.tbaa STRICT_ALIASING=1 ./scripts/10_build_raw.sh   # TBAA 版 raw
./scripts/20_build_variants.sh                             # 全部變體（403.gcc 每個 PGO 變體約 4 分鐘）
./scripts/30_verify.sh                                     # 每個變體的輸出必須與 GCC oracle 逐位元組相同
JOBS=2 ./scripts/50_callgrind.sh                           # 指令數 + 熱點（native 變體除外：valgrind 不支援 AVX-512）
python3 scripts/60_remarks.py                              # opt remarks 摘要
ROUNDS=7 ./scripts/40_time.sh                              # 與 o3 相鄰的配對計時（不要同時跑其他工作）
python3 scripts/70_analyze.py                              # results/summary.tsv
```

產物在 `data/llvm-skil-test/`（git-ignored）；`results/` 保存計時 JSON、指令數、remarks 摘要、正確性與大小。

## 檔案

| 路徑 | 內容 |
|---|---|
| `scripts/` | 建置、驗證、計時、profiling、分析 |
| `configs/variants.tsv` | 每個變體的輸入 raw、目標 CPU、額外 opt 旗標與 pipeline |
| `results/summary.tsv` | 合併表：正確性、配對速度變化、指令數、`.text` 大小 |
| `results/paired-ratios.tsv` | 每輪 `T_variant / T_o3` |
| `results/instr-counts.tsv`、`results/callgrind/*.hot.txt` | callgrind 指令數與熱點函式 |
| `results/remarks-summary.tsv`、`results/remarks-hot.tsv` | opt remarks 統計（全部 / 熱點函式） |
| `results/correctness.tsv`、`results/code-size.tsv` | 輸出雜湊比對、`.text` 大小與 ELF 雜湊 |
