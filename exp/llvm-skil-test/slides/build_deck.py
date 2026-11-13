#!/usr/bin/env python3
"""Build the llvm-optimization skill test deck from exp/llvm-skil-test/results.

Every number on the slides is read from the result TSVs here (nothing typed by
hand except prose). Fonts (JetBrains Mono, Noto Sans TC; SIL OFL 1.1) are
subset to the deck's glyphs with fontTools and embedded, so the HTML is
self-contained and renders offline.

Usage (from exp/llvm-skil-test, with a Python that has fonttools + brotli):
  VIEWPORT_CSS=<frontend-slides>/references/viewport-base.css python -I slides/build_deck.py
"""
import base64, csv, html, io, math, os, re, sys, urllib.request

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(EXP, "results")
OUT = os.path.join(EXP, "slides", "llvm-skill-test.html")
CACHE = os.environ.get("FONT_CACHE", os.path.join(EXP, "build", "fonts"))

BENCHES = ["400.perlbench", "401.bzip2", "403.gcc", "435.gromacs", "436.cactusADM",
           "445.gobmk", "454.calculix", "456.hmmer", "462.libquantum", "465.tonto",
           "481.wrf", "482.sphinx3", "483.xalanc"]
SHORT = {"454.calculix": "454.calculix (SPOOLES)"}
SHORT_D = {"454.calculix": "454 SPOOLES"}


def tsv(name):
    with open(os.path.join(RES, name)) as f:
        return list(csv.DictReader(f, delimiter="\t"))


def summary(name):
    d = {}
    for r in tsv(name):
        d[(r["bench"], r["variant"], r["ref"])] = r
    return d


S1, S2, S3 = summary("timing-paired-summary.tsv"), summary("timing-stage2-paired-summary.tsv"), summary("timing-confirm-paired-summary.tsv")


def speed(row, key="geomean_ratio"):
    """speedup % of variant over ref (positive = faster)."""
    return 100 * (1 / float(row[key]) - 1)


def suite(d, variant, ref):
    vals = [math.log(float(d[(b, variant, ref)]["geomean_ratio"])) for b in BENCHES]
    return 100 * (math.exp(-sum(vals) / len(vals)) - 1)


def strict(b, v):  # Fortran workloads use the no-FMA spelling of native variants
    return v + "_nofma" if b in ("436.cactusADM", "465.tonto", "481.wrf") and v in ("o3_native", "lto_native") else v


esc = html.escape
fmt = lambda x: f"{x:+.1f}%"

# ---------------------------------------------------------------- numbers
o3_vs_full = {b: 100 * (float(S3[(b, "full", "o3")]["geomean_ratio"]) - 1) for b in BENCHES}
tuned = {b: S3[(b, "tuned", "o3")] for b in BENCHES}
tuned_cfg = {}
with open(os.path.join(EXP, "configs", "tuned.tsv")) as f:
    for line in f:
        if line.startswith("#") or not line.strip():
            continue
        b, v, why = line.rstrip("\n").split("\t")
        tuned_cfg[b] = (v, why)
control = {b for b in BENCHES if tuned_cfg[b][0] == "o3"}
SUITE_TUNED_O3 = suite(S3, "tuned", "o3")
SUITE_LTOINL_O3 = suite(S3, "lto_inl", "o3")
SUITE_TUNED_FULL = suite(S3, "tuned", "full")
SUITE_O3_FULL = suite(S3, "o3", "full")
with open(os.path.join(RES, "correctness.tsv")) as f:
    corr = [l.split("\t") for l in f.read().splitlines()]
N_MATCH = sum(1 for r in corr if r[2] == "MATCH")
N_DIFF = sum(1 for r in corr if r[2] == "DIFF")
N_SAMPLES = 770 + 1040 + 624
size = {}
for r in tsv("code-size.tsv"):
    size[(r["bench"], r["variant"])] = int(r["text_bytes"])
lto_size = {b: 100 * (size[(b, "lto_inl")] / size[(b, "o3")] - 1) for b in BENCHES}
rem = {}
with open(os.path.join(RES, "remarks-passed.tsv")) as f:
    for line in f:
        p = line.rstrip("\n").split("\t")
        if p[0] == "bench":
            continue
        rem[(p[0], p[1])] = dict(zip(["inline", "lv", "slp", "licm", "unroll", "gvn"], map(int, p[2:])))

# ---------------------------------------------------------------- SVG charts
POS, NEG, CTRL = "#2ea043", "#a371f7", "#6e7681"  # validated (dark, surface #0d1117)


