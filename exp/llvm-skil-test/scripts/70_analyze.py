#!/usr/bin/env python3
"""Merge timing (hyperfine JSON), callgrind Ir and .text size into one table.

Speed change vs the reference (default o3), parent-study convention:
    speedup_pct = 100 * (1 / geomean(T_variant / T_ref) - 1)   (positive = faster than o3)
Each round's ratio uses the o3 run adjacent to it (paired design, 40_time.sh).
Also reports the o3-vs-o3 noise floor estimated from the spread of ratios.
Writes results/summary.tsv and results/paired-ratios.tsv.
"""
import collections, csv, glob, json, math, os, statistics as st

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(EXP, 'results')
REF = os.environ.get('REF', 'o3')


def geomean(xs):
    return math.exp(sum(map(math.log, xs)) / len(xs))


def read_tsv(name):
    p = os.path.join(RES, name)
    if not os.path.exists(p):
        return []
    with open(p) as f:
        return list(csv.DictReader(f, delimiter='\t'))


ratios = collections.defaultdict(list)
times = collections.defaultdict(list)
rows = []
for jf in sorted(glob.glob(os.path.join(RES, 'timing', '*', '*.json'))):
    bench = os.path.basename(os.path.dirname(jf))
    rnd, var = os.path.basename(jf)[:-5].split('-', 1)
    res = {r['parameters']['variant']: r['times'][0] for r in json.load(open(jf))['results']}
    if REF not in res or var not in res:
        continue
    ratios[(bench, var)].append(res[var] / res[REF])
    times[(bench, var)].append(res[var]); times[(bench, REF)].append(res[REF])
    rows.append((bench, var, rnd, res[REF], res[var], res[var] / res[REF]))
with open(os.path.join(RES, 'paired-ratios.tsv'), 'w') as f:
    f.write(f'benchmark\tvariant\tround\t{REF}_s\tvariant_s\tratio\n')
    for r in rows:
        f.write('\t'.join(f'{x:.6f}' if isinstance(x, float) else str(x) for x in r) + '\n')

ir = {(r['benchmark'], r['variant']): int(r['Ir']) for r in read_tsv('instr-counts.tsv') if r['Ir']}
size = {(r['benchmark'], r['variant']): int(r['text_bytes']) for r in read_tsv('code-size.tsv')}
elf = {(r['benchmark'], r['variant']): r['elf_sha256'] for r in read_tsv('code-size.tsv')}
ok = {(r['benchmark'], r['variant']): r['matches_oracle'] for r in read_tsv('correctness.tsv')}
tier = {}
for line in open(os.path.join(EXP, 'configs', 'variants.tsv')):
    if line.strip() and not line.startswith('#'):
        p = line.split('\t'); tier[p[0]] = p[1]

benches = sorted({b for b, _ in size} | {b for b, _ in ratios})
tier[f'{REF}_control'] = 'control'
order = list(tier)
out = os.path.join(RES, 'summary.tsv')
with open(out, 'w') as f:
    f.write('benchmark\tvariant\ttier\tcorrect\tmedian_s\tn_pairs\tspeedup_vs_o3_pct\t'
            'ratio_min\tratio_max\tIr_vs_o3_pct\ttext_vs_o3_pct\tidentical_elf_to_o3\n')
    for b in benches:
        for v in order:
            if (b, v) not in size and (b, v) not in ratios:
                continue
            # byte-identical to the reference: any timing difference is noise (parent study's '≡')
            same = 'yes' if v.endswith('_control') or (elf.get((b, v)) and elf.get((b, v)) == elf.get((b, REF))) else 'no'
            t = times.get((b, v), [])
            rs = ratios.get((b, v), [])
            sp = f'{100 * (1 / geomean(rs) - 1):+.2f}' if rs else ('0.00' if v == REF else '')
            irp = (f'{100 * (ir[(b, v)] / ir[(b, REF)] - 1):+.2f}'
                   if (b, v) in ir and (b, REF) in ir else '+0.00' if v.endswith('_control') else 'n/a')
            szp = (f'{100 * (size[(b, v)] / size[(b, REF)] - 1):+.2f}' if (b, v) in size
                   else '+0.00' if v.endswith('_control') else 'n/a')
            f.write('\t'.join([b, v, tier.get(v, ''), ok.get((b, v), '?'),
                               f'{st.median(t):.4f}' if t else '', str(len(rs)), sp, f'{sum(r < 1 for r in rs)}/{len(rs)}' if rs else '',
                               f'{min(rs):.4f}' if rs else '', f'{max(rs):.4f}' if rs else '',
                               irp, szp, same]) + '\n')
print(open(out).read())
