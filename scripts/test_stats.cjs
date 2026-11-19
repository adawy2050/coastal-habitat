const assert = require('node:assert/strict');
const S = require('../dist/stats.js');
const n=30, t=Array.from({length:n},(_,i)=>i), z=t.map(i=>Math.sin(i*1.3)), y=t.map((v,i)=>4+2*v-3*z[i]);
const fit=S.fit(y,[t,z]);
assert.ok(Math.abs(fit.r2-1)<1e-12);
assert.ok(fit.pred.every((v,i)=>Math.abs(v-y[i])<1e-10));
assert.ok(Math.abs(fit.beta[0]/fit.scales[0]-2)<1e-10);
assert.ok(Math.abs(fit.beta[1]/fit.scales[1]+3)<1e-10);
const sh=S.shapley(y,[t,z]);
assert.ok(Math.abs(sh.shares.reduce((a,b)=>a+b,0)-sh.r2)<1e-12);
const shared=S.shapley(t,[t,t]);
assert.ok(Math.abs(shared.shares[0]-.5)<1e-10 && Math.abs(shared.shares[1]-.5)<1e-10);
const residual=S.detrend(t.map((v,i)=>2*v+z[i]),t);
assert.ok(Math.abs(S.correlation(t,residual))<1e-12);
assert.equal(S.correlation([1,null,3,4],[2,9,6,8]),1);
const noise=t.map(i=>Math.cos(i*2.17)+i*.1), full=S.fit(noise,[t,z]);
let press=0;
for(let i=0;i<n;i++){
 const other=t.filter((_,k)=>k!==i), yy=noise.filter((_,k)=>k!==i), zz=z.filter((_,k)=>k!==i), ff=S.fit(yy,[other,zz]);
 const intercept=S.mean(yy),pred=intercept+ff.beta[0]*(t[i]-ff.means[0])/ff.scales[0]+ff.beta[1]*(z[i]-ff.means[1])/ff.scales[1];press+=(noise[i]-pred)**2;
}
const total=noise.reduce((a,v)=>a+(v-S.mean(noise))**2,0);
assert.ok(Math.abs(full.cvR2-(1-press/total))<1e-11);
console.log('PASS: coefficients, exact fit, shared/duplicate predictor allocation, detrending, missing pairs and PRESS vs explicit leave-one-out refits.');
