const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.join(__dirname, '../web');
const elements = {priceType:{value:'apartment'},scatterMetric:{value:'poi_park'},riskCategory:{value:'all'}};
const context = vm.createContext({
 document:{getElementById(id){return elements[id] ||= {value:'',textContent:''};}},
 window:{matchMedia(){return {matches:false};}}, Intl,Date,Number,String,URL,
});
vm.runInContext(fs.readFileSync(path.join(root,'app.js'),'utf8').split('$("searchInput").addEventListener')[0],context);
vm.runInContext(fs.readFileSync(path.join(root,'dashboard.js'),'utf8').split('window.addEventListener("cities:loaded"')[0],context);
context.report = JSON.parse(fs.readFileSync(path.join(root,'data/audit.json'),'utf8'));
context.fixtures = Object.entries(context.report.cities).map(([code,entry])=>({
 ...entry.snapshot,insee_code:code,city_name:entry.geocoding.city,
})).sort((a,b)=>a.city_name.localeCompare(b.city_name,'fr'));
vm.runInContext('cities=fixtures; audit=report; provenance={};',context);
const rows = vm.runInContext('dashboardRows()',context);
assert.equal(rows.length,11);
assert.equal(rows.filter(r=>r.apartment!=null).length,10);
const communal=Object.values(context.report.cities).filter(entry=>entry.poi_commune?.status==='available'&&entry.poi_commune?.scope==='commune').length;
assert.equal(rows.filter(r=>r.info.poi?.status==='available').length,communal);
assert.equal(rows.filter(r=>r.air!=null).length,10);
const toulouse=context.report.cities['31555'].poi_commune;
assert.equal(rows.find(r=>r.code==='31555').services.poi_park,toulouse?.status==='available'?toulouse.counts.park:null,'Seule la collecte communale est utilisée');
assert.equal(rows.find(r=>r.code==='67482').apartment,null,'DVF absente non inventée');
assert.equal(vm.runInContext('medianOfValues([1,4,8,11])',context),6);
assert.equal(vm.runInContext('finiteMetric(null)',context),null);
assert.equal(vm.runInContext('finiteMetric(0)',context),0);
for(const name of ['priceBars','housingDumbbells','servicesMatrix','scatterPlot','airLollipops','risksMatrix','qualityCoverage']) {
 const html=vm.runInContext(`${name}(dashboardRows())`,context);
 assert.doesNotMatch(html,/NaN|Infinity|undefined/,name+' : rendu numérique valide');
 assert.ok(html.length>100);
 const empty=vm.runInContext(`${name}([])`,context);
 assert.doesNotMatch(empty,/NaN|Infinity|undefined/,name+' : sélection vide sûre');
}
vm.runInContext('dashboardSelection=new Set(["69123"]);',context);
assert.equal(vm.runInContext('selectedDashboardRows().length',context),1);
elements.priceType.value='house';
assert.match(vm.runInContext('priceBars(selectedDashboardRows())',context),/5[\s\u202f]*000/);
elements.riskCategory.value='water';
assert.doesNotMatch(vm.runInContext('risksMatrix(selectedDashboardRows())',context),/Radon/);
console.log('PASS : couvertures réelles, manquants exclus, filtres, médianes, 7 graphiques et sélections vides');
