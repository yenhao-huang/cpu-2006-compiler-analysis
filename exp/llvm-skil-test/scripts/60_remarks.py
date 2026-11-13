#!/usr/bin/env python3
"""Summarise opt remarks (the skill's `-Rpass` / `-Rpass-missed` analysis) per variant.

Reads logs/<bench>/<variant>.remarks.yaml (written by 20_build_variants.sh with
-pass-remarks-output) and, if callgrind hot lists exist, restricts a second
table to the hottest functions so the missed optimisations that matter stand out.
Outputs results/remarks-summary.tsv and results/remarks-hot.tsv.
"""
import collections, glob, os, re, sys

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIND = re.compile(r'^--- !(Passed|Missed|Analysis|Failure)')
FIELD = re.compile(r'^(Pass|Name|Function):\s+(.*)$')
PASSES = ('loop-vectorize', 'slp-vectorizer', 'inline', 'loop-unroll', 'licm', 'gvn')


def remarks(path):
    kind = rec = None
    with open(path, errors='replace') as f:
        for line in f:
            m = KIND.match(line)
            if m:
                if rec: yield kind, rec
                kind, rec = m.group(1), {}
                continue
            m = FIELD.match(line)
            if m and rec is not None and m.group(1) not in rec:
                rec[m.group(1)] = m.group(2).strip().strip("'\"")
    if rec: yield kind, rec


def hot_functions(bench, n=10):
    p = os.path.join(EXP, 'results', 'callgrind', f'{bench}.o3.hot.txt')
    if not os.path.exists(p):
        return []
    out = []
    for line in open(p):
        m = re.search(r'[\d,]+\s+\([^)]*\)\s+\S*?:(\S+)', line)
        if m:
            out.append(m.group(1))
    return out[:n]


def main():
    summary = collections.Counter()
    hot_rows = []
    for path in sorted(glob.glob(os.path.join(EXP, 'logs', '*', '*.remarks.yaml'))):
        bench = os.path.basename(os.path.dirname(path))
        variant = os.path.basename(path).replace('.remarks.yaml', '')
        hot = set(hot_functions(bench)) if variant in ('o3', 'lto') else set()
        per_hot = collections.defaultdict(collections.Counter)
        for kind, r in remarks(path):
            p = r.get('Pass', '')
            if p not in PASSES or kind not in ('Passed', 'Missed'):
                continue
            summary[(bench, variant, p, kind)] += 1
            fn = r.get('Function', '')
            if fn in hot:
                per_hot[fn][(p, kind, r.get('Name', ''))] += 1
        for fn, c in per_hot.items():
            for (p, kind, name), n in sorted(c.items()):
                hot_rows.append((bench, variant, fn, p, kind, name, n))
    with open(os.path.join(EXP, 'results', 'remarks-summary.tsv'), 'w') as f:
        f.write('benchmark\tvariant\tpass\tpassed\tmissed\n')
        keys = sorted({k[:3] for k in summary})
        for b, v, p in keys:
            f.write(f'{b}\t{v}\t{p}\t{summary[(b, v, p, "Passed")]}\t{summary[(b, v, p, "Missed")]}\n')
    with open(os.path.join(EXP, 'results', 'remarks-hot.tsv'), 'w') as f:
        f.write('benchmark\tvariant\tfunction\tpass\tkind\tremark\tcount\n')
        for row in hot_rows:
            f.write('\t'.join(map(str, row)) + '\n')
    print(f'{len(summary)} summary cells, {len(hot_rows)} hot-function remark rows')


if __name__ == '__main__':
    sys.exit(main())