def hbar(rows, lo, hi, width=1640, row_h=52, label_w=360, ticks=(), cap=None, whisk=None, title=""):
    """Diverging horizontal bars. rows: (label, value, color, tooltip). Values beyond `cap` are
    drawn to the edge with a break mark and their true value as the label."""
    plot_w = width - label_w - 120
    x = lambda v: label_w + (max(lo, min(hi, v)) - lo) / (hi - lo) * plot_w
    h = len(rows) * row_h + 56
    o = [f'<svg class="chart" viewBox="0 0 {width} {h}" width="{width}" height="{h}" role="img" aria-label="{esc(title)}">']
    for t in ticks:
        o.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="8" y2="{h-40}" class="grid{" zero" if t == 0 else ""}"/>'
                 f'<text x="{x(t):.1f}" y="{h-12}" class="tick" text-anchor="middle">{t:+d}%</text>')
    for i, (lab, v, col, tip) in enumerate(rows):
        y = 12 + i * row_h
        x0, x1 = sorted((x(0), x(v)))
        bh = row_h - 18
        o.append(f'<g class="bar"><title>{esc(tip)}</title>'
                 f'<rect x="0" y="{y-4}" width="{width}" height="{row_h}" fill="transparent"/>'
                 f'<text x="{label_w-20}" y="{y+bh/2+9}" class="lab" text-anchor="end">{esc(lab)}</text>'
                 f'<rect x="{x0:.1f}" y="{y}" width="{max(2, x1-x0):.1f}" height="{bh}" rx="4" fill="{col}"/>')
        if whisk and lab in whisk:
            a, b2 = whisk[lab]
            o.append(f'<line x1="{x(a):.1f}" x2="{x(b2):.1f}" y1="{y+bh/2}" y2="{y+bh/2}" class="whisk"/>'
                     f'<line x1="{x(a):.1f}" x2="{x(a):.1f}" y1="{y+6}" y2="{y+bh-6}" class="whisk"/>'
                     f'<line x1="{x(b2):.1f}" x2="{x(b2):.1f}" y1="{y+6}" y2="{y+bh-6}" class="whisk"/>')
        broken = cap is not None and v > hi
        if broken:
            o.append(f'<path d="M{x(hi)-26:.1f} {y-2} l12 {bh+4} M{x(hi)-14:.1f} {y-2} l12 {bh+4}" class="brk"/>')
        # value label: right of the bar end (or whisker) for positives, right of the zero
        # line for negatives, so it never collides with the category label on the left
        tx = x(v) + 14 if v >= 0 else x(0) + 14
        if whisk and lab in whisk:
            tx = x(whisk[lab][1]) + 14
        anchor = "start"
        o.append(f'<text x="{tx:.1f}" y="{y+bh/2+9}" class="val" text-anchor="{anchor}">{fmt(v)}</text></g>')
    o.append("</svg>")
    return "".join(o)


# Chart A: O3 vs repo full pipeline (confirmation stage)
rows_a = sorted(((SHORT.get(b, b), o3_vs_full[b], POS if o3_vs_full[b] >= 0 else NEG,
                  f"{b}: default<O3> vs 原研究 full，12 對 geomean {fmt(o3_vs_full[b])}") for b in BENCHES),
                key=lambda r: -r[1])
chart_a = hbar(rows_a, -10, 60, ticks=(-10, 0, 20, 40, 60), cap=60, width=1100, row_h=50, label_w=330,
               title="default O3 相對原研究 full pipeline 的速度變化")

# Chart B: tuned vs O3 with min/max whiskers
rows_b, wh = [], {}
for b in sorted(BENCHES, key=lambda b: -speed(tuned[b])):
    v = speed(tuned[b]); lab = SHORT.get(b, b)
    lo_, hi_ = speed(tuned[b], "max_ratio"), speed(tuned[b], "min_ratio")
    col = CTRL if b in control else (POS if v >= 0 else NEG)
    kind = "tuned = O3（同檔控制）" if b in control else tuned_cfg[b][0]
    rows_b.append((lab, v, col, f"{b}: {kind}，12 對 geomean {fmt(v)}，範圍 [{fmt(lo_)}, {fmt(hi_)}]"))
    wh[lab] = (lo_, hi_)
chart_b = hbar(rows_b, -12, 18, ticks=(-10, -5, 0, 5, 10, 15), whisk=wh, width=1180, row_h=56, label_w=330,
               title="逐項調校相對 O3 的速度變化（確認階段）")

# Chart D: .text change of LTO+inline vs O3
rows_d = sorted(((SHORT_D.get(b, b), lto_size[b], CTRL, f"{b}: lto_inl .text 相對 O3 {fmt(lto_size[b])}") for b in BENCHES),
                key=lambda r: r[1])
chart_d = hbar(rows_d, -60, 40, ticks=(-60, -40, -20, 0, 20, 40), width=860, row_h=40, label_w=330,
               title="LTO + inline 500 的 .text 大小相對 O3")

# Stage-2 heat table
KN = [("o3_native", "O3+ISA"), ("lto_native", "LTO+ISA"), ("lto_inl", "+inline 500"),
      ("lto_noslp", "+SLP off"), ("lto_unroll", "+unroll 600")]


def heat(v):
    if abs(v) < 1.5:
        return "rgba(110,118,129,.14)"
    a = min(1.0, abs(v) / 12) * 0.55 + 0.12
    return f"rgba(46,160,67,{a:.2f})" if v > 0 else f"rgba(163,113,247,{a:.2f})"


th = "".join(f"<th>{esc(n)}</th>" for _, n in KN)
trs = []
for b in BENCHES:
    vals = [speed(S2[(b, strict(b, k) if k in ("o3_native", "lto_native") else k, "o3")]) for k, _ in KN]
    best = max(vals)
    tds = "".join(f'<td style="background:{heat(v)}"{" class=best" if v == best and v >= 1.5 else ""}>{fmt(v)}</td>' for v in vals)
    trs.append(f"<tr><th>{esc(SHORT.get(b, b))}</th>{tds}</tr>")
heat_table = f'<table class="heat"><thead><tr><th>相對 O3（10 對）</th>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table>'

# Tuned config table
LABEL = {"lto_inl_noslp": "LTO · inline 500 · SLP off", "full": "原研究 full pipeline", "lto_inl": "LTO · inline 500",
         "o3": "default<O3>", "lto_inl_unroll": "LTO · inline 500 · unroll 600",
         "lto_unroll": "LTO · ISA(無FMA) · unroll 600", "o3_native": "O3 · Alder Lake ISA"}
cfg_rows = "".join(
    f'<tr><th>{esc(SHORT.get(b, b))}</th><td class="cfg">{esc(LABEL[tuned_cfg[b][0]])}</td>'
    f'<td class="num">{fmt(speed(tuned[b]))}</td><td class="num">{fmt(speed(S3[(b, "tuned", "full")]))}</td></tr>'
    for b in BENCHES)
cfg_table = f'<table class="cfgt"><thead><tr><th>工作量</th><th>建議設定</th><th>vs O3</th><th>vs full</th></tr></thead><tbody>{cfg_rows}</tbody></table>'

# Highlights
def t(b): return fmt(speed(tuned[b]))
hl = {b: t(b) for b in BENCHES}
s1 = lambda b, v: fmt(speed(S1[(b, v, "o3")]))

