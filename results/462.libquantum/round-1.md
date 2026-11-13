| Command | Mean [ms] | Min [ms] | Max [ms] | Relative |
|:---|---:|---:|---:|---:|
| `taskset -c 2 data/462.libquantum/full 143 25` | 830.0 ± 17.0 | 811.0 | 843.7 | 1.67 ± 0.20 |
| `taskset -c 2 data/462.libquantum/no_vectors 143 25` | 585.5 ± 88.3 | 530.6 | 687.4 | 1.18 ± 0.23 |
| `taskset -c 2 data/462.libquantum/no_loop_vectorize 143 25` | 512.4 ± 11.9 | 499.9 | 523.5 | 1.03 ± 0.13 |
| `taskset -c 2 data/462.libquantum/no_inline 143 25` | 514.7 ± 6.3 | 510.1 | 521.9 | 1.03 ± 0.13 |
| `taskset -c 2 data/462.libquantum/no_unroll 143 25` | 528.7 ± 14.7 | 511.7 | 537.2 | 1.06 ± 0.13 |
| `taskset -c 2 data/462.libquantum/no_dce 143 25` | 518.6 ± 22.4 | 498.0 | 542.5 | 1.04 ± 0.13 |
| `taskset -c 2 data/462.libquantum/no_mem2reg 143 25` | 534.9 ± 24.6 | 506.8 | 552.1 | 1.07 ± 0.14 |
| `taskset -c 2 data/462.libquantum/no_simplifycfg 143 25` | 655.5 ± 115.6 | 522.5 | 731.6 | 1.32 ± 0.28 |
| `taskset -c 2 data/462.libquantum/o3 143 25` | 498.0 ± 60.1 | 441.0 | 560.8 | 1.00 |
| `taskset -c 2 data/462.libquantum/no_licm 143 25` | 646.1 ± 32.0 | 620.0 | 681.7 | 1.30 ± 0.17 |
| `taskset -c 2 data/462.libquantum/no_slp 143 25` | 598.9 ± 38.3 | 555.9 | 629.5 | 1.20 ± 0.16 |
| `taskset -c 2 data/462.libquantum/baseline 143 25` | 1405.5 ± 50.2 | 1349.0 | 1444.9 | 2.82 ± 0.36 |
