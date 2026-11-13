# Research run state

Task: CPU2006 transform-pass ablation. User explicitly requested this local directory and clone, and external-tool-only reproduction.
Repository: spec-cpu2006-redist, commit 39effd74541743ddc74d7b27cbbb315790c56d12.
Research root is a new local directory, not a repository; benchmark checkout is unmodified.
Issue/worktree/PR: skipped. No user-owned publication repository or issue was specified; do not create an unrelated upstream issue for a local study. Explicit requested directory is retained.
OpenSpec: unavailable (`command -v openspec` returned no path); no claim of OpenSpec execution or validation. This file tracks the prerequisite and local authorized work.

| Stage | Status | Evidence |
| --- | --- | --- |
| Clone and tools | completed | repo HEAD; logs/toolchain-packages.sha256 |
| Design | completed | configs/pipelines.tsv; docs/Reproduce.md |
| Build | completed | 36 binaries; data/*/raw.bc; logs/*frontend.log |
| Correctness | completed | results/correctness.txt; results/pass-audit.txt |
| Measurement | completed | 324 original + 330 paired + 10 identical-gcc-control samples; all exit codes 0 |
| Analysis/report | completed | docs/Result.md; docs/Reproduce.md; logs/final-validation.txt |

Decisions: measure three available CPU2006 integer benchmarks with official train inputs; distinguish subset study from licensed full SPEC scores. Frontend O3 with -disable-llvm-passes avoids O1 unroll-disable metadata. All variants share raw bitcode, ISA, backend, linker and workload. No custom compiler, LLVM plugin, benchmark runner, or analysis program is required.

Build notes: GCC 12 variants compiled and differential-output checks passed. libquantum 12 variants passed. gobmk frontend now preserves source subdirectories (67 .c -> 67 .bc); engine/influence.c and patterns/influence.c must not overwrite each other. docs/Reproduce.md contains the corrected commands. No failed/incomplete probe is part of the timing dataset.

2026-10-25 00:13:30 Asia/Taipei: all 36 binaries pass differential output comparison; 24 named-pass absence checks pass; paired-vector absence also checked. Formal timing running as three randomized blocks. First gcc block has CV up to 18%; mpstat diagnostic shows host-wide background activity, CPU 2's sibling is comparatively idle (~80.6%), no cgroup CPU quota or throttling. Retain fixed CPU 2 instead of switching to a busier core; report uncertainty and identical-ELF negative control.

2026-10-25 00:24:29 Asia/Taipei: original 3 blocks complete (324 samples). At 00:24:33 began 165 adjacent full/variant pairs (5 per non-full configuration) because byte-identical libquantum full/no_dce showed severe unpaired bias. Primary conclusions will use paired geometric-mean ratios, with the original dataset retained and no observations removed.

2026-10-25 00:38:29 Asia/Taipei: final validation passed. All 664 valid timing observations are retained; 36 binaries pass differential output comparison; 24 individual-pass and 3 double-vectorizer audits pass; all input/toolchain/binary hashes match; benchmark checkout is clean. Reproduce Markdown Bash blocks pass `bash -n`, its pipeline block matches configs/pipelines.tsv, and file whitespace checks passed. Main result: mem2reg paired speedup +21.09% gcc and +24.17% gobmk; other small effects are uncertain under measured host noise. No unfinished implementation or measurement work remains for this documented three-workload CPU2006 subset.

## Expanded scope (completed; chronological notes below)

The user subsequently requested all numbered tasks in this repository. The three-workload report above is archived in docs/phase1; it is NOT completion of the expanded scope. There are 13 unique benchmark directories. Official SPEC input is not required by the user: use supplied upstream examples, upstream deterministic data generators, and actual code in each directory. Do not silently omit directories or claim a component is a full application.

New work: 401.bzip2 and 456.hmmer have all 12 binaries. 400.perlbench, 435.gromacs, 482.sphinx3, 436.cactusADM, and 454.calculix have raw bitcode and variant builds in progress. Tonto's complete Fortran source compiled with Flang 19 via configs/tonto/CMakeLists.txt; O3 link in progress. WRF compilation and Xerces/Xalan legacy build compatibility are in progress. Expansion measurements have not yet started. All original clone source remains untouched; Gromacs fmax naming patch is only in the working copy.

454.calculix contains SPOOLES 2.2, not the CalculiX application. Its supplied FrontMtx/drivers/testGrid generates a known sparse linear system and reports solution error. Initial 12x12x12 probe residual = 2.6522e-11, success status is 1 by the upstream driver's convention. Report this as the supplied component evaluation.

Flang 19.1.7 and matching LLVM/Clang were downloaded and extracted locally under external/toolchain19. C workloads use LLVM 14.0.6, mixed/Fortran workloads use LLVM 19.1.7. Do not aggregate these as one compiler version. All experiments use configs/pipelines.tsv; backend remains llc -O=2.

2026-10-25 02:18 UTC: new seven workloads all have 12 configurations passing correctness (Perl 947 TAP, bzip supplied 6 cases, Gromacs coordinates, Cactus wave files, SPOOLES residual, HMMER calibration, Sphinx transcripts/scores). Tonto valid H2O SCF and WRF valid 60-step hill-flow now run. WRF needs unlimited stack; failed default-stack probe is excluded. Tonto/WRF full ablation build is ongoing, Xalan C++ portability build ongoing. No expansion timing dataset yet. See Expansion-Reproduce.md for concrete commands, LLVM19 InstCombine max-iterations adjustment and input details.

2026-10-25 02:27 UTC: Tonto and WRF all 12 configurations validated. WRF complete NetCDF fields and step diagnostics equal. 81 new pass-absence audits passed (9 workloads × (8 single + dual-vector)). Xalan native and first variants produce exactly the expected transformed XML; remaining variants still building. Formal expansion timing commands now recorded in Expansion-Reproduce.md, expected 1320 new samples, not yet run. Input/toolchain/raw bitcode hashes saved. Xalan's only noinline function is the generated __clang_call_terminate helper, retained intentionally.

2026-10-25 02:34 UTC: all 120 expansion binaries (156 including phase1) built and validated. All 90 expansion pass-absence checks passed (117 including phase1). Xalan final workload uses 5000 supplied bird-record blocks, 45,855,056 input bytes and 53,615,062 oracle output bytes; all 12 outputs exact. Sphinx final ctl repeats the supplied audio 20 times in one process; all transcripts/scores validated. No build jobs remain. Starting serial hyperfine measurement using configs/expansion-workloads.tsv; expected 1320 new valid samples.

Measurement decision: after the ten expansion workloads finish, remeasure the original three workloads with the same five-pair plus identical-ELF-control protocol (configs/recheck-workloads.tsv). The first-phase gcc identical-ELF control had a -29.48% outlier; the broader scope and old noise make a contemporaneous recheck justified. Do not run these concurrently with expansion timing. The final main table will use fresh results for all 13; old 664 samples remain archived. Revised fresh-sample target = 13×132 = 1716, with 156 unchanged canonical binaries. The ten-workload job/config in progress is not modified.

2026-10-25 02:56 UTC: formal expansion job is still running, tool PTY session 40136. Rounds 1–4 complete for all ten new tasks; round 5 has begun. Snapshot 1113 successful timing samples, no nonzero exit codes. JSON is rewritten after each command, so an in-progress pair may currently contain only one result; final validation must require all 60 pair JSONs per benchmark to contain exactly two results. Do not analyze incomplete pairs as final. Next: wait for session 40136 to finish; execute the documented recheck loop for the original three tasks SEQUENTIALLY, then aggregate all 13 into results/all-tasks and rewrite final Result/Reproduce. New total target 1716 fresh samples; old 664 remain archived. No additional build/correctness work is pending.

2026-10-25 03:00 UTC: ten-task expansion measurement completed successfully (PTY 40136 exited 0). Sequential recheck of gcc/gobmk/libquantum started; no benchmark jobs overlap. Combined config list is configs/all-workloads.tsv. Once recheck ends, validate 793 JSON files, 1716 times, all exit codes 0, 60 pairs with 2 results per benchmark and 12-result initial file. Use only fresh results/expansion/timing in final main table; historical 664 samples remain archived.

2026-10-25 03:19 UTC — EXPANDED GOAL COMPLETE. All 13 repository task directories evaluated with 12 configurations each: 156 canonical binaries, correctness checks passed, 117 single/dual pass-absence audits. Fresh timing stage completed: 793 JSON files, 1716 valid observations, all exits 0. Final reports are docs/Result.md and docs/Reproduce.md, with detailed external-tool build/validation/timing commands in docs/Expansion-Reproduce.md. Primary paired estimates, code sizes, ELF identity, hashes and combined audit are in results/all-tasks. All 156 binary hashes match, source clone is clean, all task names match the repository inventory, and reproduction Bash blocks pass syntax validation. Full validation log: logs/all-tasks-final-validation.txt. Historical 664 observations remain archived and are not mixed into final estimates. SPOOLES is explicitly a supplied component; Cactus short-duration uncertainty and same-ELF controls are reported. No pending benchmark, build, analysis, or documentation work.
