/**
 * Viewport-invariance probe for candle-structure detection
 * =========================================================
 *
 * WHAT THIS TESTS
 *   Trading UIs that detect structure (fair-value gaps, order blocks, swings, sweeps, fib
 *   retracements) can be built two ways:
 *     (A) detect on a FIXED data window (the revealed price history) — what's on screen (zoom/pan)
 *         does NOT change the result; or
 *     (B) detect on the VISIBLE window (what the viewport currently shows) — zoom/pan DOES change it.
 *
 *   This probe runs the same detectors across 20 simulated viewports over one OHLC window and prints
 *   a table so you can SEE which category each detector falls into. The demonstrated result:
 *     • FVG detection is fed the fixed window  → identical across all 20 viewports (invariant).
 *     • Fib detection is fed the VISIBLE slice → varies with zoom/pan, by design (a zoomed-in trader
 *       anchors the recent leg; a zoomed-out trader anchors the macro leg).
 *   The detectors themselves are pure functions; only the candles handed to them change.
 *
 * HOW TO RUN
 *   npx tsx viewport-detection-probe.ts               # uses built-in synthetic OHLC
 *   npx tsx viewport-detection-probe.ts data.csv      # or supply your own CSV: time,open,high,low,close
 *
 * WHAT TO EXPECT
 *   A 20-row table. The FVG column is the SAME on every row (viewport is not an input). The fib column
 *   shows several DISTINCT anchor legs / 0.618 prices as the simulated viewport zooms and pans —
 *   including different legs when the window is parked over the price high vs the price low.
 *
 * NOTE: the detector bodies below are compact REFERENCE implementations of well-known ICT concepts
 * (3-candle FVG with a displacement gate; fractal swing pivots; swing-anchored fib retracement),
 * included so this file runs standalone. They demonstrate the METHOD; a production scanner adds more
 * tuning, but the viewport-invariance property shown here is an architectural one, independent of tuning.
 */

import * as fs from 'fs';

interface Candle { time: number; open: number; high: number; low: number; close: number; }

// ── Reference detectors (pure — input candles are the only variable) ─────────────────────────────

/** Bullish/bearish 3-candle fair-value gaps, newest-first, with a displacement gate + mitigation flag. */
function detectFVGs(candles: Candle[], fvgMin: number): Array<{ index: number; high: number; low: number; direction: 'bullish' | 'bearish'; mitigated: boolean }> {
  const out: Array<{ index: number; high: number; low: number; direction: 'bullish' | 'bearish'; mitigated: boolean }> = [];
  for (let i = 2; i < candles.length; i++) {
    const c0 = candles[i - 2], cMid = candles[i - 1], c = candles[i];
    const avg = ((c0.high - c0.low) + (cMid.high - cMid.low) + (c.high - c.low)) / 3;
    const displacement = (cMid.high - cMid.low) >= avg * 0.8;   // middle candle is the impulse
    if (!displacement) continue;
    const bull = c.low - c0.high;                                // gap between c0.high and c.low
    if (bull >= fvgMin) {
      const high = c.low, low = c0.high;
      let mit = false;
      for (let j = i + 1; j < candles.length; j++) { if (candles[j].low <= high) { mit = true; break; } }
      out.push({ index: i - 1, high, low, direction: 'bullish', mitigated: mit });
    }
    const bear = c0.low - c.high;
    if (bear >= fvgMin) {
      const high = c0.low, low = c.high;
      let mit = false;
      for (let j = i + 1; j < candles.length; j++) { if (candles[j].high >= low) { mit = true; break; } }
      out.push({ index: i - 1, high, low, direction: 'bearish', mitigated: mit });
    }
  }
  return out.filter(f => !f.mitigated).reverse();                // newest-first, unmitigated
}

/** Fractal swing pivots: a high (low) that is the max (min) within ±lookback bars. */
function detectSwings(candles: Candle[], lb = 2): Array<{ index: number; price: number; type: 'H' | 'L' }> {
  const out: Array<{ index: number; price: number; type: 'H' | 'L' }> = [];
  for (let i = lb; i < candles.length - lb; i++) {
    let isH = true, isL = true;
    for (let j = i - lb; j <= i + lb; j++) {
      if (candles[j].high > candles[i].high) isH = false;
      if (candles[j].low  < candles[i].low)  isL = false;
    }
    if (isH) out.push({ index: i, price: candles[i].high, type: 'H' });
    if (isL) out.push({ index: i, price: candles[i].low,  type: 'L' });
  }
  return out;
}

/** Swing-anchored fib: most-recent extreme + the immediately-preceding opposite swing = ONE leg.
 *  Invalidated (returns null) if price has closed beyond the 100% anchor (trend reversed, not retraced). */
