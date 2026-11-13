| Command | Mean [ms] | Min [ms] | Max [ms] | Relative |
|:---|---:|---:|---:|---:|
| `taskset -c 2 data/462.libquantum/o3 143 25` | 484.3 ± 5.8 | 480.8 | 491.0 | 1.00 |
| `taskset -c 2 data/462.libquantum/no_dce 143 25` | 540.1 ± 5.4 | 534.8 | 545.5 | 1.12 ± 0.02 |
| `taskset -c 2 data/462.libquantum/no_simplifycfg 143 25` | 552.2 ± 5.8 | 547.3 | 558.6 | 1.14 ± 0.02 |
| `taskset -c 2 data/462.libquantum/baseline 143 25` | 1296.1 ± 16.1 | 1279.2 | 1311.2 | 2.68 ± 0.05 |
| `taskset -c 2 data/462.libquantum/no_slp 143 25` | 535.0 ± 1.9 | 533.2 | 537.0 | 1.10 ± 0.01 |
| `taskset -c 2 data/462.libquantum/no_vectors 143 25` | 560.3 ± 5.4 | 556.1 | 566.5 | 1.16 ± 0.02 |
| `taskset -c 2 data/462.libquantum/no_unroll 143 25` | 586.7 ± 57.1 | 535.7 | 648.4 | 1.21 ± 0.12 |
| `taskset -c 2 data/462.libquantum/full 143 25` | 739.2 ± 181.6 | 540.4 | 896.3 | 1.53 ± 0.38 |
| `taskset -c 2 data/462.libquantum/no_licm 143 25` | 574.4 ± 9.3 | 568.5 | 585.1 | 1.19 ± 0.02 |
| `taskset -c 2 data/462.libquantum/no_inline 143 25` | 543.7 ± 3.9 | 540.7 | 548.1 | 1.12 ± 0.02 |
| `taskset -c 2 data/462.libquantum/no_loop_vectorize 143 25` | 544.0 ± 2.1 | 542.7 | 546.4 | 1.12 ± 0.01 |
| `taskset -c 2 data/462.libquantum/no_mem2reg 143 25` | 552.0 ± 12.4 | 540.0 | 564.8 | 1.14 ± 0.03 |
