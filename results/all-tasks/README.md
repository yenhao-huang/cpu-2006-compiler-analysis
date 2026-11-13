# Combined 13-task evidence

The final timing table uses the fresh 13-task measurement stage in results/expansion/timing. The original three workloads are rechecked sequentially after the ten newly built workloads, because first-phase identical-binary controls showed substantial temporal noise. Each benchmark has its own adjacent full/variant pairs and identical-ELF control.

The earlier 664 samples remain unchanged in results/paired, results/null-control and the original results benchmark directories. They are historical evidence and are not mixed into the final paired estimates. Archived phase1 reports explain those observations.

Correctness: results/expansion/correctness for ten new tasks; results/correctness.txt for the original three. Compiler versions and actual workloads are in results/expansion/coverage.tsv. Combined code-size tables cover all 156 canonical executables.

Upstream/component workloads are labeled explicitly. These are reproducible program benchmarks, not official SPEC CPU2006 scores. Each paired ratio uses the full time from the same JSON file. Full/control pairs measure noise, not optimization effects.
