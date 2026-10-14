const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
const context = vm.createContext({
  document: {getElementById() {return {value: ''};}},
  window: {matchMedia() {return {matches: false};}},
  Intl, Date, Number, String, URL,
});
vm.runInContext(source.split('$("searchInput").addEventListener')[0], context);
const entry = {
  snapshot: {updated_at: '2026-10-13T12:00:00+00:00', poi_pharmacy: 0},
  dvf: {year: 2025, by_type: {apartment: {median_price_m2: 4000, sample_count: 20}}},
  poi_commune: {status: 'available', scope:'commune', counts: {pharmacy: 17}},
};
context.testAudit = {cities: {'69123': entry}};
vm.runInContext('audit = testAudit; provenance = {};', context);
context.city = {insee_code: '69123', updated_at: '2026-10-13T12:00:00+00:00', poi_pharmacy: 0};
assert.equal(vm.runInContext('priceInfo(city).value', context), 4000);
assert.equal(vm.runInContext('poiValue(city, "poi_pharmacy")', context), 17);
context.city = {...context.city, poi_pharmacy: 4};
assert.equal(vm.runInContext('priceInfo(city).value', context), null, 'Métadonnées obsolètes rejetées');
assert.equal(vm.runInContext('poiValue(city, "poi_pharmacy")', context), null, 'Ancien compteur brut jamais utilisé comme total communal');
context.city = {insee_code: 'unknown', poi_pharmacy: 0, air_quality_score: 12};
assert.equal(vm.runInContext('poiValue(city, "poi_pharmacy")', context), null, 'Ancien zéro non certifié masqué');
assert.equal(vm.runInContext('airObservation(city)', context), null, 'Air sans polluant ni date masqué');
context.city = {insee_code:'69123',updated_at:'2026-10-13T12:00:00+00:00',poi_pharmacy:0};
entry.poi_commune.counts.pharmacy=0;
assert.equal(vm.runInContext('poiValue(city, "poi_pharmacy")', context),0,'Zéro communal documenté préservé');
entry.poi_commune.scope='radius';
assert.equal(vm.runInContext('poiValue(city, "poi_pharmacy")', context),null,'Un rayon ne devient pas une commune');
assert.equal(vm.runInContext('number(null)', context), '—');
assert.equal(vm.runInContext('number(0)', context), '0', 'Zéro documenté préservé');
assert.equal(vm.runInContext('escapeHtml("<script>")', context), '&lt;script&gt;');
assert.equal(source.includes('function scoreCity'), false, 'Pas de classement synthétique');
console.log('PASS: métadonnées liées aux observations, zéros incertains, air historique, échappement et absence de score');
