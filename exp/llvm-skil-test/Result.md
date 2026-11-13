# 結果：llvm-optimization skill 對 SPEC CPU2006 子集的效能分析與優化

實驗設定與重現步驟見 [README.md](README.md)。所有數字來自 [results/summary.tsv](results/summary.tsv)。

## 結論

1. **照 skill 字面建議（LTO）幾乎沒有收益。** `lto` 在 5 個工作量中有 4 個落在噪音範圍內；hmmer 反而**穩定變慢 6.6%**（7 對中只有 1 對較快），libquantum 的 +8.8% 只有 4/7 對較快，不能確認。
2. **真正有用的是 skill 教的分析方法（opt remarks / `-Rpass-missed`）。** 拿 remarks 對照 callgrind 熱點，找出兩個具體瓶頸，推導出的優化帶來本實驗最大的效果：
   - hmmer：remarks 指出熱迴圈因 `UnsafeDep` 沒有向量化，並建議 loop distribution → `o3_ldist` **快 24.2%**（7/7）。
   - 熱點函式的 GVN/LICM 普遍卡在 alias（`LoadClobbered`）→ 改用 strict aliasing（TBAA）。libquantum 指令數 **−40%**、向量化迴圈從 7 個增加到 74 個，但時間只 +6.0%（5/7），不能確認有加速。
3. **全部組合（`best_pgo` = TBAA + loop distribution + LTO + PGO）：hmmer 快 49.1%、gcc 快 15.1%**，兩者都是 7/7 對較快。bzip2 和 gobmk 沒有任何變體穩定超過 `o3`。
4. 改用主機 CPU（AVX-512）**沒有可靠收益**，hmmer 的 `best_pgo_native`（+38.3%）比不用 AVX-512 的 `best_pgo`（+49.1%）還慢。

全部 60 個執行檔（5 項 × 12 變體）的輸出都與獨立 GCC -O2 版本逐位元組相同。

## 怎麼判斷「真的有差」

這台是 2 vCPU 的共享雲端機，噪音比母研究的實體機大很多。兩個逐位元組相同的執行檔（`o3_control`，以及在 bzip2/gcc/gobmk/libquantum 上與 `o3` 完全相同的 `o3_ldist`）量出來的幾何平均差異在 **−3.1% ～ +1.1%** 之間，單一配對比值則落在 0.78～1.33。

因此本報告只把**幾何平均超出 ±5%、且 7 對全部同方向**的結果視為確定效果；6/7 視為「傾向」，其餘視為噪音。另以 callgrind 指令數（Ir，可重複、不受噪音影響）輔助判讀，但指令數不等於時間。

速度變化 = `100 × (1 / geomean(T_variant / T_o3) − 1)`，正值代表比 `o3` 快；每輪比值都使用相鄰執行的 `o3`。

## 主要結果（相對 `o3`）

| 工作量 | 變體 | 速度變化 | 較快對數 | 指令數 | `.text` |
|---|---|---:|:-:|---:|---:|
| 456.hmmer | **best_pgo** | **+49.13%** | 7/7 | −32.85% | −60.94% |
| 456.hmmer | best_pgo_native | +38.25% | 7/7 | n/a | −60.70% |
| 456.hmmer | **o3_ldist** | **+24.23%** | 7/7 | −25.90% | +0.74% |
| 456.hmmer | lto_pgo | +10.72% | 7/7 | −3.07% | −62.96% |
| 403.gcc | **best_pgo** | **+15.11%** | 7/7 | −11.02% | +5.81% |
| 403.gcc | lto_pgo_native | +10.27% | 6/7（傾向） | n/a | +5.86% |
| 403.gcc | lto_pgo | +7.20% | 5/7 | −10.61% | +5.10% |
| 462.libquantum | o3_native | +8.72% | 6/7（傾向） | n/a | +3.50% |
| 462.libquantum | lto | +8.77% | 4/7 | −1.51% | −46.24% |
| 462.libquantum | best_pgo | +7.22% | 5/7 | −43.27% | +88.23% |
| 462.libquantum | o3_tbaa | +6.01% | 5/7 | −40.13% | +107.47% |
| 456.hmmer | lto | **−6.61%** | 1/7 | −0.07% | −52.75% |
| 456.hmmer | lto_native | −6.34% | 0/7 | n/a | −52.04% |

