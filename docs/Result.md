# CPU2006 repository 全 13 項 transform-pass 消融結果

完成 repo 全部 **13 個編號目錄、每項 12 組配置、156 個執行檔**的建置與正確性檢查，以及 **1716 個有效計時樣本**（793 個 JSON，所有計時命令 exit=0）。八種單獨消融與雙 vectorizer 消融共通過 **117 項 pass absence audit**。來源 commit：`39effd74541743ddc74d7b27cbbb315790c56d12`，clone 保持乾淨。

主要結果是：WRF 的 loop vectorizer 與 LICM、Xalan 的 inlining，以及多個程式的 mem2reg 有明顯效益；SLP 在 Sphinx 改善速度，在 SPOOLES 反而變慢。以下使用固定輸入的程式執行時間，**不是官方 SPEC CPU2006 分數**。第一階段的 664 個舊樣本保留為歷史證據，沒有混入本報告估計。

## 實際評測範圍

| repo 項目 | 實際程式與固定工作量 | LLVM |
|---|---|---:|
| 400.perlbench | Perl 5.8.7 miniperl；原 regexp.t 的 947 TAP cases，每個時間樣本執行 20 次 | 14 |
| 401.bzip2 | bzip2 1.0.3；附帶 sample1/2/3.ref 串接 32 次，13,800,960 bytes，level 3 | 14 |
| 403.gcc | modified CPU2006 gcc；train integrate.in | 14 |
| 435.gromacs | Gromacs 3.1 mdrun；water tutorial，216 水分子、5000 steps、seed 1993 | 14 |
| 436.cactusADM | modified BenchADM；原 test_Bench.par，3×3×200、100 steps | 19 |
| 445.gobmk | modified CPU2006 gobmk；train arb.tst | 14 |
| 454.calculix | 目錄提供的 SPOOLES 2.2 testGrid driver；已知解 20³ 系統、seed 10101、1 RHS | 14 |
| 456.hmmer | modified HMMER 2.3 校準；ig.hmm、fixed 500、num 10000、seed 1 | 14 |
| 462.libquantum | modified CPU2006 libquantum；143 25 | 14 |
| 465.tonto | modified Tonto；原手冊 H2O RHF DZP 範例，SCF energy −76.046397 | 19 |
| 481.wrf | modified WRF；原 ideal hill2d_x 產生資料，202×3×41、60 steps、每步 20 秒 | 19 |
| 482.sphinx3 | Sphinx 3 0.4.1 livepretend；原 AN4 Pittsburgh 音訊，一個進程辨識 20 次 | 14 |
| 483.xalanc | Xalan 1.8 + Xerces 2.5；原 birds.xml records 重複 5000 次，原 birds.xsl | 14 |

454.calculix 的 repo 內容是 SPOOLES 庫與 driver，故本列是該元件的實測，不能推論成完整 CalculiX 應用程式的結果。其餘亦依實際 upstream／modified 程式與上述輸入解讀。全部目錄均有測量，沒有因缺少官方 SPEC 輸入而略過。

## 八種 pass 的消融效益

每格為 **100 × (geomean(T_without / T_full) − 1)**，單位 %；正值代表加上該 pass 的完整 pipeline 較快。這是五對相鄰量測的比值幾何平均，不是單次最快時間。

- `~`：五對觀察範圍跨越 0，方向不穩定。
- `≡`：消融後**整個 ELF 位元組相同**，不把時間差歸因於 pass。
- 沒有 `~` 也不代表統計顯著；需對照下方相同執行檔控制。所有 min/max 是觀察範圍，並非信賴區間。

