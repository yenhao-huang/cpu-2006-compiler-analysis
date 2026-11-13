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

**最有用的是 mem2reg**：13 項中有 10 項加速超過 5%。其次依程式類型而定：C++ 物件導向程式靠 Inlining，數值／Fortran 程式靠 Loop vectorizer 與 LICM。

| 排名 | Pass | 13 項幾何平均 | >+5% 項數 | 代表案例 |
|---:|---|---:|---:|---|
| 1 | mem2reg | +19.5% | 10 | bzip2 +56.7%、HMMER +47.5%、Gromacs +43.8% |
| 2 | Inlining | +10.9%（不含 Xalan +2.8%） | 4 | Xalan +176.1%；HMMER −3.9% |
| 3 | Loop vectorizer | +4.6% | 2 | WRF +71.3%、HMMER +11.1% |
| 4 | LICM | +3.8% | 3 | WRF +38.6% |
| 5 | SimplifyCFG | +2.4% | 1 | HMMER +13.8% |
| 6 | Loop unrolling | ≈0% | 0 | 程式碼變大，速度改善不穩定 |
| 7 | SLP vectorizer | ≈0% | 1 | Sphinx +8.9%；SPOOLES −11.3% |
| 8 | DCE | ≈0% | 0 | 8 項消融後 ELF 完全相同 |

- 正值表示加入該 pass 後較快；數值為移除該 pass 的損失，含對後續 pass 的連帶影響（例如沒有 mem2reg，LICM 與 vectorizer 難以發揮）。
- 幾何平均僅供粗略排序；各程式輸入尺度不同，報告本身不合成總分。
- 相同 ELF 控制組單對誤差可達 ±10%，1%～5% 的差異不足以下結論。
- 結論限於本研究的精簡 pipeline；標準 O3 在 HMMER 上約快 3 倍。

完整數值與限制見 [結果報告](docs/Result.md)。這是 repo 內程式的實驗，不是官方 SPEC 分數；`454.calculix` 評測其提供的 SPOOLES 元件。

## 取得與重現

```bash
git clone --recurse-submodules https://github.com/yenhao-huang/cpu-2006-compiler-analysis.git
cd cpu-2006-compiler-analysis
```

- [詳細流程與命令範例](docs/Workflow.md)
- [完整重現說明](docs/Reproduce.md)
- [原始計時資料](results/expansion/timing)／[分析摘要](results/all-tasks)

`data/` 與工具鏈在本機建置產生，不隨 repo 上傳；既有計時資料可直接重新分析。