bzip2 與 gobmk 的所有優化變體（不含 baseline／full）都在 −3.1% ～ +3.8% 之間，與噪音無法區分（完整表見 summary.tsv）。

### skill 推薦的 LTO 本身

| 工作量 | lto 速度 | 較快對數 | 指令數 |
|---|---:|:-:|---:|
| 401.bzip2 | +0.31% | 4/7 | −2.38% |
| 403.gcc | −2.53% | 1/7 | −0.64% |
| 445.gobmk | −0.37% | 4/7 | −1.67% |
| 456.hmmer | −6.61% | 1/7 | −0.07% |
| 462.libquantum | +8.77% | 4/7 | −1.51% |

原因：母研究已經先用 `llvm-link` 把整個程式合併成一份 raw.bc，`default<O3>` 本來就能跨檔 inline。LTO 剩下的主要差異是 `internalize` + 全域 DCE，讓 `.text` 縮小 4.7%～52.8%，但指令數只少 0%～2.4%。這個 repo 的方法已經吃掉了 skill 所說「LTO 的好處」。

### 母研究的 `full` pipeline 與 `o3` 的差距

`full`（母研究自訂的 8-pass pipeline）在 hmmer 慢 68.4%、libquantum 慢 14.8%、gobmk 慢 10.5%（三者 0～1/7 較快）。這不是本實驗要測的對象，但代表母研究的消融是在一條明顯弱於 O3 的 pipeline 上做的；某個 pass 在 `full` 中的效益，不一定能推到 `default<O3>`。

## 分析：瓶頸在哪裡、為什麼這些優化有效

### 熱點（callgrind，`o3`）

| 工作量 | 前幾名熱點 |
|---|---|
| 401.bzip2 | mainGtU 43.0%、fallbackSort 40.4%、BZ2_blockSort 7.1% |
| 403.gcc | **libc `memset` 31.7%**，其餘分散（cselib_invalidate_mem 2.9%、mark_set_1 2.8%…） |
| 445.gobmk | 分散：do_play_move 7.7%、do_dfa_matchpat 7.3%、order_moves 5.9%… |
| 456.hmmer | **P7Viterbi 95.5%** |
| 462.libquantum | test_sum 23.6%、quantum_sigma_x 17.6%、quantum_cnot 15.8%、muxfa 15.1%、muxfa_inv 15.0% |

hmmer 只有一個熱點，對單一迴圈的改進會直接反映在總時間；gobmk 的熱點分散，在單一處下手效益有限；gcc 有三成時間在 libc 的 `memset`，編譯器 pass 碰不到這部分。

### Remarks 指出的兩個瓶頸

**1. 熱點函式裡的 load 因 alias 無法消除。** 在 `o3` 的熱點函式中，數量最多的 missed remark 都是 GVN `LoadClobbered` 和 LICM `LoadWithLoopInvariantAddressInvalidated`，例如 gcc `cse_insn` 7124 次、gobmk `do_play_move` 1325 次、bzip2 `BZ2_blockSort` 944 次、hmmer `P7Viterbi` 236 次。原因是母研究的前端用 `-fno-strict-aliasing`，LLVM 拿不到型別 alias 資訊（TBAA）。改用 `-fstrict-aliasing` 後：

| 工作量 | LICM 成功 hoist（o3 → o3_tbaa） | 向量化迴圈 | 指令數 |
|---|---|---|---:|
| 401.bzip2 | 692 → 937 | — | +0.06% |
| 456.hmmer | 2905 → 3236 | — | −0.09% |
| 462.libquantum | 497 → 538 | **7 → 74** | **−40.13%** |

libquantum 的 `quantum_sigma_x` 從 19.7 億降到 4.2 億指令（−79%）。但時間只 +6.0%（5/7）：這幾個函式掃過整個量子態陣列，瓶頸主要在記憶體頻寬，指令減少很難轉成等比例的加速。