| 項目 | Inlining | Unroll | Loop Vec | SLP | mem2reg | LICM | DCE | SimplifyCFG |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 400.perlbench | +5.10~ | -0.12~ | -2.56~ | +0.38~ | +29.78 | -0.52~ | ≡ | -1.01~ |
| 401.bzip2 | +3.01 | +1.38 | +0.33~ | +0.44~ | +56.72 | -0.87~ | ≡ | +3.68 |
| 403.gcc | +4.74 | -0.08~ | -0.25~ | -0.38~ | +19.67 | +0.51~ | -0.40~ | +2.57~ |
| 435.gromacs | +2.58~ | +0.66~ | +0.19~ | +0.99~ | +43.84 | +0.88 | -0.02~ | +1.31 |
| 436.cactusADM | +3.63 | -0.40~ | -4.11 | +1.45~ | -11.40 | +8.56 | ≡ | +1.50 |
| 445.gobmk | +3.36 | +1.57 | +0.23~ | +1.38~ | +22.44 | +0.82~ | ≡ | +2.77~ |
| 454.calculix | +5.21 | +1.74~ | -0.03~ | -11.28 | +2.42~ | -1.76~ | ≡ | +2.13~ |
| 456.hmmer | -3.87 | -2.60~ | +11.07 | +0.17~ | +47.49 | +2.66 | +0.20~ | +13.76 |
| 462.libquantum | +0.61~ | +0.14~ | -3.29 | -0.70~ | +0.92~ | +5.36~ | ≡ | +0.93~ |
| 465.tonto | +5.15~ | -6.89 | +2.91 | +0.44~ | +9.57 | +4.79 | ≡ | +0.28~ |
| 481.wrf | +1.63~ | +4.89 | +71.25 | -0.52~ | +7.97 | +38.64 | -0.41~ | +0.68~ |
| 482.sphinx3 | +2.50~ | +0.73~ | -0.46~ | +8.94 | +9.61 | +0.14~ | ≡ | +2.27~ |
| 483.xalanc | +176.07 | +0.28~ | +1.81~ | -1.20~ | +35.15 | -3.84~ | +0.61~ | +1.22~ |

1. **Inlining 的效益高度依賴程式。** Xalan +176.07%（五對 +128.22%～+218.39%），即 no_inline 約需 full 的 2.761 倍時間；其 .text 增加 17.72%。HMMER 則 −3.87%（−5.15%～−1.95%），同時 .text 增加 36.74%。Inlining 在全部 13 項增加 .text，範圍 +1.29%～+41.07%，中位數 +25.98%；不能只看省掉函式呼叫而忽略程式碼大小。時間與大小的關聯不能單獨證明 instruction-cache 是原因。
2. **mem2reg 是這組 pipeline 最廣泛的改善來源。** bzip2 +56.72%、HMMER +47.49%、Gromacs +43.84%、Xalan +35.15%、Perl +29.78%、gobmk +22.44%、gcc +19.67%；這七項的五對範圍皆遠離 0。Tonto、WRF、Sphinx 約 +8%～+10%；SPOOLES、libquantum 的方向不穩定。這是移除顯式 mem2reg 的條件效應，不能解讀為所有記憶體提升最佳化的總貢獻。
3. **Loop vectorizer 與 LICM 對 WRF 特別重要。** Loop vectorizer +71.25%（+68.17%～+73.75%）；LICM +38.64%（+37.73%～+39.56%）。HMMER 的 loop vectorizer 為 +11.07%（+8.33%～+13.29%）。這些幅度明顯大於相同 ELF 控制；未量測硬體計數器，因此不據此宣稱特定 CPU stall 已被消除。
4. **SLP 有正反案例。** Sphinx +8.94%（+6.07%～+14.13%）；SPOOLES −11.28%（−16.82%～−6.85%），即加上 SLP 後較慢。兩者皆通過輸出驗證，SPOOLES 同檔控制只有 −1.50%～+3.16%。不能把 vectorization 一概視為收益。
5. **SimplifyCFG 對 HMMER 有清楚改善：+13.76%**（+11.30%～+16.31%）。其他項目多在數個百分點內，與噪音接近。Unrolling 在全部項目增加 .text（+1.61%～+17.22%，中位數 +3.70%），但速度改善多不穩定；WRF +4.89% 仍有部分範圍接近控制噪音。Tonto 的 −6.89% 受 −27.51% 的單對偏差影響，不作普遍退步結論。
6. **DCE 在八項產生相同完整 ELF。** Perl、bzip2、gobmk、Cactus、SPOOLES、libquantum、Tonto、Sphinx 的顯式 DCE 在其餘 pipeline 與後端存在時，對最終執行檔冗餘。這不表示死碼刪除這類最佳化沒有價值；其他 pass 或後端可能已消除相同死碼。其餘五項的 DCE 時間效果也接近零且方向不穩。