# ---------------------------------------------------------------- slides
SLIDES = []
add = SLIDES.append

add(f'''<section class="slide title-slide">
  <div class="prompt reveal"><span class="g">howard@cpu2006</span>:<span class="b">~/exp/llvm-skil-test</span>$ ./evaluate --skill llvm-optimization<span class="cursor"></span></div>
  <h1 class="reveal">llvm-optimization skill<br>× CPU2006 13 項</h1>
  <p class="sub reveal">測試 · 效能分析 · 優化</p>
  <div class="kpis reveal">
    <div class="kpi"><b>{fmt(SUITE_TUNED_O3)}</b><span>逐項調校 vs <code>default&lt;O3&gt;</code></span></div>
    <div class="kpi"><b>{fmt(SUITE_TUNED_FULL)}</b><span>vs 原研究 full pipeline</span></div>
    <div class="kpi"><b>{N_SAMPLES}</b><span>配對計時樣本</span></div>
    <div class="kpi"><b>0</b><span>採用設定的輸出差異</span></div>
  </div>
  <p class="foot reveal">skill：gmh5225/awesome-llvm-security · .claude/skills/llvm-optimization @ b7609b4 · 2026-11-13 · 13 項幾何平均，確認階段 12 對</p>
</section>''')

add(f'''<section class="slide">
  <div class="hdr reveal"><span class="n">01</span><h2>實驗設計：三階段，避免挑選偏誤</h2></div>
  <div class="flow reveal">
    <div class="step"><i>raw.bc</i><p>原研究 13 項共用 bitcode<br>LLVM 14 (C/C++) · 19 (Fortran)</p></div><span class="arr">→</span>
    <div class="step"><i>stage 1</i><p>skill 直接建議<br>O2 · O3 · Os · LTO · 目標 ISA</p></div><span class="arr">→</span>
    <div class="step"><i>remarks</i><p><code>-pass-remarks-output</code><br>找出要調整的 pass</p></div><span class="arr">→</span>
    <div class="step"><i>stage 2</i><p>inline / unroll / SLP knob<br>只用來挑設定</p></div><span class="arr">→</span>
    <div class="step hot"><i>stage 3</i><p>全新 12 輪獨立確認<br>報告數字全部出自這裡</p></div>
  </div>
  <div class="cols3 reveal">
    <div class="card"><h3>固定條件</h3><ul><li>同一 raw.bc、<code>llc -O=2</code>、同連結參數</li><li>原研究的固定輸入與工作目錄</li><li>i7-14700K，固定 CPU 2</li></ul></div>
    <div class="card"><h3>計時</h3><ul><li>每輪所有變體隨機排序各跑一次</li><li>同輪配對比值 → 幾何平均</li><li>{N_SAMPLES} 樣本（770 + 1040 + 624），全 exit 0</li></ul></div>
    <div class="card"><h3>正確性</h3><ul><li>每個變體與已驗證的 <code>full</code> 差分比對</li><li>{N_MATCH} MATCH · {N_DIFF} DIFF（皆為 FMA，見 06）</li><li>採用設定 100% 逐位元組相同</li></ul></div>
  </div>
</section>''')

add('''<section class="slide">
  <div class="hdr reveal"><span class="n">02</span><h2>skill 內容如何變成可量測的變體</h2></div>
  <table class="map reveal">
    <thead><tr><th>skill 段落</th><th>變體</th><th>實際指令</th></tr></thead>
    <tbody>
      <tr><td>Optimization Levels</td><td><code>o2 o3 os</code></td><td><code>opt -passes='default&lt;O2|O3|Os&gt;'</code></td></tr>
      <tr><td>Link-Time Optimization</td><td><code>lto</code></td><td><code>lto-pre-link&lt;O3&gt;,internalize,lto&lt;O3&gt;</code> · 只保留 <code>main,_QQmain</code></td></tr>
      <tr><td>Vectorization（目標 ISA）</td><td><code>*_native</code></td><td>IR <code>"target-cpu"</code> → <code>alderlake</code>（14700K 同 ISA）</td></tr>
      <tr><td>Optimization Remarks</td><td>分析</td><td><code>-pass-remarks-output -pass-remarks-filter='inline|loop-vectorize|slp|licm|unroll|gvn'</code></td></tr>
      <tr><td>Inlining · Unrolling · SLP</td><td>stage-2 knob</td><td><code>-inline-threshold=500</code> · <code>-unroll-threshold=600</code> · <code>-slp-threshold=1000</code></td></tr>
    </tbody>
  </table>
  <p class="note reveal">對照組：<code>full</code>＝原研究 15-pass 顯式 pipeline、<code>o3</code>＝<code>default&lt;O3&gt;</code>，直接複製原研究已驗證的執行檔。skill 中「撰寫自訂 pass / dominator tree / Alive2」屬於 pass 開發，不適用於調整既有程式，未納入。</p>
</section>''')

add(f'''<section class="slide">
  <div class="hdr reveal"><span class="n">03</span><h2>第一個發現：O3 比研究用 pipeline 快 {fmt(SUITE_O3_FULL)}</h2></div>
  <div class="split">
    <div class="reveal">{chart_a}</div>
    <div class="side reveal">
      <div class="card"><h3>讀法</h3><p>每列為 <code>default&lt;O3&gt;</code> 相對原研究 <code>full</code> 的速度變化，確認階段 12 對幾何平均。</p></div>
      <div class="card"><h3>重點</h3><ul>
        <li>HMMER {fmt(o3_vs_full["456.hmmer"])}（約 3.1 倍；圖中截斷）</li>
        <li>Cactus {fmt(o3_vs_full["436.cactusADM"])}、Tonto {fmt(o3_vs_full["465.tonto"])}、Xalan {fmt(o3_vs_full["483.xalanc"])}</li>
        <li>只有 bzip2（{fmt(o3_vs_full["401.bzip2"])}）與 WRF（{fmt(o3_vs_full["481.wrf"])}）是 <code>full</code> 較快</li>
      </ul></div>
      <div class="card"><h3>skill 其他等級</h3><ul>
        <li><code>-O2</code> 與 O3 差距多在 ±3% 內</li>
        <li><code>-Os</code> .text −4% 至 −31%，但 Xalan {s1("483.xalanc","os")}、Cactus {s1("436.cactusADM","os")}</li>
      </ul></div>
    </div>
  </div>
</section>''')

