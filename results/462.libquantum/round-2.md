| Command | Mean [ms] | Min [ms] | Max [ms] | Relative |
|:---|---:|---:|---:|---:|
| `taskset -c 2 data/462.libquantum/no_dce 143 25` | 536.4 ± 6.0 | 529.5 | 540.2 | 1.10 ± 0.02 |
| `taskset -c 2 data/462.libquantum/no_mem2reg 143 25` | 555.7 ± 18.2 | 544.3 | 576.7 | 1.14 ± 0.04 |
| `taskset -c 2 data/462.libquantum/no_loop_vectorize 143 25` | 543.4 ± 20.6 | 531.3 | 567.1 | 1.11 ± 0.04 |
| `taskset -c 2 data/462.libquantum/no_slp 143 25` | 531.7 ± 11.3 | 518.6 | 538.3 | 1.09 ± 0.02 |
| `taskset -c 2 data/462.libquantum/no_unroll 143 25` | 565.6 ± 10.8 | 553.1 | 572.5 | 1.16 ± 0.02 |
| `taskset -c 2 data/462.libquantum/baseline 143 25` | 1316.7 ± 14.2 | 1306.2 | 1332.8 | 2.69 ± 0.04 |
| `taskset -c 2 data/462.libquantum/no_simplifycfg 143 25` | 562.6 ± 9.7 | 553.8 | 573.1 | 1.15 ± 0.02 |
| `taskset -c 2 data/462.libquantum/full 143 25` | 568.6 ± 20.2 | 548.6 | 589.1 | 1.16 ± 0.04 |
| `taskset -c 2 data/462.libquantum/o3 143 25` | 488.7 ± 4.1 | 484.2 | 492.3 | 1.00 |
| `taskset -c 2 data/462.libquantum/no_inline 143 25` | 548.0 ± 19.7 | 533.1 | 570.3 | 1.12 ± 0.04 |
| `taskset -c 2 data/462.libquantum/no_vectors 143 25` | 566.1 ± 4.9 | 562.4 | 571.7 | 1.16 ± 0.01 |
| `taskset -c 2 data/462.libquantum/no_licm 143 25` | 581.3 ± 12.7 | 568.2 | 593.4 | 1.19 ± 0.03 |