Cactus 的 full 僅約 **29 ms**，同檔控制已有 −9.75%～−0.45% 的波動。其 mem2reg −11.40%、LICM +8.56% 等估計保留在表中，但不足以支持穩健的效益排序；程序啟動與排程占比不能忽略。較小效果應以更長且經驗證的工作量及更穩定主機再確認。

雙 vectorizer 消融額外檢查交互作用：WRF +73.53%、HMMER +11.88%、Sphinx +8.60%、SPOOLES −6.24%。WRF/HMMER 主要方向與 loop vectorizer 一致，Sphinx 與 SLP 一致；**不能將兩個單獨消融百分比相加**。完整五對數值及所有負向結果均在 [paired-summary.tsv](../results/all-tasks/paired-summary.tsv)。

## 絕對時間、baseline、標準 O3 與噪音控制

full 時間是每項 60 個配對 full 觀察值的中位數。baseline/full、O3/full 是五對**時間比**的幾何平均：小於 1 表示該對照比 full 快。baseline 保留共同前端與後端，只用 verify middle-end，不能稱為完整編譯器 O0。O3 使用 default<O3>，是較廣的實務最佳化參考，並非單一 pass 消融。

| 項目 | full 中位數（秒） | baseline/full | O3/full | 同檔控制速度變化 % [min,max] |
|---|---:|---:|---:|---:|
| 400.perlbench | 0.3517 | 1.435 | 1.016 | -2.36 [-6.79,+0.42] |
| 401.bzip2 | 1.8341 | 1.895 | 1.020 | +0.82 [-1.52,+4.88] |
| 403.gcc | 0.3066 | 1.413 | 0.939 | +0.90 [-3.53,+10.26] |
| 435.gromacs | 1.5655 | 1.827 | 0.921 | -0.19 [-2.19,+0.98] |
| 436.cactusADM | 0.0290 | 1.191 | 0.679 | -3.02 [-9.75,-0.45] |
| 445.gobmk | 2.8006 | 1.464 | 0.869 | +2.00 [+0.15,+5.50] |
| 454.calculix | 0.0849 | 2.126 | 0.971 | +0.55 [-1.50,+3.16] |
| 456.hmmer | 2.6854 | 1.830 | 0.315 | +0.45 [-1.24,+2.85] |
| 462.libquantum | 0.4934 | 2.399 | 0.898 | -0.66 [-3.89,+1.49] |
| 465.tonto | 0.4691 | 1.191 | 0.819 | -1.08 [-5.64,+3.06] |
| 481.wrf | 0.7566 | 3.278 | 1.009 | +0.51 [-2.85,+3.43] |
| 482.sphinx3 | 1.1101 | 1.564 | 0.909 | +1.27 [-1.72,+4.59] |
| 483.xalanc | 1.0184 | 3.085 | 0.833 | +4.61 [+1.30,+10.55] |

full_control 是 full 的逐位元組副本。即使相同 ELF，gcc 仍可觀察到 +10.26%、Xalan +10.55% 的單對偏差；gobmk 的五對控制甚至全為正。因此，表中 1%～5% 的差異及「五次同方向」都不能單獨證明 pass 的真實改善。保留所有離群值，不扣掉控制平均值，也不挑最快樣本。

標準 O3 在 HMMER 的時間比僅 0.315，顯示精簡 full pipeline 並非最佳可達速度；本研究回答的是列出的 pass 在固定共同 pipeline 下的條件貢獻，不是證明這組 pipeline 優於 O3。不同程式使用不同輸入尺度及部分不同工具鏈，不將跨程式絕對秒數或速度改善合成官方總分。

## 實驗方法與正確性

