# CPU2006 Transform Pass 消融實驗

完成日期：2026-10-25（Asia/Taipei）。三個 CPU2006 子項、12 種配置，共 36 個執行檔全部通過差分輸出驗證；八項消融的 24 個 pass audit 也通過。完成 **664 個有效計時樣本**（原設計 324、相鄰配對 330、額外 gcc 相同執行檔控制 10），暖機不計入。

**本次最一致的單項改善訊號是 mem2reg：gcc +21.09%、gobmk +24.17%，各五對均為正向。** libquantum 的 mem2reg 效益無法可靠區分。Inlining 增加約 26–41% `.text`，但三個工作負載都沒有穩定的時間改善證據。其他小幅差異也受共享主機噪音限制，不能據此建立通用 pass 排名。

這些結果只適用於下述三個 train 工作負載及固定 pipeline；不是完整 SPEC CPU2006 分數。

## 主要消融結果

每格為 **加入該 pass 的速度提升百分比 [五對最小值, 最大值]**；用相鄰 `T_without/T_full` 的幾何平均計算。正值代表 full 較快。區間是觀察範圍，不是信賴區間；跨零表示五對改善方向不一致。

| 加入的 pass | 403.gcc | 445.gobmk | 462.libquantum |
| --- | ---: | ---: | ---: |
| Inlining | +2.58% [−6.17, +7.17] | +1.69% [−6.21, +9.12] | +0.88% [−4.52, +5.89] |
| Loop unrolling | −0.78% [−4.41, +1.31] | +0.64% [−3.45, +6.46] | +1.89% [−0.86, +5.58] |
| Loop vectorizer | −0.76% [−5.34, +4.79] | −0.86% [−6.25, +3.89] | +7.25% [−3.94, +35.60] |
| SLP Vectorizer | −1.84% [−4.58, +2.73] | +3.27% [−2.09, +9.03] | −1.65% [−12.84, +20.27] |
| mem2reg | **+21.09% [+16.56, +27.38]** | **+24.17% [+20.80, +31.49]** | −4.19% [−31.28, +23.42] |
| LICM | −3.67% [−8.32, +2.26] | +1.40% [−1.82, +3.58] | +1.77% [−14.75, +17.18] |
| DCE | −9.15% [−29.19, −2.41] † | +4.80% [−0.02, +15.54] ‡ | −6.71% [−15.40, +0.79] ‡ |
| SimplifyCFG | +0.39% [−11.99, +4.99] | +1.71% [−2.40, +5.28] | −0.44% [−21.75, +10.04] |
| 兩個 vectorizer 一起 | −2.68% [−9.77, +0.24] | +0.28% [−1.29, +2.11] | +1.64% [−4.41, +3.92] |

† gcc DCE 雖五對都呈負向，但幾何平均被一對約 −29% 拉動；五對中位數效果為 **−2.94%**。額外複製 full 的 byte-identical 控制也出現 **−29.48% 到 +3.95%** 的範圍（幾何平均 −5.71%），因此不能可靠宣稱 DCE 本身造成 9.15% 退步。

‡ gobmk、libquantum 的 full/no_dce **完整 ELF 相同**，所以表中的非零數字只是量測差異，**不是 DCE 收益或損失**。這兩組的實際機器碼效應為零。

所有原始樣本均保留，沒有刪掉造成大幅偏差的 pair。配對縮短了時間差，仍無法完全消除背景干擾；「五對方向一致」是本次的描述性證據，並非多重比較修正後的統計顯著性結論。

## 絕對時間與整體對照

相鄰配對中的 full 各有 55 次執行；下表提供時間尺度，**不要用這個合併 full 平均取代每一對自己的分母**。

| full 工作負載 | 中位數（秒） | 平均 ± 樣本標準差（秒） | 最小–最大（秒） |
| --- | ---: | ---: | ---: |
| 403.gcc | 0.3455 | 0.3503 ± 0.0443 | 0.3052–0.5341 |
| 445.gobmk | 3.1239 | 3.0984 ± 0.2391 | 2.6956–3.8010 |
| 462.libquantum | 0.5405 | 0.5802 ± 0.0977 | 0.4759–0.8162 |

