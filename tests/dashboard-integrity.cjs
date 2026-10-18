const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.join(__dirname, '../web');
const elements = {priceType:{value:'apartment'},scatterMetric:{value:'poi_park'},budgetMax:{value:'3000'},riskCategory:{value:'all'}};
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
context.tradeoffFixtures=[
 {code:'a',name:'Alpha',apartment:2000,services:{poi_park:30},info:{dvf:{year:2025},poi:{collected_at:'2026-10-14',retained:true}},apartmentCount:20},
 {code:'b',name:'Beta',apartment:3000,services:{poi_park:20},info:{dvf:{year:2025},poi:{collected_at:'2026-10-15'}},apartmentCount:30},
 {code:'c',name:'Gamma',apartment:4000,services:{poi_park:40},info:{dvf:{year:2025},poi:{collected_at:'2026-10-15'}},apartmentCount:40},
 {code:'d',name:'Delta',apartment:2500,services:{poi_park:0},info:{dvf:{year:2025},poi:{collected_at:'2026-10-15'}},apartmentCount:15},
 {code:'e',name:'Epsilon',apartment:6000,services:{poi_park:20},info:{dvf:{year:2025},poi:{collected_at:'2026-10-15'}},apartmentCount:10},
 {code:'f',name:'Inconnue',apartment:1,services:{poi_park:null},info:{dvf:{year:2025}}}
];
let choices=vm.runInContext('budgetAnalysis(tradeoffFixtures,"poi_park",3000)',context);
assert.equal(choices.top.map(row=>row.code).join(','),'a,b,d','Le budget exclut les villes trop chères ; le classement suit les services, zéro documenté compris');
assert.equal(choices.eligible.length,3,'Le prix égal au budget est accepté');
assert.equal(choices.missing.length,1,'Une ville sans services reste inconnue');
assert.equal(vm.runInContext('budgetAnalysis(tradeoffFixtures,"poi_park",6000).top.map(row=>row.code).join(",")',context),'c,a,b','Trois propositions au maximum ; à égalité, le prix le plus bas est prioritaire');
assert.equal(vm.runInContext('budgetAnalysis(tradeoffFixtures,"poi_park",1000).top.length',context),0,'Aucune ville hors budget ne complète les résultats');
assert.equal(vm.runInContext('budgetAnalysis(tradeoffFixtures.slice(0,1),"poi_park",3000).top.length',context),1,'Un seul résultat reste affichable');
assert.equal(vm.runInContext('budgetAnalysis(tradeoffFixtures,"poi_park",2999.99).top.length',context),2,'Le budget décimal reste précis');
assert.equal(vm.runInContext('budgetAnalysis(tradeoffFixtures,"poi_park",NaN).status',context),'invalid');
assert.equal(vm.runInContext('budgetAnalysis(tradeoffFixtures,"poi_park",Infinity).status',context),'invalid');
assert.equal(vm.runInContext('budgetAnalysis(tradeoffFixtures,"poi_park",0).status',context),'invalid');
const budgetHtml=vm.runInContext('budgetRecommendations(tradeoffFixtures)',context);
assert.match(budgetHtml,/Alpha/);assert.match(budgetHtml,/chiffres précédents conservés/);
assert.match(budgetHtml,/Inconnue/);assert.doesNotMatch(budgetHtml,/NaN|Infinity|undefined/);
assert.equal(vm.runInContext('budgetAnalysis(tradeoffFixtures.slice(0,3).map((row,i)=>({...row,info:{dvf:{year:i?2025:2024}}})),"poi_park",3000).status',context),'periods','Ne pas classer ensemble des prix de millésimes différents');
for(const name of ['priceBars','housingDumbbells','servicesMatrix','budgetRecommendations','airLollipops','risksMatrix','qualityCoverage']) {
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
console.log('PASS : couvertures réelles, manquants exclus, filtres, médianes, graphiques, sélection par budget et états vides');