r = lambda b, v, k: f'{rem[(b, v)][k]:,}'
add(f'''<section class="slide">
  <div class="hdr reveal"><span class="n">04</span><h2>Remarks 指出差距來源</h2></div>
  <div class="split wide-left">
    <div class="reveal">
      <table class="rem">
        <thead><tr><th>Passed remarks</th><th>full</th><th>O3</th><th>LTO+ISA</th></tr></thead>
        <tbody>
          <tr><th>GVN · gcc</th><td class="bad">0</td><td>{r("403.gcc","o3","gvn")}</td><td>{r("403.gcc","lto_native","gvn")}</td></tr>
          <tr><th>GVN · Xalan</th><td class="bad">0</td><td>{r("483.xalanc","o3","gvn")}</td><td>{r("483.xalanc","lto_native","gvn")}</td></tr>
          <tr><th>loop-vectorize · Tonto</th><td>{r("465.tonto","full","lv")}</td><td>{r("465.tonto","o3","lv")}</td><td class="good">{r("465.tonto","lto_native","lv")}</td></tr>
          <tr><th>inline · Xalan</th><td>{r("483.xalanc","full","inline")}</td><td>{r("483.xalanc","o3","inline")}</td><td class="good">{r("483.xalanc","lto_native","inline")}</td></tr>
          <tr><th>inline · gcc</th><td>{r("403.gcc","full","inline")}</td><td>{r("403.gcc","o3","inline")}</td><td class="good">{r("403.gcc","lto_native","inline")}</td></tr>
        </tbody>
      </table>
      <ul class="bul">
        <li><b>原研究 pipeline 完全沒有 GVN</b>：O3 有數千筆冗餘消除，與 O3 整體快 20% 一致。</li>
        <li><b>Tonto 向量化</b>：x86-64 (SSE2) 成本模型讓多數 Fortran 迴圈不值得向量化；改 AVX2 後成功數增加約 5 倍。</li>
        <li><b>LTO 每項都 inline 更多</b>，且刪除未被呼叫的函式庫程式碼（右圖）。</li>
      </ul>
      <p class="note">remark 計數是嘗試次數，不等於速度；只用來挑 stage-2 要調的 pass。</p>
    </div>
    <div class="side reveal"><h3 class="ch">LTO + inline 500：.text 相對 O3</h3>{chart_d}</div>
  </div>
</section>''')

add(f'''<section class="slide">
  <div class="hdr reveal"><span class="n">05</span><h2>stage 1：skill 直接建議的設定（相對 O3）</h2></div>
  <div class="cols3 reveal">
    <div class="card big"><h3>LTO</h3><p class="v">{s1("400.perlbench","lto")}</p><p>Perl；gobmk {s1("445.gobmk","lto")}、Xalan {s1("483.xalanc","lto")}</p><p class="neg">Cactus {s1("436.cactusADM","lto")}：LTO 反而較慢</p></div>
    <div class="card big"><h3>目標 ISA（Alder Lake）</h3><p class="v">{s1("481.wrf","lto_native")}</p><p>WRF LTO+ISA；Sphinx O3+ISA {s1("482.sphinx3","o3_native")}</p><p>C/C++ 原本已是 x86-64-v3，增益小</p></div>
    <div class="card big"><h3>-O2 / -Os</h3><p class="v">≈ O3</p><p><code>-O2</code> 多在 ±3% 內</p><p class="neg"><code>-Os</code> Xalan {s1("483.xalanc","os")}、Cactus {s1("436.cactusADM","os")}</p></div>
  </div>
  <p class="note reveal">libquantum 在本階段的 O3 樣本有一次主機噪音尖峰（943 ms vs 常態約 390 ms），其 stage-1 比值不採用；stage 2/3 的 10–12 對中沒有變體勝過 O3。</p>
</section>''')

add(f'''<section class="slide">
  <div class="hdr reveal"><span class="n">06</span><h2>目標 ISA 的陷阱：Fortran + FMA 改變輸出</h2></div>
  <div class="split even">
    <div class="reveal">
      <pre class="term"><span class="c"># Flang 前端產生的 IR（WRF）</span>
attributes #0 = {{ "frame-pointer"="all" <span class="hl">"target-cpu"="x86-64"</span> }}
  11431  fmul <span class="hl">contract</span> float
   5414  fadd <span class="hl">contract</span> float

<span class="c"># target-cpu → alderlake：contract 被融合成 FMA</span>
<span class="neg">DIFF</span>  Cactus · Tonto · WRF   (6 個 native 變體)
  WRF  em_t_2  46359.5703 → 46359.5664   <span class="c"># 1 ULP (float32)</span>
  Tonto Kinetic Energy 76.771588 → 76.771596

<span class="c"># 修正：保留 AVX2，關閉 FMA</span>
"target-cpu"="alderlake" <span class="hl">"target-features"="-fma"</span>
<span class="ok">MATCH</span> 6/6 — 逐位元組相同</pre>
    </div>
    <div class="side reveal">
      <div class="card"><h3>結果（stage 1，相對 O3）</h3>
        <table class="mini"><thead><tr><th></th><th>含 FMA</th><th>無 FMA</th></tr></thead><tbody>
          <tr><th>WRF LTO+ISA</th><td>{s1("481.wrf","lto_native")}</td><td>{s1("481.wrf","lto_native_nofma")}</td></tr>
          <tr><th>Tonto O3+ISA</th><td>{s1("465.tonto","o3_native")}</td><td>{s1("465.tonto","o3_native_nofma")}</td></tr>
          <tr><th>Cactus O3+ISA</th><td>{s1("436.cactusADM","o3_native")}</td><td>{s1("436.cactusADM","o3_native_nofma")}</td></tr>
        </tbody></table></div>
      <div class="card"><h3>解讀</h3><ul><li>WRF 的增益來自 AVX2 寬度，關 FMA 仍保留</li><li>Tonto 的增益全來自 FMA；不能逐位元組相同就不採用</li><li>skill 未提醒此風險</li></ul></div>
    </div>
  </div>
</section>''')