| 整體對照 | gcc | gobmk | libquantum |
| --- | ---: | ---: | ---: |
| full 相對 baseline 速度 | 1.446× | 1.436× | 2.345× |
| 上列五對速度範圍 | 1.334–1.675× | 1.419–1.475× | 2.098–2.520× |
| O3 / full 時間比（幾何平均） | 0.923 | 0.882 | 0.951 |
| O3 / full 五對時間比範圍 | 0.766–0.988 | 0.870–0.896 | 0.886–1.113 |

full 相對 baseline 的改善在五對皆明顯。標準 O3 在 gobmk 的五對均比 full 少約 10.4–13.0% 時間，顯示這個為消融而設計的 pipeline 並不是最佳效能 pipeline。gcc 的 O3 五對也較快，但改善幅度受一個較大偏差影響；libquantum 的範圍跨越 1，不能可靠判定勝負。這些整體對照不能拿來歸因於某一個 pass。

## 八個 pass 的判讀

1. **Inlining**：三個效果範圍都跨零，卻有明確的 code size 增加。移除呼叫開銷與暴露更多最佳化機會是機制，不保證這些 train 輸入變快；本次沒有量到足夠穩定的收益來支持通用判斷。
2. **Loop unrolling**：`.text` 增加 2.40–6.29%，時間差異則小且跨零。降低迴圈控制開銷不等於必然改善整體程式，不能僅靠是否展開就推論效能。
3. **Loop vectorizer**：三個程式都有實際 vectorized remarks。libquantum 的 +7.25% 不穩定：其中位數效果僅 **+0.80%**，而範圍到 +35.60%，因此不宣稱獲得穩定 SIMD 加速。
4. **SLP Vectorizer**：code size 變化很小，三個時間範圍皆跨零。靜態向量化事件數不代表熱門執行路徑的覆蓋率，未取得可分離於噪音的速度收益。
5. **mem2reg**：在 gcc、gobmk 出現本次最一致且幅度較大的正向結果；libquantum 無法判定。它把可提升的 stack allocas 轉為 SSA 值／PHI，並非直接將任意記憶體存取映射到實體暫存器。後續 passes 與 backend 的作用仍存在，因此不能由單一消融外推它的全部價值。
6. **LICM**：確實有 hoist 與 memory promotion，但三個時間範圍都跨零。可移出的是在該迴圈內不變、且搬移符合安全條件的運算；本次沒有證據證明搬移事件一定落在決定總時間的熱點。
7. **DCE**：gobmk、libquantum 的結果是機器碼層級零差異；gcc 的 `.text` 只少 48 bytes，函式大小差異出現在 `convert_for_assignment` 與 `mtherr`。gcc 的負向計時不能與額外相同 binary 控制的噪音可靠區分。這不代表 dead-code elimination 在其他 pipeline 或程式中沒有用。
8. **SimplifyCFG**：三個程式 `.text` 都減少（約 0.45–2.76%），但時間改善尚不能可靠辨識。簡化／合併控制流程的空間收益比本次的時間差異更明確。

同時移除兩種 vectorizer 的結果也跨零，沒有足夠證據聲稱兩者互補或互斥；個別 speedup 相加並不是交互作用估計。本研究的限制是共享主機、少量配對與 train 子集，適合確認轉換、code size 代價與較大的效能訊號，不足以對百分之幾的差異建立普遍結論。

## 研究問題與範圍

比較 Inlining、Loop unrolling、Loop vectorizer、SLP Vectorizer、mem2reg、LICM、DCE、SimplifyCFG 在固定 pipeline 中的邊際效能與 code size 影響。採用 leave-one-out 消融；另外比較同時移除兩個 vectorizer 的組合，檢查交互作用。

來源為使用者指定的 `git@github.com:miyuki/spec-cpu2006-redist.git`，固定 commit `39effd74541743ddc74d7b27cbbb315790c56d12`。此 repository 是 CPU2006 的可再散布部分，並不是完整 licensed suite。實測範圍如下：

