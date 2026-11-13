| Command | Mean [ms] | Min [ms] | Max [ms] | Relative |
|:---|---:|---:|---:|---:|
| `taskset -c 2 data/403.gcc/no_inline spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 399.1 ± 87.8 | 331.6 | 498.4 | 1.12 ± 0.27 |
| `taskset -c 2 data/403.gcc/no_licm spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 356.9 ± 33.2 | 318.7 | 378.7 | 1.00 |
| `taskset -c 2 data/403.gcc/o3 spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 406.6 ± 60.0 | 339.9 | 456.2 | 1.14 ± 0.20 |
| `taskset -c 2 data/403.gcc/no_dce spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 391.7 ± 43.4 | 347.6 | 434.4 | 1.10 ± 0.16 |
| `taskset -c 2 data/403.gcc/no_mem2reg spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 510.3 ± 49.3 | 465.8 | 563.3 | 1.43 ± 0.19 |
| `taskset -c 2 data/403.gcc/no_simplifycfg spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 453.6 ± 31.2 | 423.9 | 486.0 | 1.27 ± 0.15 |
| `taskset -c 2 data/403.gcc/no_slp spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 475.7 ± 6.9 | 468.3 | 482.0 | 1.33 ± 0.13 |
| `taskset -c 2 data/403.gcc/full spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 475.8 ± 52.1 | 445.5 | 536.0 | 1.33 ± 0.19 |
| `taskset -c 2 data/403.gcc/no_vectors spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 392.1 ± 37.4 | 367.3 | 435.1 | 1.10 ± 0.15 |
| `taskset -c 2 data/403.gcc/baseline spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 565.1 ± 43.6 | 516.7 | 601.4 | 1.58 ± 0.19 |
| `taskset -c 2 data/403.gcc/no_unroll spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 363.5 ± 12.3 | 355.5 | 377.7 | 1.02 ± 0.10 |
| `taskset -c 2 data/403.gcc/no_loop_vectorize spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 407.0 ± 45.3 | 379.7 | 459.3 | 1.14 ± 0.17 |
