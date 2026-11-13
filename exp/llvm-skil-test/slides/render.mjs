// Render the deck with headless Chromium over the DevTools protocol (pipe transport,
// no dependencies): wait for document.fonts.ready, screenshot every slide at 1920x1080
// plus one phone viewport, and export a PDF (one slide per page, backgrounds, selectable text).
// Usage: CHROME=/path/chrome-headless-shell node slides/render.mjs <deck.html> <out-dir>
import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";
import { resolve, basename } from "node:path";

const [deck, outDir] = process.argv.slice(2);
mkdirSync(outDir, { recursive: true });
const chrome = spawn(process.env.CHROME, ["--headless", "--no-sandbox", "--hide-scrollbars",
  "--remote-debugging-pipe", "about:blank"], { stdio: ["ignore", "ignore", "pipe", "pipe", "pipe"] });
const toChrome = chrome.stdio[3], fromChrome = chrome.stdio[4];
let id = 0, buf = "";
const pending = new Map(), waiters = [];
fromChrome.on("data", d => {
  buf += d.toString();
  let i;
  while ((i = buf.indexOf("\0")) >= 0) {
    const msg = JSON.parse(buf.slice(0, i)); buf = buf.slice(i + 1);
    if (msg.id && pending.has(msg.id)) { const { ok, err } = pending.get(msg.id); pending.delete(msg.id); msg.error ? err(new Error(JSON.stringify(msg.error))) : ok(msg.result); }
    else waiters.slice().forEach(w => w(msg));
  }
});
const send = (method, params = {}, sessionId) => new Promise((ok, err) => {
  const m = { id: ++id, method, params }; if (sessionId) m.sessionId = sessionId;
  pending.set(m.id, { ok, err }); toChrome.write(JSON.stringify(m) + "\0");
});
const once = (pred) => new Promise(ok => { const w = m => { if (pred(m)) { waiters.splice(waiters.indexOf(w), 1); ok(m); } }; waiters.push(w); });
const sleep = ms => new Promise(r => setTimeout(r, ms));

const { targetId } = await send("Target.createTarget", { url: "about:blank" });
const { sessionId: s } = await send("Target.attachToTarget", { targetId, flatten: true });
const ev = async (expr) => (await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true }, s)).result.value;
await send("Page.enable", {}, s);
const view = async (w, h, mobile = false) => send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile }, s);
await view(1920, 1080);
const loaded = once(m => m.method === "Page.loadEventFired" && m.sessionId === s);
await send("Page.navigate", { url: "file://" + resolve(deck) }, s);
await loaded;
const fonts = await ev("document.fonts.ready.then(()=>[...document.fonts].map(f=>f.family+' '+f.weight+':'+f.status))");
const n = await ev("document.querySelectorAll('.slide').length");
// overflow check: any element whose box extends past the 1920x1080 slide
const overflow = await ev(`[...document.querySelectorAll('.slide')].map((sl,i)=>{const r=sl.getBoundingClientRect();
  const bad=[...sl.querySelectorAll('*')].filter(e=>{const b=e.getBoundingClientRect();return b.width&&(b.right>r.right+1||b.bottom>r.bottom+1)}).length;return bad?('slide '+(i+1)+': '+bad+' overflowing'):null}).filter(Boolean)`);
const shots = [];
for (let i = 0; i < n; i++) {
  await ev(`deck.go(${i})`); await sleep(900);
  const { data } = await send("Page.captureScreenshot", { format: "png" }, s);
  const f = `${outDir}/slide-${String(i + 1).padStart(2, "0")}.png`; writeFileSync(f, Buffer.from(data, "base64")); shots.push(f);
}
await view(390, 844, true); await ev("dispatchEvent(new Event('resize'));deck.go(7)"); await sleep(900);
writeFileSync(`${outDir}/phone-slide-08.png`, Buffer.from((await send("Page.captureScreenshot", { format: "png" }, s)).data, "base64"));
await view(1920, 1080); await ev("dispatchEvent(new Event('resize'));deck.go(0)"); await sleep(300);
const pdf = await send("Page.printToPDF", { printBackground: true, preferCSSPageSize: true, paperWidth: 20, paperHeight: 11.25,
  marginTop: 0, marginBottom: 0, marginLeft: 0, marginRight: 0 }, s);
const pdfPath = deck.replace(/\.html$/, ".pdf"); writeFileSync(pdfPath, Buffer.from(pdf.data, "base64"));
console.log(JSON.stringify({ slides: n, fonts, overflow, shots: shots.length, pdf: pdfPath }, null, 1));
chrome.kill();
process.exit(0);