- 每項共 12 配置：baseline、full、八種單獨消融、no_vectors、default<O3>。每個 variant 共用該項 raw.bc、ISA、link libraries 與 llc -O=2 後端。消融刪除指定 pass 的所有顯式出現，其餘順序不變；不保證停用其他 pass 的相似轉換。
- full pipeline 為 `mem2reg → inline → mem2reg → instcombine → simplifycfg → loop-simplify → lcssa → loop-rotate → licm → indvars → loop-vectorize → slp-vectorizer → loop-unroll<O3> → instcombine → dce → simplifycfg → dce`；實際 adaptor/scope 見 [LLVM14 配置](../configs/pipelines.tsv)。LLVM19 全配置將顯式 InstCombine 迭代上限設為 100，以解決 Cactus fixpoint 錯誤，仍保留 verifier，見 [LLVM19 配置](../configs/pipelines-llvm19.tsv)。
- C/C++ 主要用 LLVM 14.0.6，混合／Fortran 用 LLVM 19.1.7。LLVM14 C/C++ 與 Cactus C 為 x86-64-v3，Flang 與 WRF C 保留預設 x86-64；不聲稱全套同一 ISA/lowering。原 Makefile 的 Xalan 前端最終 O2、Xerces O3，但共同停用 LLVM middle-end，詳見重現文件。
- Intel Core i7-14700K，固定 CPU 2；CPU 3 為 SMT sibling。主機共用、未關 turbo、沒有獨占核心；[環境紀錄](../logs/expansion/environment.txt) 與 [CPU 監測](../logs/expansion/timing-cpu-monitor.txt) 保留。編譯與正式計時不重疊，benchmark 不並行跑。
- 每項 12 個配置各一次暖機及一次 initial 診斷；之後五輪，每輪 11 組 full/variant 配對與 1 組 full/full_control，配置及配對順序隨機化並保存。每項 12+110+10=132 個有效樣本；13 項共 1716。主估計只用 paired，warmup 不計。命令的必要 shell、輸入載入及程序啟動計入時間；prepare 的輸出清理在計時外。
- 正確性依據包含 Perl 947 TAP、bzip2 黃金檔／還原、Gromacs 原生終態座標、Cactus O3 波形對照、SPOOLES 已知解殘差 ≤1e-8、HMMER 完整校準結果、Tonto SCF/MO 分解、WRF 60 steps 與整個 NetCDF、Sphinx 20 次辨識及分數、Xalan 全部 53,615,062 bytes XML。原三項採既有輸出比較。這些是所選工作量的驗證，不等同於證明所有輸入皆正確。

## 資料與重現

- [重現入口](Reproduce.md) 與 [完整建置、輸入、驗證、計時命令](Expansion-Reproduce.md)。只使用外部既有工具，沒有自製 runner、compiler wrapper 或 LLVM plugin。
- [全部命令](../configs/all-workloads.tsv)、[涵蓋清單](../results/expansion/coverage.tsv)、[原始 JSON 與執行順序](../results/expansion/timing)。
- [逐對比值](../results/all-tasks/paired-ratios.tsv)、[摘要](../results/all-tasks/paired-summary.tsv)、[時間分布](../results/all-tasks/timing-summary.tsv)、[.text 大小](../results/all-tasks/code-size.tsv)、[大小變化](../results/all-tasks/code-size-effects.tsv)、[ELF 身分](../results/all-tasks/elf-identity.tsv)。大小變化使用 `100×(full_text/without_text−1)`。
- [新增十項正確性](../results/expansion/correctness)、[原三項正確性](../results/correctness.txt)、[全部 117 項 pass audit](../results/all-tasks/pass-audit.tsv)。原三項的 24 項單獨消融紀錄在 results/pass-audit.txt，另三項雙 vectorizer 檢查由各自的 no_vectors.passes.log 核對並合併。
- [156 個執行檔雜湊](../results/all-tasks/binaries.sha256)、[輸入雜湊](../results/expansion/inputs.sha256)、[原三項輸入雜湊](../results/inputs.sha256)、[最後驗證紀錄](../logs/all-tasks-final-validation.txt)。