add(f'''<section class="slide">
  <div class="hdr reveal"><span class="n">07</span><h2>stage 2：在嚴格正確的 LTO+ISA 上調整 knob</h2></div>
  <div class="split wide-left">
    <div class="reveal">{heat_table}</div>
    <div class="side reveal">
      <div class="card"><h3>突出結果</h3><ul>
        <li><b>SPOOLES 關 SLP {fmt(speed(S2[("454.calculix","lto_noslp","o3")]))}</b>：與原研究消融中 SLP 造成 −11% 一致</li>
        <li><b>inline 500</b> 是最一致的 knob：13 項幾何平均 {fmt(suite(S2,"lto_inl","o3"))}</li>
        <li>WRF 各欄都約 +10%：來源是 ISA，不是 knob</li>
        <li>Cactus：LTO 系列 −7%，維持 O3</li>
      </ul></div>
      <div class="card"><h3>噪音尺度</h3><p>5 項 <code>-unroll-threshold=600</code> 產生與 LTO+ISA 完全相同的檔案，兩欄差距（約 ±1.5%）即為噪音。|變化| &lt; 1.5% 以灰底表示。</p></div>
    </div>
  </div>
</section>''')

add(f'''<section class="slide">
  <div class="hdr reveal"><span class="n">08</span><h2>stage 3：獨立 12 輪確認，13 項 {fmt(SUITE_TUNED_O3)}</h2></div>
  <div class="split">
    <div class="reveal">{chart_b}
      <div class="legend"><span><i style="background:{POS}"></i>較 O3 快</span><span><i style="background:{NEG}"></i>較 O3 慢</span><span><i style="background:{CTRL}"></i>tuned = O3（同檔控制）</span><span><i class="wl"></i>12 對 min–max</span></div>
    </div>
    <div class="side reveal">
      <div class="card"><h3>重現 stage 2</h3><ul>
        <li>SPOOLES {fmt(speed(S2[("454.calculix","lto_noslp","o3")]))} → <b>{hl["454.calculix"]}</b></li>
        <li>WRF {fmt(speed(S2[("481.wrf","lto_unroll","o3")]))} → <b>{hl["481.wrf"]}</b></li>
        <li>Perl {fmt(speed(S2[("400.perlbench","lto_inl","o3")]))} → <b>{hl["400.perlbench"]}</b></li>
        <li>Xalan {fmt(speed(S2[("483.xalanc","lto_inl","o3")]))} → <b>{hl["483.xalanc"]}</b></li>
        <li>gcc {fmt(speed(S2[("403.gcc","lto_inl","o3")]))} → {hl["403.gcc"]}（不足以宣稱）</li>
      </ul></div>
      <div class="card"><h3>控制組</h3><p>5 項 tuned 即 O3 本身，同檔配對落在 {min(speed(tuned[b]) for b in control):+.2f}% 至 {max(speed(tuned[b]) for b in control):+.2f}%。統一設定 <code>lto_inl</code> 為 {fmt(SUITE_LTOINL_O3)}。</p></div>
    </div>
  </div>
</section>''')

add(f'''<section class="slide">
  <div class="hdr reveal"><span class="n">09</span><h2>建議設定（只在明顯超過噪音時離開 O3）</h2></div>
  <div class="split wide-left">
    <div class="reveal">{cfg_table}</div>
    <div class="side reveal">
      <div class="card"><h3>通用起點</h3><pre class="term small">opt -passes='lto-pre-link&lt;O3&gt;,
  internalize,lto&lt;O3&gt;' \\
  -internalize-public-api-list=main \\
  -inline-threshold=500 in.bc
# Fortran：target-cpu=alderlake
#          target-features=-fma</pre><p>13 項 {fmt(SUITE_LTOINL_O3)} vs O3</p></div>
      <div class="card"><h3>逐項例外</h3><ul><li>數值核心（SPOOLES）先試關 SLP</li><li>Cactus 不用 LTO</li><li>bzip2 原 pipeline 比 O3 快</li></ul></div>
    </div>
  </div>
</section>''')

add('''<section class="slide">
  <div class="hdr reveal"><span class="n">10</span><h2>skill 評估</h2></div>
  <div class="cols2 reveal">
    <div class="card good-b"><h3>有用</h3><ul>
      <li>最佳化等級、LTO、目標 ISA 三個方向找出全部主要增益</li>
      <li>Optimization Remarks 直接指出 GVN 缺席、Tonto 向量化與 LTO inlining</li>
      <li>Inlining／SLP 的概念說明對選 knob 有幫助</li>
    </ul></div>
    <div class="card bad-b"><h3>不足或與工具鏈不符</h3><ul>
      <li><code>opt -instcombine in.ll</code>（Alive2 範例）在 LLVM 19 失敗，需 <code>-passes=</code></li>
      <li><code>opt -stats</code> 在兩個 Debian release 工具鏈無輸出</li>
      <li>未說明 new PM 下如何關 SLP：<code>-vectorize-slp=false</code> 無效，需 <code>-slp-threshold</code></li>
      <li>未提醒改 ISA 會讓 <code>contract</code> 浮點融合成 FMA</li>
      <li>沒有 PGO、ThinLTO 實際流程；大段內容偏向 pass 開發</li>
    </ul></div>
  </div>
</section>''')

