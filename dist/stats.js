/* Small, dependency-free annual-series statistics. Missing values are never zero-filled. */
(function (root) {
  'use strict';
  const mean = a => a.reduce((s, v) => s + v, 0) / a.length;
  const dot = (a, b) => a.reduce((s, v, i) => s + v * b[i], 0);
  const finite = x => x !== null && x !== undefined && Number.isFinite(x);
  function standardize(a) {
    const ok = a.filter(finite), m = mean(ok), sd = Math.sqrt(mean(ok.map(v => (v - m) ** 2)));
    return a.map(v => finite(v) ? (sd > 1e-12 ? (v - m) / sd : 0) : null);
  }
  function fit(y, columns = []) {
    const n = y.length, ym = mean(y), yc = y.map(v => v - ym);
    const sst = dot(yc, yc), Q = [], R = [], active = [], xm = [], xs = [];
    for (let j = 0; j < columns.length; j++) {
      const m = mean(columns[j]), sd = Math.sqrt(mean(columns[j].map(v => (v - m) ** 2)));
      xm.push(m); xs.push(sd);
      if (sd < 1e-12) continue;
      let v = columns[j].map(x => (x - m) / sd), rr = [];
      for (let k = 0; k < Q.length; k++) {
        const r = dot(Q[k], v); rr.push(r); v = v.map((x, i) => x - r * Q[k][i]);
      }
      // Reorthogonalization protects highly correlated index subsets.
      for (let k = 0; k < Q.length; k++) {
        const r = dot(Q[k], v); rr[k] += r; v = v.map((x, i) => x - r * Q[k][i]);
      }
      const norm = Math.sqrt(dot(v, v));
      if (norm < 1e-9) continue;
      rr.push(norm); R.push(rr); Q.push(v.map(x => x / norm)); active.push(j);
    }
    const projected = Q.map(q => dot(q, yc));
    const pred = y.map((_, i) => ym + Q.reduce((s, q, j) => s + q[i] * projected[j], 0));
    const residual = y.map((v, i) => v - pred[i]);
    const sse = dot(residual, residual), r2 = sst > 1e-12 ? Math.max(0, Math.min(1, 1 - sse / sst)) : 0;
    const betaActive = new Array(Q.length).fill(0);
    for (let j = Q.length - 1; j >= 0; j--) {
      let rhs = projected[j];
      for (let k = j + 1; k < Q.length; k++) rhs -= R[k][j] * betaActive[k];
      betaActive[j] = rhs / R[j][j];
    }
    const beta = new Array(columns.length).fill(0);
    active.forEach((j, k) => { beta[j] = betaActive[k]; });
    const leverage = y.map((_, i) => 1 / n + Q.reduce((s, q) => s + q[i] ** 2, 0));
    const press = residual.reduce((s, v, i) => s + (v / Math.max(1e-10, 1 - leverage[i])) ** 2, 0);
    return {n, pred, residual, r2, beta, means: xm, scales: xs, rank: Q.length + 1,
      adjustedR2: n > Q.length + 1 && sst > 1e-12 ? 1 - (1 - r2) * (n - 1) / (n - Q.length - 1) : null,
      cvR2: n > Q.length + 2 && sst > 1e-12 ? 1 - press / sst : null};
  }
  function detrend(a, years) {
    const keep = a.map((v, i) => finite(v) && finite(years[i]) ? i : -1).filter(i => i >= 0);
    if (keep.length < 3) return a.map(() => null);
    const f = fit(keep.map(i => a[i]), [keep.map(i => years[i])]);
    const out = a.map(() => null); keep.forEach((i, k) => { out[i] = f.residual[k]; }); return out;
  }
  function correlation(a, b) {
    const pairs = a.map((v, i) => [v, b[i]]).filter(p => p.every(finite));
    if (pairs.length < 3) return null;
    const aa = pairs.map(p => p[0]), bb = pairs.map(p => p[1]), am = mean(aa), bm = mean(bb);
    const ac = aa.map(v => v - am), bc = bb.map(v => v - bm), den = Math.sqrt(dot(ac, ac) * dot(bc, bc));
    return den > 1e-12 ? dot(ac, bc) / den : null;
  }
  function shapley(y, columns) {
    const p = columns.length, count = 1 << p, values = new Float64Array(count), sizes = new Uint8Array(count);
    for (let mask = 1; mask < count; mask++) {
      sizes[mask] = sizes[mask >> 1] + (mask & 1);
      values[mask] = fit(y, columns.filter((_, j) => mask & (1 << j))).r2;
    }
    const fact = [1]; for (let j = 1; j <= p; j++) fact.push(fact[j - 1] * j);
    const shares = columns.map((_, j) => {
      let value = 0;
      for (let mask = 0; mask < count; mask++) if (!(mask & (1 << j))) {
        const s = sizes[mask]; value += fact[s] * fact[p - s - 1] / fact[p] * (values[mask | (1 << j)] - values[mask]);
      }
      return Math.max(0, value);
    });
    return {...fit(y, columns), shares};
  }
  function trend(years, a) {
    const keep = a.map((v, i) => finite(v) ? i : -1).filter(i => i >= 0);
    if (keep.length < 3) return null;
    const f = fit(keep.map(i => a[i]), [keep.map(i => years[i])]);
    return f.scales[0] > 0 ? f.beta[0] / f.scales[0] * 10 : 0;
  }
  const api = {mean, finite, standardize, fit, detrend, correlation, shapley, trend};
  root.AtlasStats = api;
  if (typeof module !== 'undefined') module.exports = api;
})(typeof window === 'undefined' ? globalThis : window);
