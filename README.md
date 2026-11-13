# cpu-2006-compiler-analysis

本目錄保存指定 CPU2006 可再散布來源、LLVM transform-pass 消融實驗與原始證據。

- [實驗結果與分析](docs/Result.md)
- [僅使用外部工具的完整重現命令](docs/Reproduce.md)
- [12 組 LLVM pass pipeline](configs/pipelines.tsv)
- [工作狀態](docs/STATE.md)

來源 clone 位於 `spec-cpu2006-redist/`，保持乾淨；相容性修改只在工作副本。LLVM14／LLVM19 工具局部解壓於 `external/toolchain/` 與 `external/toolchain19/`；bitcode／執行檔在 `data/`；原始計時在 `results/expansion/timing/`，最終摘要在 `results/all-tasks/`；診斷與 pass 紀錄在 `logs/`。

已完成 repo 全部 13 個編號目錄、156 個執行檔、1716 個有效計時樣本，包含原始程式與附帶元件；八項單獨消融、雙 vectorizer 消融、baseline 與 O3 對照。詳見 results/expansion/coverage.tsv。不宣稱完整 SPEC CPU2006 分數。

## 從 GitHub 取得

```bash
git clone --recurse-submodules https://github.com/yenhao-huang/cpu-2006-compiler-analysis.git
cd cpu-2006-compiler-analysis
```

來源 submodule 固定於實驗 commit `39effd74541743ddc74d7b27cbbb315790c56d12`。

Git 保存報告、CMake／pipeline／工作量配置、原始計時 JSON 與順序、分析表、正確性摘要、雜湊及精簡環境／驗證紀錄。`data/`、`external/`、大型 compiler trace、Xalan XML 與 WRF NetCDF 驗證產物保留在原實驗主機，不包含在 clone；大型驗證輸出的雜湊另存於 `results/all-tasks/local-correctness-payloads.sha256`。

重現文件保留原實驗的絕對路徑；在其他位置執行時，先將研究根目錄替換成自己的 clone 路徑，並依建置章節取得工具與產生資料。配置 TSV 內的絕對路徑也需替換。`sha256sum -c` 對本機產物的檢查須在重建相應產物後執行；原機的工具套件雜湊作為版本證據，套件本體不隨 Git 發布。