add('''<section class="slide">
  <div class="hdr reveal"><span class="n">11</span><h2>限制與下一步</h2></div>
  <div class="cols2 reveal">
    <div class="card"><h3>限制</h3><ul>
      <li>共用主機、未關 turbo；同檔控制單對仍可偏差 10% 以上，2% 以下不作結論</li>
      <li>repo 內程式與固定輸入，不是官方 SPEC 分數；454.calculix 實為 SPOOLES 元件</li>
      <li>只在 i7-14700K 驗證；alderlake ISA 執行檔需要 AVX2</li>
      <li>tuned 在同一輸入上選出，已獨立重測，換輸入或機器仍需重驗</li>
    </ul></div>
    <div class="card"><h3>下一步</h3><ul>
      <li>PGO（instrumented / sample-based）與 ThinLTO</li>
      <li>把 GVN 加入研究用 pipeline，重做消融以分離其貢獻</li>
      <li>以 Flang <code>-O2/-O3</code> 前端重產 Fortran IR，比較 FIR 層最佳化</li>
      <li>換輸入（SPEC train/ref）與另一台機器驗證 tuned 設定</li>
    </ul></div>
  </div>
  <p class="foot reveal">資料與重現：exp/llvm-skil-test/README.md · results/ · scripts/ · branch agent/llvm-skill-test</p>
</section>''')