> TBAA 改變了前端語意：程式若違反 C 的 strict aliasing 規則，結果可能出錯。這 5 項在這組輸入下輸出全部正確，但 SPEC 官方對部分程式（例如 gcc、perlbench）建議 `-fno-strict-aliasing`，用到其他輸入或其他 benchmark 前要重新驗證。

**2. hmmer 的熱迴圈沒有向量化。** `P7Viterbi` 的主迴圈 remark 是 `UnsafeDep: Backward loop carried data dependence`，並建議 `#pragma clang loop distribute(enable)`。這正是 skill「Vectorization Hints」一節的方法，只是我們不改原始碼，改用 `-enable-loop-distribute` 全域開啟。開啟後，remark 出現 `Distribute: distributed loop`，向量化的迴圈從 1 個變成 2 個（VF=8, IC=4）：迴圈被拆成「有真正相依的部分」（維持純量）和「可向量化的部分」。結果 P7Viterbi 從 161 億降到 117 億指令，時間快 24.2%。其他 4 項開啟後產生的執行檔與 `o3` 逐位元組相同，代表 loop distribution 在那幾個程式中找不到可拆的迴圈。

### PGO

PGO 一律用和計時**不同**的輸入訓練（例如 gcc 用 test 的 cccp.in、計時用 train 的 integrate.in；gobmk 用 arend.tst、計時用 arb.tst）。gcc 指令數 −10.6%、gobmk −14.0%，但 gobmk 時間沒有穩定變快（+2.2%，5/7）；bzip2 指令數反而 +5.4%。PGO 與 loop distribution 疊加在 hmmer 上效果最大（+49.1%）。

### AVX-512（`*_native`）

把 IR 的 `target-cpu` 改成 sapphirerapids，沒有一項有確定的收益，hmmer 的組合版反而少了 11 個百分點。可能原因包括 AVX-512 降頻，以及向量化成本模型在這幾個整數密集程式上選了較差的寬度。valgrind 不支援 AVX-512，這些變體沒有指令數資料。

## 對 skill 的評估

| skill 的內容 | 在本實驗的效果 |
|---|---|
| `-O1/-O2/-O3` 等最佳化等級 | 母研究已使用 `default<O3>` 作為對照，沒有新資訊 |
| LTO（`-flto`） | 對已合併 bitcode 幾乎無效，hmmer 穩定變慢 6.6% |
| Optimization remarks（`-Rpass-missed` 等） | **最有價值**：直接指向 alias 與迴圈相依兩個瓶頸 |
| `#pragma clang loop vectorize/distribute` 等提示 | 以 opt 旗標實作 loop distribution，hmmer +24% |
| `-stats`、`-debug-pass-manager` | 有用但不是關鍵 |
| 寫自訂 pass、強度折減範例、Alive2 | 與效能調校無直接關係，沒有使用 |
| 沒有提到的：PGO、strict aliasing/TBAA、熱點 profiling | 本實驗的另外兩個主要收益來源 |

總結來說，這個 skill 適合用來入門「LLVM 有哪些最佳化、怎麼觀察 pass 做了什麼」。若直接把它當成調校清單，在這個 repo（已整體合併 IR、已有 O3 對照）上幾乎沒有收益。有效的流程是：**先 profiling 找熱點 → 讀熱點函式的 missed remarks → 依原因選擇對策**（alias 問題 → TBAA 或 `restrict`；迴圈相依 → distribution；分支多 → PGO）。

## 限制

- 只測 5 項純 C 程式；Fortran／C++ 的 8 項沒有涵蓋。
- LLVM 18 與母研究的 14/19 不同，雲端機與母研究的 i7-14700K 也不同，數值不能跨研究比較。
- 每個變體 7 對配對計時，雲端噪音大；比 ±5% 小的差異無法判斷。
- PGO 的訓練輸入雖與計時輸入不同，但屬於同一程式、同一類工作，對其他輸入的效果未知。
- 輸出比對是對獨立 GCC 版本的 differential test，不是官方 SPEC 驗證。
