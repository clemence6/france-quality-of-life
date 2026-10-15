const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const root=path.join(__dirname,'../web');
const elements={priceType:{value:'apartment'},scatterMetric:{value:'poi_park'},riskCategory:{value:'all'}};
const context=vm.createContext({document:{getElementById(id){return elements[id]||={value:'',textContent:''};}},window:{matchMedia(){return {matches:false};}},Intl,Date,Number,String,URL});
vm.runInContext(fs.readFileSync(path.join(root,'en/app.js'),'utf8').split('$("searchInput").addEventListener')[0],context);
vm.runInContext(fs.readFileSync(path.join(root,'en/dashboard.js'),'utf8').split('window.addEventListener("cities:loaded"')[0],context);
context.report=JSON.parse(fs.readFileSync(path.join(root,'data/audit.json'),'utf8'));
context.fixtures=Object.entries(context.report.cities).map(([code,entry])=>({...entry.snapshot,insee_code:code,city_name:entry.geocoding.city}));
vm.runInContext('cities=fixtures; audit=report; provenance={};',context);
const rows=vm.runInContext('dashboardRows()',context);
assert.equal(rows.length,11);
assert.equal(rows.filter(r=>r.apartment!=null).length,10,'Translation must not change available observations');
assert.equal(vm.runInContext('number(1234.5,1)',context),'1,234.5');
assert.equal(vm.runInContext('date("2026-10-15T12:00:00Z")',context),'15 Oct 2026');
assert.equal(vm.runInContext('date(null)',context),'unknown date');
assert.equal(vm.runInContext('riskLabel("Inondation")',context),'Flooding');
assert.equal(vm.runInContext('riskFamily("Inondation")',context),'water','Filters still operate on original source labels');
for(const name of ['priceBars','housingDumbbells','servicesMatrix','scatterPlot','airLollipops','risksMatrix','qualityCoverage']) {
 const output=vm.runInContext(`${name}(dashboardRows())`,context);
 assert.doesNotMatch(output,/NaN|Infinity|undefined|ventes retenues|dans la commune|Sélectionnez|Lire les valeurs|Prix appartements|Donnée indisponible|collecte du/);
 assert.ok(output.length>100,name);
 assert.doesNotMatch(vm.runInContext(`${name}([])`,context),/NaN|Infinity|undefined/);
}
const english=fs.readFileSync(path.join(root,'en/index.html'),'utf8');
assert.match(english,/<html lang="en">/);
assert.match(english,/<base href="\.\.\/">/);
assert.match(english,/src="en\/app.js\?v=10"/);
assert.match(english,/Find the city that suits you/);
assert.match(english,/Sources & methodology/);
assert.doesNotMatch(english,/11 villes|Connexion aux données|Quel budget|La qualité/);
const languageSource=fs.readFileSync(path.join(root,'language.js'),'utf8');
function languageCase(lang,saved,storageBlocked=false){
 let event,change,replaced,assigned;
 const select={value:'',addEventListener(type,callback){change=callback;}};
 const storage={getItem(){if(storageBlocked)throw Error('blocked');return saved;},setItem(k,v){if(storageBlocked)throw Error('blocked');saved=v;}};
 vm.runInNewContext(languageSource,{document:{documentElement:{lang},baseURI:'https://example.web.app/',getElementById(){return select;},addEventListener(type,callback){event=callback;}},location:{hash:'#dashboard',replace(url){replaced=url;},assign(url){assigned=url;}},localStorage:storage,URL});
 return {select,get saved(){return saved;},get replaced(){return replaced;},get assigned(){return assigned;},ready(){event?.();},change(){change?.();}};
}
const remembered=languageCase('fr','en');
assert.equal(remembered.replaced,'https://example.web.app/en/#dashboard');
const switchBack=languageCase('en','en');switchBack.ready();
assert.equal(switchBack.select.value,'en');switchBack.select.value='fr';switchBack.change();
assert.equal(switchBack.saved,'fr');assert.equal(switchBack.assigned,'https://example.web.app/#dashboard');
const noStorage=languageCase('fr',null,true);noStorage.ready();noStorage.select.value='en';noStorage.change();
assert.equal(noStorage.assigned,'https://example.web.app/en/#dashboard');
console.log('PASS: English charts, unchanged observations, dates, risk labels, language memory and navigation');
