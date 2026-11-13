| Command | Mean [ms] | Min [ms] | Max [ms] | Relative |
|:---|---:|---:|---:|---:|
| `taskset -c 2 data/403.gcc/no_simplifycfg spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 384.1 ± 12.1 | 372.1 | 396.3 | 1.06 ± 0.12 |
| `taskset -c 2 data/403.gcc/no_unroll spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 398.3 ± 26.8 | 367.7 | 417.5 | 1.10 ± 0.14 |
| `taskset -c 2 data/403.gcc/no_dce spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 430.1 ± 53.3 | 371.0 | 474.3 | 1.19 ± 0.20 |
| `taskset -c 2 data/403.gcc/baseline spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 556.7 ± 41.4 | 524.1 | 603.3 | 1.54 ± 0.20 |
| `taskset -c 2 data/403.gcc/no_loop_vectorize spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 442.4 ± 6.9 | 435.0 | 448.8 | 1.22 ± 0.13 |
| `taskset -c 2 data/403.gcc/no_vectors spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 421.5 ± 76.1 | 347.0 | 499.0 | 1.16 ± 0.24 |
| `taskset -c 2 data/403.gcc/o3 spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 362.3 ± 39.1 | 319.6 | 396.5 | 1.00 |
| `taskset -c 2 data/403.gcc/no_mem2reg spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 509.5 ± 57.4 | 448.4 | 562.3 | 1.41 ± 0.22 |
| `taskset -c 2 data/403.gcc/no_inline spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 404.1 ± 32.3 | 382.4 | 441.2 | 1.12 ± 0.15 |
| `taskset -c 2 data/403.gcc/no_slp spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 388.6 ± 18.2 | 374.2 | 409.1 | 1.07 ± 0.13 |
| `taskset -c 2 data/403.gcc/no_licm spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 387.3 ± 8.7 | 377.8 | 395.0 | 1.07 ± 0.12 |
| `taskset -c 2 data/403.gcc/full spec-cpu2006-redist/modified/403.gcc/data/train/input/integrate.in -o /dev/null` | 384.0 ± 10.7 | 373.4 | 394.8 | 1.06 ± 0.12 |
