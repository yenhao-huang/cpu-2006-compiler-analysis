# 13 項 transform-pass 消融：重現入口

GitHub 使用者可先閱讀 [README 的來源萃取到分析流程](../README.md)。`data/` 與 `external/` 不隨 repo 發布，請依下列建置步驟產生；下方「已保留套件」描述原實驗主機。只重新分析 repo 中的計時 JSON 不需要這些本機產物。

研究根目錄：`/workspace/compiler_optimization/transform_pass_research`。來源固定為 `miyuki/spec-cpu2006-redist` commit `39effd74541743ddc74d7b27cbbb315790c56d12`。原 clone 保持乾淨；相容性修改只在 `data/expansion` 工作副本。

使用 Git、Debian 套件、Clang/LLVM/Flang、原 configure/make、CMake、binutils、hyperfine、jq、GNU datamash/coreutils。**沒有自製 benchmark runner、compiler wrapper 或 LLVM plugin。** Shell 只列舉檔案／配置及呼叫外部工具；CMakeLists 是建置設定。輸入來自 repo 範例或原程式的產生功能。

## 1. 設定既有工具

```bash
cd /workspace/compiler_optimization/transform_pass_research
export STUDY_ROOT="$PWD"
export PATH="$STUDY_ROOT/external/toolchain19/usr/bin:$STUDY_ROOT/external/toolchain/usr/bin:$PATH"
export LD_LIBRARY_PATH="$STUDY_ROOT/external/toolchain19/usr/lib/x86_64-linux-gnu:$STUDY_ROOT/external/toolchain/usr/lib/x86_64-linux-gnu"
clang-14 --version
flang-new-19 --version
hyperfine --version
sha256sum -c logs/toolchain-packages.sha256
sha256sum -c logs/toolchain19-packages.sha256
```

套件已保留在 external/debs、external/debs19，只解壓至本目錄，沒有更改系統安裝。需支援 x86-64-v3 的 CPU；本次單工固定 CPU 2。若更換 CPU 編號，修改配置表並記錄環境，不能宣稱精確重播本次時間。

## 2. 從原始碼建置

- [第一階段建置命令](phase1/Reproduce.md)：clone、LLVM14 工具，以及 403.gcc、445.gobmk、462.libquantum。其舊時間結果是歷史資料，**不作最終主表的分母**。
- [其餘十項完整建置／輸入／驗證說明](Expansion-Reproduce.md)：包含混合 C/Fortran、原生 configure/make 的 bitcode 擷取、WRF ideal 資料產生器及相容性修改。
- [LLVM14 pipeline](../configs/pipelines.tsv)、[LLVM19 pipeline](../configs/pipelines-llvm19.tsv)：每項 12 配置，八種單獨消融、雙 vectorizer 消融、baseline、full、標準 O3。
- [Tonto CMake](../configs/tonto/CMakeLists.txt)、[WRF CMake](../configs/wrf/CMakeLists.txt) 與 [最小 source patches](../configs/patches)。

同一程式的各配置都從共同 raw.bc 開始，後端固定 llc -O=2；消融移除指定 pass 的所有顯式出現，其他順序不變。LLVM19 的 InstCombine 統一允許最多 100 次迭代並保留 verifier。這是指定 pipeline 的消融，並非從 default<O3> 刪除 pass，也不代表停用其他 pass／後端所有相似語意的最佳化。

## 3. 正確性與輸入

完整項目、實際程式與工作量見 [coverage.tsv](../results/expansion/coverage.tsv)。454.calculix 目錄實際提供 SPOOLES 庫與 driver，本研究測該 driver；不是缺少來源的完整 CalculiX。

[驗證說明](Expansion-Reproduce.md#正確性標準) 與 [逐配置輸出](../results/expansion/correctness) 涵蓋 TAP、黃金壓縮檔、已知解殘差、模擬座標／波形、NetCDF、SCF 能量、辨識結果及 XML。原三項的驗證見 [correctness.txt](../results/correctness.txt)。WRF 必須 ulimit -s unlimited；SPOOLES driver 的成功狀態為 1，命令明確正規化為 0。

```bash
sha256sum -c results/expansion/inputs.sha256
sha256sum -c results/expansion/raw-bitcode.sha256
sha256sum -c results/inputs.sha256
sha256sum -c results/all-tasks/binaries.sha256
sha256sum -c results/all-tasks/final-configs.sha256
```

以上是提供的測試或 differential validation，沒有宣稱取代官方 SPEC harness。

## 4. 重新計時

[完整計時與分析命令](Expansion-Reproduce.md#完整計時命令建置與正確性檢查全部完成後才執行) 直接呼叫 hyperfine；執行時不要並行編譯或跑其他 benchmark。

- [新增十項命令](../configs/expansion-workloads.tsv) 與 [每次輸出清理](../configs/expansion-prepare.tsv)。
- [原三項同流程重測](../configs/recheck-workloads.tsv)，必須在前十項結束後執行。
- [全部 13 項最終命令清單](../configs/all-workloads.tsv)。

每個配置先一次暖機與一個初始診斷樣本，再量五輪相鄰 full/variant 配對；每輪還有 full/full_control 相同 ELF 控制。每項 132 個有效樣本，全部共 1716，暖機不計。保留所有樣本，沒有挑最快值或刪除離群值。

確切執行順序存在 results/expansion/timing/* 的 order 檔。若要重播順序，保留檔案、略過 shuf，改為讀取相應 order 檔；重新亂序是重做相同設計，不是逐次重播。

## 5. 彙整與解讀

jq 展開 hyperfine JSON，datamash 計算五對比值的幾何平均、範圍與其他摘要；命令見上方完整說明。加入 pass 的速度變化為 `100 × (geomean(T_without / T_full) − 1)`，正值代表 full 較快。最小／最大值是觀察範圍，不是信賴區間。不能把不同 pass 百分比相加。

[最終結果](Result.md)、[合併表格](../results/all-tasks)、[原始計時](../results/expansion/timing)、[全部 117 項 pass absence audit](../results/all-tasks/pass-audit.tsv) 互相對應。第一階段舊 664 個樣本與報告保留在原目錄及 docs/phase1，最終主表使用新的 13 項資料，不混合不同階段估計。
