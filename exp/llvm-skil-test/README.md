# llvm-optimization skill 對 CPU2006 13 項的測試、效能分析與優化

用 [`gmh5225/awesome-llvm-security`](https://github.com/gmh5225/awesome-llvm-security)（commit `b7609b4`）的
`.claude/skills/llvm-optimization` skill 指導最佳化，對本 repo 已建置的 13 個 CPU2006 工作量做三階段實驗：
**skill 建議的設定 → 依分析調整 knob → 獨立重測確認**。所有變體從原研究同一份 `raw.bc` 出發，後端固定 `llc -O=2`。

## 結論

| 指標（13 項幾何平均，獨立確認階段 12 對） | 速度變化 |
|---|---:|
| `default<O3>` 相對原研究 `full` pipeline | **+19.95%** |
| 統一建議 `lto_inl`（LTO + 本機 ISA + inline 500）相對 O3 | **+2.12%** |
| 逐項調校 `tuned` 相對 O3 | **+3.29%** |
| 逐項調校 `tuned` 相對原研究 `full` | **+23.89%** |

速度變化 = `100 × (1 / geomean(T_variant / T_ref) − 1)`，正值代表較快。所有被採用的執行檔輸出與 `full` **逐位元組相同**（SPOOLES 為已知解殘差 ≤ 1e-8）。

確認階段相對 O3 明顯優於噪音的項目：

| 工作量 | tuned 設定 | 相對 O3（12 對 geomean，[min,max]） | 主要來源 |
|---|---|---:|---|
| 454.calculix (SPOOLES) | LTO + SLP 關閉 + inline 500 | **+13.88%** [+11.8, +16.2] | SLP 在此程式造成退步（與原消融結果一致） |
| 481.wrf | LTO + Alder Lake ISA（無 FMA）+ unroll 600 | **+10.47%** [+4.3, +16.4] | Flang IR 預設 x86-64（SSE2），改 AVX2 後向量化 |
| 400.perlbench | LTO + inline 500 + SLP 關閉 | **+7.82%** [+6.3, +10.5] | 更積極 inlining |
| 483.xalanc | LTO + inline 500 | **+3.64%** [+0.8, +5.6] | inlining（原研究中 Xalan 最重要的 pass） |
| 445.gobmk | LTO + inline 500 + unroll 600 | **+2.78%** [+1.3, +3.7] | inlining／unroll |
| 482.sphinx3 | O3 + 本機 ISA | **+1.92%** [+0.6, +3.1] | ISA 調整 |
| 401.bzip2 | 原研究 `full` pipeline | **+1.68%** [−1.9, +3.5] | 較多 LICM/loop-vectorize；O3 反而較慢 |

gcc（+0.88%）未明顯超出噪音；gromacs、cactusADM、hmmer、libquantum、tonto 沒有任何嚴格正確的變體勝過 O3，tuned 即為 O3 本身，這五組逐位元組相同的 tuned/o3 配對同時作為噪音控制，幾何平均落在 −0.29%～+0.63%。

## skill 如何轉成實驗

skill 內容是通用說明（最佳化等級、核心 pass、LTO、向量化提示、remarks、Alive2），沒有針對特定程式的指令。對應方式如下：

| skill 段落 | 實驗變體／分析 | 指令 |
|---|---|---|
| Optimization Levels | `o2`、`o3`、`os` | `opt -passes='default<O2|O3|Os>'` |
| Link-Time Optimization | `lto` | `opt -passes='lto-pre-link<O3>,internalize,lto<O3>' -internalize-public-api-list=main,_QQmain` |
| Vectorization（目標 ISA） | `o3_native`、`lto_native` | IR 的 `target-cpu` 改為 `alderlake`（i7-14700K 同 ISA；LLVM14 無 raptorlake） |
| Optimization Remarks | 各 pass Passed/Missed 計數 | `-pass-remarks-output` + `-pass-remarks-filter`，見 [remarks.tsv](results/remarks.tsv) |
| Inlining / Loop Unrolling / SLP | 第二階段 knob | `-inline-threshold=500`、`-unroll-threshold=600`、`-slp-threshold=1000`（實質關閉 SLP） |

`full` 與 `o3` 直接複製原研究已驗證的執行檔，作為對照。

## 方法

- **輸入與後端**：每項沿用 [configs/workloads.tsv](configs/workloads.tsv) 的固定工作量（與原研究相同；Cactus 重複 20 次、SPOOLES 重複 10 次以拉長到約 0.3–0.7 秒）。C/C++ 用 LLVM 14.0.6，Fortran/混合用 LLVM 19.1.7。
- **正確性**：[scripts/check.sh](scripts/check.sh) 以原研究的標準對每個變體與 `full` 做差分比對：Perl 947 TAP、bzip2 壓縮 hash 與還原、gcc 組語、Gromacs 終態座標、Cactus 32 個輸出檔、gobmk/HMMER/libquantum stdout、SPOOLES 殘差、Tonto 完整 stdout、WRF 60 步與整個 NetCDF、Sphinx 辨識結果、Xalan 對 oracle XML。結果見 [correctness.tsv](results/correctness.tsv)：149 MATCH、6 DIFF（見下）。
- **計時**：固定 CPU 2，1 輪暖機後，每輪將所有變體隨機排序各跑一次（[scripts/time.sh](scripts/time.sh)，順序存檔）；比值在同一輪內配對計算，取幾何平均與中位數。三階段共 **2434 個有效樣本**（770 + 1040 + 624），全部 exit 0。每項另放一個與 `full` 逐位元組相同的 `full_control`。
- **避免挑選偏誤**：第二階段只用來選設定，最終數字來自第三階段全新的 12 輪量測。

## 第一階段：skill 直接建議的設定

相對 O3（7 對 geomean，%）。`*` 為本機 ISA 但關閉 FMA 的版本（O3 / LTO）。

| 工作量 | full | o2 | os | o3_native | lto | lto_native | native* |
|---|---:|---:|---:|---:|---:|---:|---:|
| 400.perlbench | −4.9 | +1.9 | +1.7 | +3.0 | +5.4 | +6.0 | |
| 401.bzip2 | +2.0 | −0.5 | +0.3 | −0.3 | −0.4 | −1.6 | |
| 403.gcc | −6.8 | −1.0 | −0.8 | −0.9 | +0.5 | −0.4 | |
| 435.gromacs | −3.1 | −0.4 | −0.2 | +1.0 | +0.7 | −0.2 | |
| 436.cactusADM | −32.9 | −0.5 | −13.1 | −4.7 | −7.6 | +0.5 | −3.8 / −6.8 |
| 445.gobmk | −11.1 | −0.1 | −1.2 | +0.5 | +2.4 | +1.6 | |
| 454.calculix | −0.8 | +0.2 | −0.5 | −0.2 | +1.3 | +1.1 | |
| 456.hmmer | −67.7 | +3.3 | −2.0 | +2.0 | +0.6 | −2.1 | |
| 462.libquantum | −1.0 | (+16.6) | (+8.2) | (+16.3) | (+11.6) | (+10.8) | |
| 465.tonto | −18.0 | +1.1 | −1.6 | +3.6 | +0.5 | +2.9 | −0.5 / −3.0 |
| 481.wrf | +2.0 | +0.1 | +0.2 | +8.6 | −1.2 | +11.2 | +7.5 / +9.7 |
| 482.sphinx3 | −5.1 | +3.2 | +2.7 | +4.7 | +0.9 | +3.0 | |
| 483.xalanc | −14.7 | −2.8 | −9.3 | +0.0 | +1.7 | +0.8 | |

- libquantum 本階段 O3 有主機噪音尖峰（單次 943 ms vs 常態 ~390 ms），括號內數值不可信；第二、三階段 10–12 對中沒有變體勝過 O3。
- `-Os` 縮小 .text 4%～31%，速度多數與 O3 相近，但 Xalan −9.3%、Cactus −13.1%。
- 單純 LTO 對 Perl、gobmk 有利，對 Cactus 不利（−7.6%）。

### 本機 ISA 的正確性問題與修正

Flang 前端產生的 IR 是 `target-cpu="x86-64"`，且浮點運算帶 `contract` 旗標。改成 Alder Lake 後 LLVM 會融合成 FMA，**Cactus、Tonto、WRF 輸出不再逐位元組相同**（WRF em_t_2 差 1 個 float32 ULP；Tonto SCF energy 到 6 位小數相同，Kinetic Energy 差 1e-7 相對值）。這 6 個 DIFF 均為此原因。對這三項另建 `*_nofma`（`target-features="-fma"`），保留 AVX2 寬度但不融合，**恢復逐位元組相同**；WRF 仍得到約 +10%，Tonto 的增益則完全來自 FMA（+3.6% → −0.5%）。最終建議只採用無 FMA 版本。

## Remarks 分析（skill「Optimization Remarks」）

[remarks-passed.tsv](results/remarks-passed.tsv) 是 `full`、`o3`、`lto_native` 三種 pipeline 各 pass 的 Passed remark 數。重點：

- 原研究 `full` pipeline **沒有 GVN**（0 筆），O3 則有數千筆 GVN 消除（gcc 9725、Xalan 4860）。這與 O3 比 `full` 快 20% 的整體差距一致；HMMER 差距最大（`full` 慢 68%）。
- Tonto 的 loop-vectorize 成功數：O3 450 → lto_native 2208。SSE2 成本模型讓多數 Fortran 迴圈不值得向量化，換成 AVX2 後才通過。
- LTO 在每一項都比 O3 inline 更多（Xalan 60456 → 66719、gcc 20899 → 21554），並刪除未被呼叫的函式庫程式碼：SPOOLES .text −59%、HMMER −50%、libquantum −45%（[code-size-vs-o3.tsv](results/code-size-vs-o3.tsv)）。
- remark 計數是嘗試次數，不能一對一換算成速度，只用來指出要調整的 pass。

## 第二階段：依分析調整 knob

以嚴格正確的 LTO + 本機 ISA 為底（Fortran 用無 FMA），相對 O3（10 對 geomean，%）：

| 工作量 | o3_native | lto_native | lto_inl | lto_noslp | lto_unroll |
|---|---:|---:|---:|---:|---:|
| 400.perlbench | +3.1 | +3.9 | **+8.4** | +6.8 | +5.1 |
| 401.bzip2 | −0.9 | −0.6 | +0.2 | −1.2 | −0.7≡ |
| 403.gcc | +0.3 | −0.1 | **+2.2** | +0.5 | +0.9 |
| 435.gromacs | +1.1 | +0.6 | +0.3 | −3.1 | +0.7 |
| 436.cactusADM | −3.1 | −7.2 | −0.3 | −0.6 | −6.9 |
| 445.gobmk | +0.9 | +2.1 | **+3.2** | +2.2 | **+3.1** |
| 454.calculix | −0.1 | +1.2 | +1.8 | **+15.5** | +1.0≡ |
| 456.hmmer | +1.6 | +0.9 | +2.2 | +0.8 | +2.5≡ |
| 462.libquantum | −0.0 | −3.7 | −0.3 | −0.6 | −2.4≡ |
| 465.tonto | −0.3 | −1.7 | +0.8 | −1.6 | −1.5 |
| 481.wrf | +9.5 | +10.8 | +9.8 | +9.9 | **+11.3** |
| 482.sphinx3 | +2.2 | +2.1 | +1.6 | −4.7 | +1.5≡ |
| 483.xalanc | −0.5 | +0.7 | **+3.9** | +0.7 | +0.0 |

`≡`：`-unroll-threshold=600` 產生與 `lto_native` 完全相同的執行檔，兩欄差距即為噪音（約 ±1.5%）。13 項幾何平均：`lto_inl` +2.55%、`lto_noslp` +1.75%、`o3_native` +1.04%、`lto_native` +0.61%、`o2` +0.23%。

依此選定 [configs/tuned.tsv](configs/tuned.tsv)：只在變化明顯超過噪音時才離開 O3，並合併兩個各自有效的 knob（Perl、SPOOLES、gobmk）。

## 第三階段：獨立確認

全新 12 輪，變體 `full`、`o3`、`lto_inl`、`tuned`，結果見本文開頭。第二階段的增益都重現（SPOOLES +15.5 → +13.9、WRF +11.3 → +10.5、Perl +8.4 → +7.8、Xalan +3.9 → +3.6、gobmk +3.2 → +2.8），gcc 從 +2.2 降到 +0.9，不足以宣稱改善。

## 對 skill 的評估

**有用**：skill 列出的三個方向（最佳化等級、LTO、向量化／目標 ISA）加上 remarks，足以找出本實驗所有主要增益：O3 相對研究 pipeline 的 +20%、LTO + inline 的 +2～8%、WRF 的 ISA 問題、SPOOLES 的 SLP 退步。

**不足或與實際工具鏈不符**：

- Alive2 範例 `opt -instcombine input.ll` 在 LLVM 19 失敗（`The opt -passname syntax ... is not supported`），須改為 `-passes=instcombine`；LLVM 14 仍可用。
- `opt -stats` 在兩個 Debian release 工具鏈都沒有輸出（需啟用 statistics 的 LLVM 建置）。
- 沒有提到在 new pass manager 下如何關閉 `default<O3>` 內的 SLP：`-vectorize-slp=false` 實測無效，需用 `-slp-threshold`。
- 沒有提醒改變目標 ISA 會讓帶 `contract` 的 Fortran 程式產生 FMA，結果不再逐位元組相同。
- 沒有 PGO、ThinLTO 的實際流程；本實驗未測這兩項。
- 其餘大段內容（自訂 pass、dominator tree、Alive2）屬於開發 pass 用，對「調整既有程式效能」沒有直接作用。

## 限制

- 共用主機、未關 turbo；同檔控制顯示單對仍可能偏差 10% 以上，因此只採用配對幾何平均與多輪範圍，2% 以下的差異不作結論。
- 這是 repo 內程式與固定輸入的實驗，不是官方 SPEC 分數；SPOOLES 是 454.calculix 目錄提供的元件。
- 調整只在本機 i7-14700K 驗證；`alderlake` ISA 的執行檔不能在不支援 AVX2 的 CPU 執行。
- `tuned` 是在同一輸入上選出的設定，雖經獨立重測，換輸入或機器時仍需重新驗證。

## 簡報

[slides/llvm-skill-test.html](slides/llvm-skill-test.html)（單一檔案，字型已內嵌，可離線開啟）與 [PDF](slides/llvm-skill-test.pdf)，12 頁，以 frontend-slides skill 製作。所有數字由 [slides/build_deck.py](slides/build_deck.py) 從 `results/` 產生；渲染與 PDF 匯出用 [slides/render.mjs](slides/render.mjs)，驗證紀錄見 [slides/STATE.md](slides/STATE.md)。

```bash
# 需要含 fonttools、brotli 的 Python；Chromium 主機需 fontconfig（見 STATE.md）
VIEWPORT_CSS=<frontend-slides>/references/viewport-base.css python -I slides/build_deck.py
CHROME=<chrome-headless-shell> node slides/render.mjs slides/llvm-skill-test.html build/shots
```

## 重現

```bash
cd exp/llvm-skil-test
# 1. 建置（需先完成原研究 data/ 與 external/ 工具鏈）
for b in $(grep -v '^#' configs/benchmarks.tsv | cut -f1); do
  for v in full full_control o3 o2 os o3_native lto lto_native lto_inl lto_noslp lto_unroll; do echo "$b $v"; done
done | xargs -P 10 -L 1 scripts/build.sh
for b in 436.cactusADM 465.tonto 481.wrf; do
  scripts/build.sh $b o3_native_nofma; scripts/build.sh $b lto_native_nofma
done
scripts/build.sh 400.perlbench lto_inl_noslp; scripts/build.sh 454.calculix lto_inl_noslp
scripts/build.sh 445.gobmk lto_inl_unroll
grep -v '^#' configs/tuned.tsv | while IFS=$'\t' read -r b v _; do cp build/$b/$v build/$b/tuned; done
# 2. 正確性（同一 benchmark 的變體須依序執行）
scripts/check.sh 481.wrf full; scripts/check.sh 481.wrf tuned
# 3. remarks、計時（三階段均單工）、分析
scripts/remarks.sh 454.calculix
scripts/time-all.sh; scripts/time-stage2.sh; scripts/time-confirm.sh
scripts/analyze.sh timing; scripts/analyze.sh timing-stage2; scripts/analyze.sh timing-confirm
```

| 路徑 | 內容 |
|---|---|
| [configs/](configs) | benchmark 連結參數、變體定義、工作量、tuned 選擇與理由 |
| [scripts/](scripts) | 建置、正確性、remarks、計時、分析 |
| [results/timing*/](results) | 三階段原始 hyperfine JSON 與每輪順序 |
| [results/*-paired-summary.tsv](results) | 配對比值摘要（geomean、median、min、max） |
| [results/correctness.tsv](results/correctness.tsv) | 155 筆差分正確性結果 |
| [results/remarks*.tsv](results) | optimization remarks 計數 |
| [results/code-size*.tsv](results) | .text 大小 |

`build/` 與詳細 log 只保留在本機。