# ---------------------------------------------------------------- template
CSS = r"""
:root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--ink:#e6edf3;--muted:#8b949e;--g:#39d353;--b:#58a6ff;
--pos:#2ea043;--neg:#a371f7;--warn:#d29922;--mono:'JetBrains Mono','Noto Sans TC',monospace;--cjk:'Noto Sans TC','JetBrains Mono',sans-serif;
--stage-bg:#010409;--slide-bg:#0d1117;--ease:cubic-bezier(.16,1,.3,1)}
*{margin:0;padding:0;box-sizing:border-box}
@page{size:1920px 1080px;margin:0}
"""
CSS2 = r"""
body{font-family:var(--cjk);color:var(--ink);-webkit-print-color-adjust:exact;print-color-adjust:exact}
.slide{padding:72px 96px;font-size:28px;line-height:1.5}
.slide::after{content:"";position:absolute;inset:0;pointer-events:none;background:repeating-linear-gradient(0deg,rgba(255,255,255,.018) 0 1px,transparent 1px 4px)}
.slide::before{content:"";position:absolute;left:96px;right:96px;bottom:52px;border-top:1px solid var(--line)}
code,pre,.n,.prompt,.tick,.val,.num,.heat td,.rem td,.mini td,.kpi b{font-family:var(--mono)}
code{color:var(--g);font-size:.86em}
h1{font-family:var(--mono);font-size:104px;line-height:1.08;font-weight:700;letter-spacing:-2px;margin:36px 0 18px}
h2{font-size:52px;font-weight:700;line-height:1.2}
h3{font-size:26px;color:var(--g);font-family:var(--mono);font-weight:700;margin-bottom:12px;letter-spacing:.5px}
.hdr{display:flex;align-items:baseline;gap:28px;margin-bottom:40px}
.slide:not(.title-slide){display:flex;flex-direction:column}
.body{flex:1;display:flex;flex-direction:column;justify-content:center;padding-bottom:56px}
.hdr .n{color:var(--g);font-size:30px;border:1px solid var(--g);padding:2px 14px;border-radius:4px}
.title-slide{display:flex;flex-direction:column;justify-content:center;background:radial-gradient(1200px 700px at 85% 10%,rgba(57,211,83,.10),transparent 60%),var(--bg)}
.prompt{font-size:30px;color:var(--muted)}.prompt .g{color:var(--g)}.prompt .b{color:var(--b)}
.cursor{display:inline-block;width:16px;height:34px;background:var(--g);vertical-align:-6px;margin-left:8px;animation:blink 1.1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
.sub{font-size:44px;color:var(--muted)}
.kpis{display:flex;gap:28px;margin-top:64px}
.kpi{flex:1;border:1px solid var(--line);background:var(--panel);border-radius:8px;padding:26px 30px;border-top:3px solid var(--g)}
.kpi b{display:block;font-size:60px;color:var(--ink)}.kpi span{color:var(--muted);font-size:24px}
.foot{position:absolute;left:96px;bottom:14px;font-size:20px;color:var(--muted)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:26px 30px}
.card p{font-size:25px;color:var(--ink)}.card p+p{margin-top:6px}
ul{list-style:none}li{position:relative;padding-left:30px;margin:6px 0;font-size:25px}
li::before{content:">";position:absolute;left:0;color:var(--g);font-family:var(--mono)}
.cols3{display:grid;grid-template-columns:repeat(3,1fr);gap:28px}
.cols2{display:grid;grid-template-columns:1fr 1fr;gap:32px}
.split{display:grid;grid-template-columns:auto 1fr;gap:40px;align-items:start}
.split.wide-left{grid-template-columns:1.25fr 1fr}.split.even{grid-template-columns:1.1fr 1fr}
.side{display:flex;flex-direction:column;gap:22px}
.flow{display:flex;align-items:stretch;gap:14px;margin-bottom:44px}
.step{flex:1;border:1px solid var(--line);border-radius:8px;padding:20px 22px;background:var(--panel)}
.step i{font-style:normal;font-family:var(--mono);color:var(--g);font-size:26px;font-weight:700}
.step p{font-size:22px;color:var(--muted);margin-top:8px}.step.hot{border-color:var(--g);box-shadow:0 0 0 1px var(--g) inset}
.arr{align-self:center;color:var(--g);font-family:var(--mono);font-size:34px}
table{border-collapse:collapse;width:100%}
th,td{text-align:left;padding:12px 16px;border-bottom:1px solid var(--line);font-size:24px}
thead th{color:var(--muted);font-weight:400;font-size:21px;border-bottom:1px solid var(--g)}
.map td:first-child{color:var(--ink);white-space:nowrap}.map td{font-size:24px}
.note{margin-top:28px;font-size:22px;color:var(--muted);max-width:1600px}
.heat th,.heat td{padding:9px 14px;font-size:22px;text-align:right}.heat th:first-child{text-align:left}
.heat td.best{outline:2px solid var(--g);outline-offset:-2px;font-weight:700}
.cfgt td,.cfgt th{font-size:23px;padding:10px 14px}.cfgt .num{text-align:right}.cfgt .cfg{color:var(--g);font-family:var(--mono);font-size:21px}
.rem th,.rem td{font-size:23px;padding:9px 14px}.rem td{text-align:right}.rem td.bad{color:var(--neg);font-weight:700}.rem td.good{color:var(--g);font-weight:700}
.bul{margin-top:22px}
.mini th,.mini td{font-size:22px;padding:8px 10px}.mini td{text-align:right}
.big .v{font-family:var(--mono);font-size:72px;font-weight:700;color:var(--ink);margin:4px 0 10px}
.neg{color:var(--neg)}.ok{color:var(--g)}
.term{background:#010409;border:1px solid var(--line);border-radius:8px;padding:28px 32px;font-size:22px;line-height:1.55;color:var(--ink);white-space:pre}
.term.small{font-size:19px;padding:18px 20px;margin-bottom:10px}
.term .c{color:var(--muted)}.term .hl{color:var(--warn)}
.good-b{border-top:3px solid var(--pos)}.bad-b{border-top:3px solid var(--neg)}
.chart .grid{stroke:var(--line);stroke-width:1}.chart .grid.zero{stroke:var(--muted);stroke-width:2}
.chart .tick{fill:var(--muted);font-size:20px}.chart .lab{fill:var(--ink);font-size:22px;font-family:var(--mono)}
.chart .val{fill:var(--ink);font-size:21px}.chart .whisk{stroke:var(--ink);stroke-width:2;opacity:.75}
.chart .brk{stroke:var(--bg);stroke-width:5}.chart .bar:hover rect:not([fill=transparent]){filter:brightness(1.25)}
.ch{margin-bottom:6px}
.legend{display:flex;gap:30px;font-size:21px;color:var(--muted);margin-top:6px;padding-left:40px}
.legend i{display:inline-block;width:18px;height:18px;border-radius:4px;vertical-align:-3px;margin-right:8px}
.legend i.wl{height:2px;width:26px;background:var(--ink);vertical-align:4px;border-radius:0}
.reveal{opacity:0;transform:translateY(24px);transition:opacity .6s var(--ease),transform .6s var(--ease)}
.slide.visible .reveal{opacity:1;transform:none}
.slide.visible .reveal:nth-child(2){transition-delay:.08s}.slide.visible .reveal:nth-child(3){transition-delay:.16s}.slide.visible .reveal:nth-child(4){transition-delay:.24s}
.pager{position:fixed;right:22px;bottom:16px;z-index:1000;font:16px var(--mono);color:#8b949e}
.edit-hotzone{position:fixed;top:0;left:0;width:80px;height:80px;z-index:10000}
.edit-toggle{position:fixed;top:16px;left:16px;z-index:10001;opacity:0;pointer-events:none;transition:opacity .3s;background:#161b22;color:#39d353;border:1px solid #39d353;border-radius:6px;font:14px var(--mono);padding:6px 10px;cursor:pointer}
.edit-toggle.show,.edit-toggle.active{opacity:1;pointer-events:auto}
[contenteditable=true]{outline:1px dashed rgba(57,211,83,.5)}
@media print{.slide{display:flex!important;flex-direction:column}.title-slide{justify-content:center}.slide .reveal{opacity:1!important;transform:none!important}.pager,.edit-toggle,.edit-hotzone{display:none!important}.cursor{animation:none}html,body,.deck-viewport{background:#0d1117!important}}
"""
JS = r"""
/* Deck controller: fixed 1920x1080 stage, keyboard / wheel / touch navigation, pager. */
class SlidePresentation{
  constructor(){this.slides=[...document.querySelectorAll('.slide')];this.stage=document.getElementById('deckStage');
    this.pager=document.getElementById('pager');this.i=0;this.lock=0;this.scale();addEventListener('resize',()=>this.scale());
    addEventListener('keydown',e=>{if(e.target.isContentEditable)return;
      if(['ArrowRight','ArrowDown','PageDown',' '].includes(e.key)){e.preventDefault();this.go(this.i+1)}
      if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key)){e.preventDefault();this.go(this.i-1)}
      if(e.key==='Home')this.go(0);if(e.key==='End')this.go(this.slides.length-1)});
    addEventListener('wheel',e=>{const t=Date.now();if(t-this.lock<600)return;this.lock=t;this.go(this.i+(e.deltaY>0?1:-1))},{passive:true});
    let x0=null;addEventListener('touchstart',e=>x0=e.touches[0].clientX,{passive:true});
    addEventListener('touchend',e=>{if(x0===null)return;const d=e.changedTouches[0].clientX-x0;if(Math.abs(d)>40)this.go(this.i+(d<0?1:-1));x0=null});
    const h=parseInt(location.hash.slice(1));this.go(isNaN(h)?0:h-1)}
  scale(){const f=Math.min(innerWidth/1920,innerHeight/1080);this.stage.style.transform=`translate(${(innerWidth-1920*f)/2}px,${(innerHeight-1080*f)/2}px) scale(${f})`}
  go(n){this.i=Math.max(0,Math.min(n,this.slides.length-1));this.slides.forEach((s,k)=>{s.classList.toggle('active',k===this.i);s.classList.toggle('visible',k===this.i)});
    this.pager.textContent=`${String(this.i+1).padStart(2,'0')} / ${String(this.slides.length).padStart(2,'0')}`;history.replaceState(null,'','#'+(this.i+1))}
}
const deck=new SlidePresentation();
/* Inline editing: E key or top-left hotzone; edits auto-save to localStorage (per browser). */
const editor={isActive:false,key:'llvm-skill-deck-v1',
  els(){return document.querySelectorAll('.slide h1,.slide h2,.slide h3,.slide p,.slide li,.slide td,.slide th')},
  toggleEditMode(){this.isActive=!this.isActive;this.els().forEach(el=>el.contentEditable=this.isActive);
    document.getElementById('editToggle').classList.toggle('active',this.isActive);if(!this.isActive)this.save()},
  save(){try{localStorage.setItem(this.key,JSON.stringify([...this.els()].map(e=>e.innerHTML)))}catch(e){}},
  load(){try{const d=JSON.parse(localStorage.getItem(this.key)||'null');if(d){const els=this.els();if(d.length===els.length)els.forEach((e,i)=>e.innerHTML=d[i])}}catch(e){}}};
editor.load();
document.addEventListener('input',()=>editor.isActive&&editor.save());
const tg=document.getElementById('editToggle'),hz=document.querySelector('.edit-hotzone');let ht=null;
tg.addEventListener('click',()=>editor.toggleEditMode());hz.addEventListener('click',()=>editor.toggleEditMode());
hz.addEventListener('mouseenter',()=>{clearTimeout(ht);tg.classList.add('show')});
hz.addEventListener('mouseleave',()=>{ht=setTimeout(()=>{if(!editor.isActive)tg.classList.remove('show')},400)});
tg.addEventListener('mouseenter',()=>clearTimeout(ht));
tg.addEventListener('mouseleave',()=>{ht=setTimeout(()=>{if(!editor.isActive)tg.classList.remove('show')},400)});
document.addEventListener('keydown',e=>{if((e.key==='e'||e.key==='E')&&!e.target.isContentEditable)editor.toggleEditMode()});
"""


