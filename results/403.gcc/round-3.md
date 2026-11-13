| Command | Mean [ms] | Min [ms] | Max [ms] | Relative |
|:---|---:|---:|---:|---:|
| `taskset -c 2 data/403.gcc/no_vectors spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 366.7 ± 16.2 | 357.2 | 385.4 | 1.07 ± 0.05 |
| `taskset -c 2 data/403.gcc/no_slp spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 343.6 ± 4.4 | 339.3 | 348.1 | 1.00 |
| `taskset -c 2 data/403.gcc/no_loop_vectorize spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 373.4 ± 27.6 | 347.8 | 402.6 | 1.09 ± 0.08 |
| `taskset -c 2 data/403.gcc/o3 spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 418.8 ± 16.4 | 401.1 | 433.5 | 1.22 ± 0.05 |
| `taskset -c 2 data/403.gcc/no_simplifycfg spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 459.1 ± 13.6 | 444.5 | 471.6 | 1.34 ± 0.04 |
| `taskset -c 2 data/403.gcc/no_inline spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 464.1 ± 25.2 | 438.1 | 488.4 | 1.35 ± 0.08 |
| `taskset -c 2 data/403.gcc/baseline spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 635.1 ± 25.2 | 613.6 | 662.8 | 1.85 ± 0.08 |
| `taskset -c 2 data/403.gcc/no_dce spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 446.1 ± 22.4 | 430.3 | 471.8 | 1.30 ± 0.07 |
| `taskset -c 2 data/403.gcc/full spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 443.2 ± 19.7 | 421.4 | 459.8 | 1.29 ± 0.06 |
| `taskset -c 2 data/403.gcc/no_licm spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 444.8 ± 4.1 | 440.4 | 448.5 | 1.29 ± 0.02 |
| `taskset -c 2 data/403.gcc/no_mem2reg spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 548.9 ± 5.4 | 542.9 | 553.5 | 1.60 ± 0.03 |
| `taskset -c 2 data/403.gcc/no_unroll spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 457.3 ± 12.3 | 450.1 | 471.6 | 1.33 ± 0.04 |
