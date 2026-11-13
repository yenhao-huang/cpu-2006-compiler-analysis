# cpu-2006-compiler-analysis

使用 [spec-cpu2006-redist](https://github.com/miyuki/spec-cpu2006-redist) 的 **13 個 benchmark**，比較不同 LLVM transform pass 對執行速度與程式碼大小的影響。

## 實驗流程

**SPEC 來源 → LLVM IR → Pass 消融 → 執行測試 → 效能分析**

1. **萃取來源與輸入**：從 repo 選出各 benchmark 的程式、附帶範例與固定參數。
2. **產生 LLVM IR**：用 Clang／Flang 編譯成 bitcode，透過 `llvm-link` 合併。
3. **建立消融版本**：從相同 IR 出發，每次移除一種 pass，再編譯成執行檔。
4. **驗證並計時**：確認輸出正確，在相同 CPU 與輸入下重複配對測量。
5. **分析差異**：比較執行時間、程式碼大小與量測噪音，判斷 pass 的效益。

評測的八種 pass：Inlining、Loop unrolling、Loop vectorizer、SLP vectorizer、mem2reg、LICM、DCE、SimplifyCFG。

## 結果

共完成 **156 個執行檔、1716 個有效計時樣本**。

| 工作量 | Pass | 速度變化 |
|---|---|---:|
| WRF | Loop vectorizer | +71.25% |
| Xalan | Inlining | +176.07% |
| SPOOLES | SLP vectorizer | −11.28% |

正值表示加入該 pass 後較快；效果依工作量而異，小幅差異須考慮噪音。完整數值與限制見 [結果報告](docs/Result.md)。這是 repo 內程式的實驗，不是官方 SPEC 分數；`454.calculix` 評測其提供的 SPOOLES 元件。

## 取得與重現

```bash
git clone --recurse-submodules https://github.com/yenhao-huang/cpu-2006-compiler-analysis.git
cd cpu-2006-compiler-analysis
```

- [詳細流程與命令範例](docs/Workflow.md)
- [完整重現說明](docs/Reproduce.md)
- [原始計時資料](results/expansion/timing)／[分析摘要](results/all-tasks)

`data/` 與工具鏈在本機建置產生，不隨 repo 上傳；既有計時資料可直接重新分析。