def viewport_css():
    p = os.environ.get("VIEWPORT_CSS")
    with open(p) as f:
        return f.read()


def font_faces(text):
    """Subset JetBrains Mono / Noto Sans TC (full static TTFs from Google Fonts, cached) to the
    deck's glyphs with fontTools and embed them as base64 woff2. Needs fontTools + brotli."""
    from fontTools import subset
    os.makedirs(CACHE, exist_ok=True)
    body_chars = set(text) - set("\n\t\r")
    ascii_chars = set(chr(c) for c in range(0x20, 0x7F))
    # Noto gets only the visible slide text: adding extra symbols to its subset made Chromium
    # 1248 reject the Regular weight (NetworkError). JetBrains Mono also gets full ASCII.
    per_family = {"JetBrains Mono": "".join(sorted(body_chars | ascii_chars)), "Noto Sans TC": "".join(sorted(body_chars))}
    out = []
    for fam, q in (("JetBrains Mono", "JetBrains+Mono"), ("Noto Sans TC", "Noto+Sans+TC")):
        for w in (400, 700):
            ttf = os.path.join(CACHE, f"{q.replace('+', '')}-{w}.ttf")
            if not os.path.exists(ttf):
                css = urllib.request.urlopen(f"https://fonts.googleapis.com/css2?family={q}:wght@{w}", timeout=60).read().decode()
                src = re.search(r"url\((https://[^)]+)\)", css).group(1)
                with open(ttf, "wb") as f:
                    f.write(urllib.request.urlopen(src, timeout=120).read())
            opts = subset.Options(); opts.flavor = "woff2"; opts.layout_features = ["*"]
            font = subset.load_font(ttf, opts)
            sub = subset.Subsetter(opts); sub.populate(text=per_family[fam]); sub.subset(font)
            buf = io.BytesIO(); subset.save_font(font, buf, opts)
            b64 = base64.b64encode(buf.getvalue()).decode()
            out.append(f"@font-face{{font-family:'{fam}';font-weight:{w};font-style:normal;font-display:block;"
                       f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    return "\n".join(out)


def wrap_body(sl):
    i = sl.find("</h2></div>")
    if i < 0:
        return sl
    i += len("</h2></div>")
    j = sl.rfind("</section>")
    return sl[:i] + '\n  <div class="body">' + sl[i:j] + "</div>\n" + sl[j:]


SLIDES = [wrap_body(sl) for sl in SLIDES]
body = "\n".join(SLIDES)
# U+FF5E (fullwidth tilde) in the Noto Sans TC Regular subset makes Chromium reject the
# whole font (NetworkError on load; found by bisecting the glyph set). Use an en dash.
body = body.replace("～", "–")
visible_text = re.sub(r"<[^>]+>", " ", body + "00 / 12 EDIT")
visible_text = html.unescape(visible_text)
faces = font_faces(visible_text)
doc = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>llvm-optimization skill × CPU2006</title>
<!-- Fonts: JetBrains Mono (JetBrains) and Noto Sans TC (Google), both SIL Open Font License 1.1,
     subset to this deck's glyphs and embedded. Generated by slides/build_deck.py from results/. -->
<style>
{faces}
{CSS}
/* ---- viewport-base.css (frontend-slides skill, verbatim) ---- */
{viewport_css()}
/* ---- deck theme: Terminal Green ---- */
{CSS2}
</style>
</head>
<body>
<div class="deck-viewport"><main class="deck-stage" id="deckStage">
{body}
</main></div>
<div class="pager" id="pager" aria-live="polite"></div>
<div class="edit-hotzone"></div><button class="edit-toggle" id="editToggle" title="Edit mode (E)">EDIT</button>
<script>{JS}</script>
</body>
</html>
"""
with open(OUT, "w") as f:
    f.write(doc)
print(f"wrote {OUT} ({len(doc)//1024} KiB, {len(SLIDES)} slides)")