function detectFib(candles: Candle[]): { direction: 'up' | 'down'; lowPrice: number; highPrice: number; lowIndex: number; highIndex: number } | null {
  if (candles.length < 5) return null;
  const sw = detectSwings(candles);
  const highs = sw.filter(s => s.type === 'H'), lows = sw.filter(s => s.type === 'L');
  if (!highs.length || !lows.length) return null;
  const H = highs.reduce((m, s) => (s.index > m.index ? s : m));
  const L = lows.reduce((m, s) => (s.index > m.index ? s : m));
  if (H.index === L.index) return null;
  let lowS, highS, direction: 'up' | 'down';
  if (H.index > L.index) {
    const prev = lows.filter(s => s.index < H.index).reduce<typeof lows[number] | null>((m, s) => (!m || s.index > m.index ? s : m), null);
    if (!prev) return null;
    lowS = prev; highS = H; direction = 'up';
  } else {
    const prev = highs.filter(s => s.index < L.index).reduce<typeof highs[number] | null>((m, s) => (!m || s.index > m.index ? s : m), null);
    if (!prev) return null;
    lowS = L; highS = prev; direction = 'down';
  }
  if (highS.price <= lowS.price) return null;
  const start = Math.min(lowS.index, highS.index);
  for (let i = start; i < candles.length; i++) {
    if (direction === 'up' ? candles[i].close < lowS.price : candles[i].close > highS.price) return null;
  }
  return { direction, lowPrice: lowS.price, highPrice: highS.price, lowIndex: lowS.index, highIndex: highS.index };
}

// ── Test data: built-in synthetic (deterministic), or a CSV you supply ───────────────────────────

function syntheticWindow(): Candle[] {
  // Deterministic (no randomness). A clean ICT-style staircase between control-point swings so different
  // viewports anchor different fib legs, plus one late UNMITIGATED bullish FVG as a fixed FVG target.
  const pts: Array<[number, number]> = [
    [0, 100], [12, 114], [22, 107], [34, 123], [46, 113],
    [58, 132], [70, 120], [82, 140], [95, 126], [107, 146], [119, 152],
  ];
  const priceAt = (i: number): number => {
    for (let k = 1; k < pts.length; k++) {
      if (i <= pts[k][0]) { const [i0, p0] = pts[k - 1]; const [i1, p1] = pts[k]; return p0 + (p1 - p0) * ((i - i0) / (i1 - i0)); }
    }
    return pts[pts.length - 1][1];
  };
  const bars: Candle[] = [];
  let t = 1_700_000_000;
  for (let i = 0; i < 120; i++) {
    const mid = priceAt(i);
    const open = mid - 0.5, close = mid + 0.5;
    bars.push({ time: t, open: +open.toFixed(2), high: +(Math.max(open, close) + 0.6).toFixed(2), low: +(Math.min(open, close) - 0.6).toFixed(2), close: +close.toFixed(2) });
    t += 300;
  }
  // Inject a clean bullish FVG at bars 110–112: bar 111 is a big up-impulse (displacement), bar 112 opens
  // ~5 above bar 110's high (the gap), and 113→119 hold above it so it stays unmitigated.
  const g = 110;
  const base = bars[g].high;
  bars[g + 1] = { ...bars[g + 1], open: base, close: +(base + 8).toFixed(2), high: +(base + 9).toFixed(2), low: +(base - 0.3).toFixed(2) };
  const gapLow = +(base + 5).toFixed(2);
  bars[g + 2] = { ...bars[g + 2], open: +(gapLow + 1).toFixed(2), close: +(gapLow + 2).toFixed(2), high: +(gapLow + 2.6).toFixed(2), low: gapLow };
  for (let i = g + 3; i < 120; i++) {
    const lvl = gapLow + 2 + (i - (g + 2)) * 0.5;
    bars[i] = { ...bars[i], open: +(lvl - 0.3).toFixed(2), close: +(lvl + 0.3).toFixed(2), high: +(lvl + 0.8).toFixed(2), low: +(lvl - 0.6).toFixed(2) };
  }
  return bars;
}

function loadCSV(path: string): Candle[] {
  return fs.readFileSync(path, 'utf8').trim().split('\n')
    .map(l => l.split(',').map(Number))
    .filter(r => r.length >= 5 && r.every(Number.isFinite))
    .map(([time, open, high, low, close]) => ({ time, open, high, low, close }));
}

// ── Probe ─────────────────────────────────────────────────────────────────────────────────────

const csvPath = process.argv[2];
const full: Candle[] = csvPath ? loadCSV(csvPath) : syntheticWindow();
const N = full.length;
const median = (a: number[]) => { const s = [...a].sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; };
const fvgMin = median(full.map(c => c.high - c.low)) * 0.5;      // data-driven threshold, scale-agnostic