| CPU2006 benchmark | 輸入 | 工作型態 | 量測涵蓋範圍 |
| --- | --- | --- | --- |
| 403.gcc | `data/train/input/integrate.in -o /dev/null` | C 編譯器、樹／圖結構處理與分支 | train 的這個完整 input |
| 445.gobmk | `--quiet --mode gtp < data/train/input/arb.tst` | 圍棋搜尋、分支與遊戲狀態更新 | train 的 arb input；不是全部 train inputs |
| 462.libquantum | `143 25` | Shor 模擬、複數算術與陣列／量子狀態操作 | 官方 train 參數 |

工作負載定義參考 LLVM test-suite 的 [gcc](https://github.com/llvm/llvm-test-suite/blob/main/External/SPEC/CINT2006/403.gcc/CMakeLists.txt)、[gobmk](https://github.com/llvm/llvm-test-suite/blob/main/External/SPEC/CINT2006/445.gobmk/CMakeLists.txt)、[libquantum](https://github.com/llvm/llvm-test-suite/blob/main/External/SPEC/CINT2006/462.libquantum/CMakeLists.txt)。沒有使用自製 microbenchmark 替代 CPU2006 程式。

本結果不是 SPECint2006、SPECfp2006、SPEC rate 或完整 CPU2006 分數，也不代表 ref 工作負載。libquantum ref `1397 8` 曾做耗時試跑，超過兩分鐘後手動終止；其不完整輸出及計時沒有納入統計。

## 實驗設計

同一個 benchmark 的所有版本均從相同 `raw.bc` 出發，固定 ISA、後端及連結選項。Clang 14.0.6 的前端設定 `-O3 -Xclang -disable-llvm-passes`，先產生未經 middle-end passes 最佳化的 bitcode，再以 `llvm-link` 合併 translation units。所有來源沒有修改。

這項設計允許跨 translation-unit inlining；不能與標準逐檔編譯配置混同。沒有使用 fast-math；固定 `-ffp-contract=off`、`-fno-strict-aliasing`、`-fcommon`、`-march=x86-64-v3`，以配合舊版 C 原始碼並控制目標指令集。

完整 pipeline：

```text
function(mem2reg),cgscc(inline),function(
  mem2reg,instcombine,simplifycfg,loop-simplify,lcssa,
  loop(loop-rotate),loop-mssa(licm),loop(indvars),
  loop-vectorize,slp-vectorizer,loop-unroll<O3>,
  instcombine,dce,simplifycfg,dce)
```

換行僅供閱讀，實際可執行字串在 `configs/pipelines.tsv` 與 `Reproduce.md`。兩次 mem2reg 用於 inline 前後的 local promotion；兩次 SimplifyCFG／DCE 的所有顯式出現都一併移除。支援用的 InstCombine、LoopSimplify、LCSSA、LoopRotate、IndVarSimplify 保持原位。

| 版本 | 處理 |
| --- | --- |
| baseline | 不執行研究中的 IR 最佳化 pipeline，僅驗證 IR |
| full | 上述完整 pipeline |
| no_inline / no_unroll / no_loop_vectorize / no_slp | 分別移除對應 pass |
| no_mem2reg / no_licm / no_dce / no_simplifycfg | 分別移除對應 pass 的所有顯式出現 |
| no_vectors | 同時移除 Loop 與 SLP vectorizer |
| o3 | LLVM `default<O3>` middle-end 對照 |

所有版本都使用 `llc -O=2 -filetype=obj -relocation-model=pic` 與相同 linker。baseline 並非完整的「零最佳化」，因為相同 backend 仍會做 instruction selection、register allocation 與 machine passes。o3 也不是另一組單項消融。

每項消融對照的是 **指定 named IR pass 在這個 pipeline 內的邊際貢獻**，不是在所有編譯階段完全消除該類轉換。特別是：

- 移除 mem2reg 時沒有另外放入 SROA 偷做同樣的 promotion；但 LICM 自身仍能做 loop memory promotion，其他簡化與後端也可能減少存取。
- 移除 DCE 後，InstCombine、SimplifyCFG 與後端仍可能清除 dead instructions。
- 移除 SimplifyCFG 不代表其他 passes 不再簡化控制流程。
- Loop vectorizer 可能自行 interleave；移除 LoopUnrollPass 不代表機器碼中絕不出現任何展開形式。
- 各項 speedup 不具可加性，效益依賴 pass 順序與其他 passes。

`opt -debug-pass-manager` 保存實際 pass 紀錄；audit 同時檢查 full 有執行該 pass、消融版本沒有執行該 pass。LLVM 預設輸入／輸出 verifier 保留，libquantum 建置另曾使用 `-verify-each`。後者不改變最佳化語意，但對 gcc 模組逐子步驟重驗的額外成本很高，因此正式重現命令使用預設 verifier。

## 正確性與統計方法

先使用獨立 GCC 12 的 `-O2` 建置參考版本，再比對每個 variant：gcc 產生的 assembly 檔與 stdout、gobmk 的完整 stdout、libquantum 的完整 stdout，使用 `cmp` 逐位元比較，且要求成功退出。這是跨編譯器的差分正確性檢查，無法證明不存在共同 bug，也不能取代缺少的官方 expected outputs／SPEC harness。

量測使用 hyperfine 1.15.0，固定 CPU 2、單工執行。先做三個區塊，各自隨機打散 12 個 variant 的順序；每個區塊先暖機一次，再量三次，每個 benchmark/variant 共九個有效樣本。所有樣本均保留，使用 GNU datamash 計算平均與樣本標準差，另保留中位數、最小值與最大值。

第一輪 libquantum 的 full / no_dce 平均為 0.8300 / 0.5186 秒，但兩者完整 ELF 相同，顯示整輪比較受到嚴重的非 pass 干擾，與時段漂移相符。這不單獨證明是哪一種微架構或系統因素造成。主機 `mpstat` 顯示背景活動持續變化；容器沒有 CPU quota 或 throttling。CPU 2 的 sibling 在診斷期間約 80.6% idle，其他候選核心並沒有一致更安靜，所以沒有中途換核心或挑選看起來較漂亮的一輪。

為縮短對照的時間差，另追加每個 variant **五組相鄰 full/variant 配對**，每對隨機交換順序，每組也打散 variant 順序。每次 hyperfine 呼叫只量這兩個程式各一次；前面的完整量測已暖機，不再增加配對暖機。11 個非 full 配置 × 3 個 benchmark × 5 組 = 165 對、330 個有效時間樣本。主要消融結論使用各對 ratio 的幾何平均；原本 324 個有效樣本完整保留作時段敏感度診斷，兩種設計不混在一起算平均。配對仍無法保證消除瞬間負載變化，因此保留五對範圍與 byte-identical DCE 控制。

主要效能表的 **speedup (%) = 100 × (geomean(T_without / T_full) − 1)**，每對使用自己的 full 作分母。正值表示加入該 pass 較快；負值表示加入該 pass 較慢。這不是時間下降百分比。五對的 min/max 是觀察範圍，不是 95% 信賴區間；五對同方向也不等於正式顯著性檢定。Code size 以 ELF `.text` section 的 bytes 計算，變化率為 `100 × (text_full / text_without − 1)`；正值表示加入 pass 後變大。

環境是共享 i7-14700K 主機上的 Debian 12 x86-64 container。CPU 2 的 SMT sibling 是 CPU 3；未獨占 sibling。CPU governor 為 powersave，未停用 Turbo，其他使用者的系統負載持續存在。固定 affinity 與亂序區塊能減少部分偏差，無法消除頻率、cache、SMT 和背景工作負載的干擾。因此小幅差異、區塊方向反轉或與相同機器碼不一致的時間差異，不能直接判為 pass 的穩定因果效益。

## Code size 與實際轉換證據

full 的 `.text` 大小分別為 gcc **3,149,302 bytes**、gobmk **933,981 bytes**、libquantum **40,270 bytes**。下表表示「加入該 pass 後，相對於移除版本」的大小變化，正值為變大：

| 加入的 pass | gcc | gobmk | libquantum |
| --- | ---: | ---: | ---: |
| Inlining | +34.96% | +41.07% | +25.98% |
| Loop unrolling | +3.70% | +6.29% | +2.40% |
| Loop vectorizer | +0.59% | +2.03% | +4.35% |
| SLP Vectorizer | +0.078% | +0.021% | +0.040% |
| mem2reg | −11.52% | +3.60% | −8.24% |
| LICM | +0.93% | +2.10% | +5.31% |
| DCE | −0.0015%（48 bytes） | 0% | 0% |
| SimplifyCFG | −2.76% | −0.45% | −1.10% |
| 兩個 vectorizer 一起 | +0.67% | +2.05% | +4.40% |

Inlining 的 code size 成本在三個程式都很明確。mem2reg 的大小效果則不是單向：促成後續最佳化也可能產生更多機器碼，不能認定「少了 load/store，整個 binary 就一定變小」。本研究未量測 instruction-cache misses、branch misses 或 IPC，因此不把時間變化直接歸因於這些微架構因素。

LLVM 的成功 remarks 提供下列靜態轉換事件數；它們涵蓋整個 module，並非執行次數或熱點佔比：

| 事件 | gcc | gobmk | libquantum |
| --- | ---: | ---: | ---: |
| Inlined callsite | 17,889 | 3,208 | 167 |
| LICM Hoisted | 16,420 | 6,522 | 1,144 |
| LICM memory promotion | 111 | 78 | 11 |
| FullyUnrolled + PartialUnrolled | 684 + 392 | 272 + 144 | 41 + 11 |
| Loop Vectorized | 180 | 121 | 22 |
| SLP stores / horizontal reduction / list | 938 / 28 / 51 | 48 / 9 / 11 | 0 / 0 / 2 |

libquantum 的 whole-module 靜態 IR 在 full 中有 203 個 alloca、1,313 個 load、762 個 store；移除 mem2reg 後為 679、2,556、1,365。這證明輸入 IR 與消融有實質差異，但不能把靜態指令數當作動態 memory traffic。沒有 inlining 時的數字也不可直接橫比，因為函式本體複製會改變整個 module 的大小。

**DCE 有兩個機器碼層級的零差異對照**：gobmk 與 libquantum 的 full 和 no_dce 連完整 ELF 都逐位元相同（`cmp` 通過，SHA-256 相同），不只是 `.text` 一樣大。因此這兩組任何非零計時差異都不能歸因於 DCE 的程式碼效果。gcc 則有 48 bytes 差異；仍需看時間變化是否超過噪音。

Loop vectorizer 把多個迴圈 iteration 的操作加寬，SLP 則把可打包的純量操作合併。它們會受到相依性、控制流程與成本模型限制；向量化過程本身也可能部分展開迴圈。這是區分 LoopUnrollPass 與所有形式的 unrolling 的原因。[LLVM 14 vectorizers](https://releases.llvm.org/14.0.0/docs/Vectorizers.html)

## 證據與重現

- `docs/Reproduce.md`：僅依賴外部工具的完整命令，沒有自製 runner、plugin 或分析程式。
- `configs/pipelines.tsv`：全部 12 種設定。
- `logs/*/*.passes.log`、`*.remarks.yaml`：pass 執行與 LLVM remarks。
- `results/correctness.txt`、`results/pass-audit.txt`：輸出驗證與 pass audit。
- `results/*/round-*.json`：hyperfine 原始逐次樣本；`order-*.txt` 是順序。
- `results/summary.tsv`、`effects.tsv`、`blocks.tsv`、`block-effects.tsv`：外部工具產生的統計。
- `results/paired/*/*.json`、`ratios.tsv`、`paired-summary.tsv`、`paired-effects.tsv`：相鄰配對、每對分母與五組幾何平均；主要效能分析依據。
- `results/null-control/403.gcc/`：額外五對完全相同的 gcc 執行檔控制，與 pass 效果分開保存。
- `results/*/*.sections.txt`、`*.text.sha256`：code size 與機器碼識別。
- `logs/environment.txt`、`logs/toolchain-packages.sha256`：硬體／工具版本與套件校驗值。

LLVM pass 定義與工具介面參考 [LLVM 14 passes](https://releases.llvm.org/14.0.0/docs/Passes.html) 與 [opt](https://releases.llvm.org/14.0.0/docs/CommandGuide/opt.html)。