const hiIdx = full.reduce((m, c, i) => (c.high > full[m].high ? i : m), 0);
const loIdx = full.reduce((m, c, i) => (c.low  < full[m].low  ? i : m), 0);
const clamp = (a: number, b: number): [number, number] => [Math.max(0, Math.min(a, b)), Math.min(N - 1, Math.max(a, b))];

const viewports: Array<{ label: string; win: [number, number] }> = [
  { label: 'full window (zoom out)',       win: clamp(0, N - 1) },
  { label: 'right 90%',                    win: clamp(Math.floor(N * 0.10), N - 1) },
  { label: 'right 75%',                    win: clamp(Math.floor(N * 0.25), N - 1) },
  { label: 'right 60%',                    win: clamp(Math.floor(N * 0.40), N - 1) },
  { label: 'right 50%',                    win: clamp(Math.floor(N * 0.50), N - 1) },
  { label: 'right 40%',                    win: clamp(Math.floor(N * 0.60), N - 1) },
  { label: 'right 30% (zoom in)',          win: clamp(Math.floor(N * 0.70), N - 1) },
  { label: 'right 20% (zoom in more)',     win: clamp(Math.floor(N * 0.80), N - 1) },
  { label: 'right 12% (recent leg)',       win: clamp(Math.floor(N * 0.88), N - 1) },
  { label: 'left half (pan left)',         win: clamp(0, Math.floor(N * 0.50)) },
  { label: 'left third',                   win: clamp(0, Math.floor(N * 0.33)) },
  { label: 'middle third (pan)',           win: clamp(Math.floor(N * 0.33), Math.floor(N * 0.66)) },
  { label: 'mid 40% window',               win: clamp(Math.floor(N * 0.30), Math.floor(N * 0.70)) },
  { label: 'near-TOP: window over high',   win: clamp(hiIdx - 20, hiIdx + 5) },
  { label: 'near-TOP: tight over high',    win: clamp(hiIdx - 10, hiIdx + 3) },
  { label: 'near-BOTTOM: window over low', win: clamp(loIdx - 20, loIdx + 5) },
  { label: 'near-BOTTOM: tight over low',  win: clamp(loIdx - 10, loIdx + 3) },
  { label: 'high→low span',                win: clamp(Math.min(hiIdx, loIdx), Math.max(hiIdx, loIdx)) },
  { label: 'first 25 bars',                win: clamp(0, 25) },
  { label: 'last 25 bars',                 win: clamp(N - 26, N - 1) },
];

const dp = Math.abs(full[0].close) < 20 ? 5 : 2;                 // forex 5dp / indices 2dp
const px = (n: number | undefined) => (n == null ? '—' : n.toFixed(dp));

// FVG on the FIXED window — identical input for EVERY viewport.
const fvg1 = detectFVGs(full, fvgMin)[0];

console.log(`\nOHLC window: ${N} bars (${csvPath ? `CSV ${csvPath}` : 'synthetic'}). fvgMin=${fvgMin.toFixed(6)}`);
console.log(`High @bar ${hiIdx}=${px(full[hiIdx].high)} | Low @bar ${loIdx}=${px(full[loIdx].low)}`);
console.log(`FVG input = fixed window (viewport-independent). Fib input = visible slice.\n`);

const header = ['#', 'viewport', 'FVG_1 (fixed win)', 'fib dir', 'fib low→high (visible)', 'fib 0.618'];
const rows = [header.join(' | '), header.map(h => '-'.repeat(h.length)).join('-|-')];
const fibKeys = new Set<string>();
viewports.forEach((v, i) => {
  const [s, e] = v.win;
  const vis = full.slice(s, e + 1);
  const fib = vis.length >= 5 ? detectFib(vis) : null;
  fibKeys.add(fib ? `${fib.lowPrice}_${fib.highPrice}` : 'null');
  const fib618 = fib ? fib.highPrice - (fib.highPrice - fib.lowPrice) * 0.618 : undefined;
  rows.push([
    String(i + 1).padStart(2),
    v.label.padEnd(26),
    (fvg1 ? `${fvg1.direction} ${px(fvg1.high)}→${px(fvg1.low)}` : 'none').padEnd(22),
    (fib?.direction ?? '—').padEnd(5),
    (fib ? `${px(fib.lowPrice)}→${px(fib.highPrice)}` : 'no clean leg').padEnd(22),
    px(fib618),
  ].join(' | '));
});
console.log(rows.join('\n'));
console.log(`\nFVG_1 across 20 runs: ${fvg1 ? `CONSTANT (${px(fvg1.high)}→${px(fvg1.low)})` : 'none'} — viewport is NOT an input ✔`);
console.log(`Fib across 20 runs:  ${fibKeys.size} DISTINCT results — viewport IS an input for fib (fed the visible slice).`);
