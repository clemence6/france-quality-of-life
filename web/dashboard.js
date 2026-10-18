/* Graphiques natifs SVG : valeurs brutes, unités séparées, manquants explicites. */
let dashboardSelection = null;
const CHART_COLORS = {teal: "#248474", orange: "#d7865f", blue: "#547d9b", amber: "#b58054"};

function finiteMetric(value) {
 return value != null && value !== "" && Number.isFinite(Number(value)) && Number(value) >= 0 ? Number(value) : null;
}
function dashboardRows() {
 return cities.map(city => {
  const info = information(city);
  const services = Object.fromEntries(POI.map(([key]) => [key, info.poi?.status === "available" && info.poi?.scope === "commune" ? finiteMetric(poiValue(city, key)) : null]));
  return {city, info, code: city.insee_code, name: city.city_name,
   apartment: finiteMetric(priceInfo(city).value), house: finiteMetric(priceInfo(city,"house").value),
   apartmentCount: priceInfo(city).count, houseCount: priceInfo(city,"house").count,
   samples: info.dvf ? finiteMetric(info.dvf.nb_ventes_totales) : null,
   services, air: airObservation(city), risks: info.risks?.risks ?? null};
 });
}
function selectedDashboardRows() {
 return dashboardRows().filter(row => dashboardSelection == null || dashboardSelection.has(row.code));
}
function medianOfValues(values) {
 if (!values.length) return null;
 const sorted = [...values].sort((a,b)=>a-b), middle = Math.floor(sorted.length / 2);
 return sorted.length % 2 ? sorted[middle] : (sorted[middle-1] + sorted[middle]) / 2;
}
function niceMaximum(value, steps=4) {
 if (!(value > 0)) return 1;
 const power = 10 ** Math.floor(Math.log10(value / steps));
 const unit = Math.ceil(value / steps / power) * power;
 return Math.ceil(value / unit) * unit;
}
function dataTable(headers, rows) {
 return `<details class="chart-data"><summary>Lire les valeurs en tableau</summary><div class="matrix-scroll"><table class="data-table"><thead><tr>${headers.map(h=>`<th scope="col">${escapeHtml(h)}</th>`).join("")}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(cell=>`<td>${escapeHtml(cell)}</td>`).join("")}</tr>`).join("")}</tbody></table></div></details>`;
}
function svgChart(label, width, height, body) {
 return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(label)}"><title>${escapeHtml(label)}</title>${body}</svg>`;
}
function chartEmpty(message) { return `<div class="chart-empty">${escapeHtml(message)}</div>`; }
function chartCity(row, body, description) {
 return `<g class="chart-point" data-chart-city="${escapeHtml(row.code)}" tabindex="0" role="button" aria-label="${escapeHtml(description)}"><title>${escapeHtml(description)}</title>${body}</g>`;
}
function priceBars(rows) {
 const type = $("priceType").value;
 const present = rows.filter(row=>row[type] != null).sort((a,b)=>a[type]-b[type]);
 $("priceNote").textContent = `${present.length} / ${rows.length} villes avec un prix disponible. Survolez une barre pour voir le nombre de ventes et la période. Le calcul est expliqué dans « Sources & méthode ».`;
 if (!present.length) return chartEmpty("Aucune médiane documentée pour ce type de logement dans la sélection.");
 const w=560, left=113, right=70, plot=w-left-right, h=present.length*29+50, max=niceMaximum(Math.max(...present.map(r=>r[type])));
 let body="";
 for (let i=0;i<=4;i++) {const x=left+plot*i/4;body+=`<line x1="${x}" y1="8" x2="${x}" y2="${h-35}" class="chart-gridline"/><text x="${x}" y="${h-13}" text-anchor="middle" class="chart-axis">${number(max*i/4)}</text>`;}
 present.forEach((row,i)=>{
  const y=12+i*29, length=row[type]/max*plot, selected=row.code===selectedId;
  const p=priceInfo(row.city,type), count=type==="apartment"?row.apartmentCount:row.houseCount;
  body+=chartCity(row,`<text x="0" y="${y+13}" class="chart-label">${escapeHtml(row.name)}</text><rect x="${left}" y="${y}" width="${length}" height="18" rx="4" fill="${selected?CHART_COLORS.orange:CHART_COLORS.teal}" opacity="${selected?1:.85}"/><text x="${left+length+7}" y="${y+13}" class="chart-value">${number(row[type])}</text>`,`${row.name} : ${number(row[type])} €/m², ${number(count)} ventes analysées, ${p.period}. Cliquez pour sélectionner cette ville.`);
 });
 return svgChart("Médianes des prix au mètre carré par ville, ordre croissant",w,h,body)+dataTable(["Ville","Médiane €/m²","Ventes analysées","Période"],present.map(row=>[row.name,number(row[type]),number(type==="apartment"?row.apartmentCount:row.houseCount),priceInfo(row.city,type).period]));
}
function housingDumbbells(rows) {
 const present=rows.filter(row=>row.apartment!=null&&row.house!=null);
 if (!present.length) return chartEmpty("Aucune ville ne dispose de deux médianes documentées dans cette sélection.");
 const w=560,left=113,right=24,plot=w-left-right,h=present.length*29+50,max=niceMaximum(Math.max(...present.flatMap(r=>[r.apartment,r.house])));
 let body="";
 for(let i=0;i<=4;i++){const x=left+plot*i/4;body+=`<line x1="${x}" y1="8" x2="${x}" y2="${h-35}" class="chart-gridline"/><text x="${x}" y="${h-13}" text-anchor="middle" class="chart-axis">${number(max*i/4)}</text>`;}
 present.forEach((row,i)=>{
  const y=20+i*29,a=left+row.apartment/max*plot,b=left+row.house/max*plot;
  body+=chartCity(row,`<text x="0" y="${y+4}" class="chart-label">${escapeHtml(row.name)}</text><line x1="${a}" y1="${y}" x2="${b}" y2="${y}" stroke="#b8c8bd" stroke-width="3"/><circle cx="${a}" cy="${y}" r="6" fill="${CHART_COLORS.teal}"/><circle cx="${b}" cy="${y}" r="6" fill="${CHART_COLORS.orange}"/>`,`${row.name} : appartements ${number(row.apartment)} €/m² (${number(row.apartmentCount)} ventes), maisons ${number(row.house)} €/m² (${number(row.houseCount)} ventes). Écart de médianes ${number(row.house-row.apartment)} €/m².`);
 });
 return svgChart("Écarts entre médianes des appartements et des maisons",w,h,body)+dataTable(["Ville","Appartement €/m²","Maison €/m²","Écart €/m²"],present.map(r=>[r.name,number(r.apartment),number(r.house),number(r.house-r.apartment)]));
}
function servicesMatrix(rows) {
 if (!rows.length) return chartEmpty("Sélectionnez au moins une ville pour afficher les services.");
 const maxima=Object.fromEntries(POI.map(([key])=>[key,Math.max(1,...rows.map(r=>r.services[key]??0))]));
 const header=POI.map(([,label])=>`<th scope="col">${label}</th>`).join("");
 const body=rows.map(row=>`<tr><td>${escapeHtml(row.name)}</td>${POI.map(([key,label])=>{
  const value=row.services[key];
  if(value==null)return `<td class="missing" title="${escapeHtml(row.name)} : ${label}, collecte non documentée">—</td>`;
  const proportion=value/maxima[key],light=96-proportion*60,ink=proportion>.6?"#fff":"#244a3a";
  return `<td style="background:hsl(156 30% ${light}%);color:${ink}" title="${escapeHtml(row.name)} : ${number(value)} services ${label.toLowerCase()} dans la commune, collecte du ${date(row.info.poi.collected_at)}${row.info.poi.retained?", dernière mise à jour indisponible":""}">${number(value)}</td>`;
 }).join("")}</tr>`).join("");
 return `<div class="matrix-scroll"><table class="services-table"><caption class="sr-only">Services référencés par catégorie et par commune</caption><thead><tr><th scope="col">Ville</th>${header}</tr></thead><tbody>${body}</tbody></table></div><div class="matrix-legend"><span>Moins de services</span><span class="legend-ramp"></span><span>Plus de services</span></div>`;
}
function budgetAnalysis(rows,key,budget) {
 if(!Number.isFinite(budget)||budget<200||budget>20000)return {status:"invalid",present:[],missing:[],eligible:[],top:[]};
 const present=rows.filter(row=>finiteMetric(row.apartment)>0 && finiteMetric(row.services[key])!=null && Number.isInteger(Number(row.info.dvf?.year)) && Number(row.info.dvf.year)>=2000);
 const codes=new Set(present.map(row=>row.code)),missing=rows.filter(row=>!codes.has(row.code));
 const eligible=present.filter(row=>row.apartment<=budget);
 const years=[...new Set(eligible.map(row=>Number(row.info.dvf.year)))];
 if(years.length>1)return {status:"periods",present,missing,eligible,top:[]};
 eligible.sort((a,b)=>b.services[key]-a.services[key] || a.apartment-b.apartment || a.name.localeCompare(b.name,"fr"));
 return {status:"ready",present,missing,eligible,top:eligible.slice(0,3),year:years[0]};
}
function budgetMethod(year) {
 return `<details class="tradeoff-method"><summary>Sources et méthode de cette sélection</summary><p>${sourceLink("dvf","Ventes immobilières · DVF")} · ${sourceLink("osm","Services cartographiés · OpenStreetMap")}</p><ol><li><strong>Votre budget fixe la première sélection.</strong> Le prix médian des appartements doit être inférieur ou égal au montant indiqué. Ce prix est calculé à partir des ventes DVF analysées, avec au moins 10 ventes par ville.</li><li><strong>Votre priorité détermine le classement.</strong> Les villes sont triées par nombre décroissant de services référencés dans la catégorie choisie. À égalité, le prix le plus bas passe en premier, puis l’ordre alphabétique. Jusqu’à trois villes sont proposées, sans ajouter de ville hors budget.</li><li><strong>Les mêmes données sont utilisées pour tous les résultats.</strong> Le code INSEE relie les ventes et les comptages de chaque commune. Les prix comparés portent sur le même millésime immobilier${year?` : ${escapeHtml(year)}`:""}. Une ville sans prix ou sans comptage documenté est exclue.</li></ol><p>Le budget porte sur une médiane au m², pas sur le prix de chaque appartement. Le comptage des services couvre toute la commune et peut favoriser les grandes villes. Il ne mesure ni leur qualité, ni leur proximité depuis un logement.</p><p>Les scripts Python préparent les données ; Supabase stocke les résultats et leur provenance ; les filtres JavaScript construisent cette sélection. Les dates de collecte restent visibles, y compris lorsqu’une observation précédente est conservée.</p></details>`;
}
function budgetRecommendations(rows) {
 const key=$("scatterMetric").value,label=POI.find(([k])=>k===key)[1],budget=Number($("budgetMax").value);
 const result=budgetAnalysis(rows,key,budget);
 if(result.status==="invalid")return chartEmpty("Indiquez un budget maximum entre 200 et 20 000 €/m².");
 if(result.status==="periods")return chartEmpty("Les prix dans ce budget couvrent des années différentes. Choisissez des villes avec le même millésime immobilier.");
 const {top,eligible,missing,year}=result;
 const summary=`<div class="budget-summary" role="status"><strong>Villes dans votre budget de ${number(budget)} €/m² maximum : ${eligible.length}.</strong><p>${top.length?`Votre priorité : ${escapeHtml(label.toLowerCase())}. Les résultats sont classés par nombre de services référencés.`:"Aucune ville documentée ne correspond à ce budget. Augmentez-le ou modifiez les villes sélectionnées."}</p></div>`;
 const cards=top.length?`<div class="budget-shortlist">${top.map((row,i)=>`<button class="tradeoff-city budget-city" data-chart-city="${escapeHtml(row.code)}"><span class="budget-rank">${i+1}</span><strong>${escapeHtml(row.name)} ↗</strong><span class="budget-service-count">${number(row.services[key])} <small>${escapeHtml(label.toLowerCase())}</small></span><span>${number(row.apartment)} €/m² · appartements</span><small>DVF ${escapeHtml(row.info.dvf.year)} · ${number(row.apartmentCount)} ventes analysées</small><small>Services collectés le ${date(row.info.poi.collected_at)}${row.info.poi.retained?" · chiffres précédents conservés":""}</small></button>`).join("")}</div>`:"";
 const schoolNote=key==="poi_school"?`<p class="tradeoff-exclusions">${escapeHtml(SCHOOL_COUNT_NOTE)}</p>`:"";
 const exclusions=missing.length?`<details class="budget-exclusions"><summary>Villes non évaluées : ${missing.length} · données incomplètes</summary><p>${missing.map(row=>escapeHtml(row.name)).join(", ")}. Les valeurs manquantes ne sont pas remplacées par zéro.</p></details>`:"";
 return summary+cards+schoolNote+exclusions+budgetMethod(year);
}
function airLollipops(rows) {
 const present=rows.filter(row=>row.air!=null);
 if(!present.length)return chartEmpty("Aucun relevé PM2.5 avec unité, station et date dans cette sélection.");
 const w=560,left=113,right=60,plot=w-left-right,h=present.length*29+50,max=niceMaximum(Math.max(...present.map(r=>Number(r.air.value))));
 let body="";
 for(let i=0;i<=4;i++){const x=left+plot*i/4;body+=`<line x1="${x}" y1="8" x2="${x}" y2="${h-35}" class="chart-gridline"/><text x="${x}" y="${h-13}" text-anchor="middle" class="chart-axis">${number(max*i/4,1)}</text>`;}
 present.forEach((row,i)=>{
  const y=20+i*29,x=left+Number(row.air.value)/max*plot;
  body+=chartCity(row,`<text x="0" y="${y+4}" class="chart-label">${escapeHtml(row.name)}</text><line x1="${left}" y1="${y}" x2="${x}" y2="${y}" stroke="#cedce4" stroke-width="3"/><circle cx="${x}" cy="${y}" r="6" fill="${CHART_COLORS.blue}"/><text x="${x+10}" y="${y+4}" class="chart-value">${number(row.air.value,1)}</text>`,`${row.name} : PM2.5 ${number(row.air.value,1)} µg/m³, station ${row.air.station}, à ${number(row.air.distance,1)} km, ${dateTime(row.air.measured_at)}. Relevé ponctuel, sans classement sanitaire.`);
 });
 return svgChart("Derniers relevés PM2.5 documentés, villes par ordre alphabétique",w,h,body)+dataTable(["Ville","PM2.5 µg/m³","Station","Distance km","Relevé"],present.map(r=>[r.name,number(r.air.value,1),r.air.station,number(r.air.distance,1),dateTime(r.air.measured_at)]));
}
function riskFamily(label) {
 const text=label.toLowerCase();
 if(/inond|crue|nappes|ruissell|submersion|barrage/.test(text))return "water";
 if(/séism|sism|radon|terrain|cavité|argile|effond|ébou|volcan/.test(text))return "ground";
 if(/atmosph|tempête|vent|neige|grêle|foudre|cyclon|feu|incend|avalanche/.test(text))return "weather";
 if(/industri|transport|marchand|thermique|toxique|surpression|nuclé/.test(text))return "industrial";
 return "other";
}
function risksMatrix(rows) {
 if(!rows.length)return chartEmpty("Sélectionnez au moins une ville pour explorer les risques recensés.");
 const category=$("riskCategory").value;
 const labels=[...new Set(rows.flatMap(row=>row.risks||[]))].filter(label=>category==="all"||riskFamily(label)===category).sort((a,b)=>a.localeCompare(b,"fr"));
 if(!labels.length)return chartEmpty("Aucun libellé de cette famille dans les réponses documentées de la sélection.");
 const head=rows.map(row=>`<th scope="col">${escapeHtml(row.name)}</th>`).join("");
 const body=labels.map(label=>`<tr><td>${escapeHtml(riskLabel(label))}</td>${rows.map(row=>{
  if(!row.risks)return '<td class="missing" title="Liste non documentée">—</td>';
  const present=row.risks.includes(label);
  return `<td class="${present?"present":""}" aria-label="${escapeHtml(row.name)} : ${present?"recensé":"non recensé dans cette réponse"}" title="${escapeHtml(row.name)} : ${present?"recensé":"non recensé dans cette réponse"}"><span class="${present?"risk-presence":"risk-absence"}" aria-hidden="true"></span></td>`;
 }).join("")}</tr>`).join("");
 return `<p class="risk-filter-note">${labels.length} types de risques affichés. Le filtre permet de choisir un thème.</p><div class="matrix-scroll"><table class="services-table risk-table" style="min-width:${Math.max(650,240+rows.length*76)}px"><caption class="sr-only">Présence des libellés officiels de risques par ville</caption><thead><tr><th scope="col">Type de risque</th>${head}</tr></thead><tbody>${body}</tbody></table></div><div class="chart-legend" style="margin-top:15px"><span><i style="background:#b58054"></i>Mentionné</span><span>○ Absent de cette liste</span><span>— Donnée indisponible</span></div>`;
}
function qualityCoverage(rows) {
 const n=rows.length;
 const retained=rows.filter(r=>r.info.poi?.status==="available"&&r.info.poi.retained).length;
 const definitions=[
  ["Immobilier · DVF",rows.filter(r=>r.apartment!=null||r.house!=null).length,"Prix calculés sur une sélection de ventes. Ils donnent un repère, sans décrire tous les logements."],
  ["Services · OSM",rows.filter(r=>r.info.poi?.status==="available").length,`Comptage sur toute la commune. Les services absents d’OpenStreetMap peuvent manquer.${retained?` Pour ${retained} ville(s), les derniers chiffres sont conservés après une panne, avec leur date.`:""}`],
  ["Air · OpenAQ",rows.filter(r=>r.air!=null).length,"La station et l’heure de chaque mesure sont conservées. Ces relevés ne décrivent pas toute une année."],
  ["Risques · GASPAR",rows.filter(r=>r.risks!=null).length,"Liste des risques mentionnés pour la commune. Elle ne décrit pas la situation de chaque logement."]
 ];
 return `<div class="quality-layout">${definitions.map(([label,count,note])=>`<div class="quality-item"><h4>${label}</h4><strong>${count} / ${n}</strong><div class="coverage-track"><span style="width:${n?count/n*100:0}%"></span></div><p>${note}</p></div>`).join("")}</div>`;
}
function renderDashboard() {
 if(!$("dashboard"))return;
 if(!cities.length){
  $("dashboardDate").textContent="En attente de la connexion aux données";
  $("analysisInsight").textContent="Les graphiques apparaîtront après le chargement des villes. Le statut de connexion est indiqué au-dessus de la carte.";
  $("kpiGrid").innerHTML=["Villes dans l’analyse","Prix immobiliers disponibles","Ventes analysées","Collectes de services"].map(label=>`<div class="kpi-card"><div class="kpi-top">${label}</div><div class="kpi-value">—</div><div class="kpi-note">En attente des données</div></div>`).join("");
  ["priceChart","housingChart","servicesChart","tradeoffChart","airChart","risksChart","qualityChart"].forEach(id=>{$(id).innerHTML=chartEmpty("Les données des villes ne sont pas encore chargées.");});
  return;
 }
 const rows=selectedDashboardRows(),n=rows.length,prices=rows.filter(r=>r.apartment!=null||r.house!=null),osm=rows.filter(r=>r.info.poi?.status==="available");
 const samples=rows.filter(r=>r.samples!=null),total=samples.reduce((sum,r)=>sum+r.samples,0);
 const collectedDates=rows.map(r=>r.info.collected?.collected_at||r.info.poi?.collected_at).filter(d=>d&&!Number.isNaN(Date.parse(d))).sort((a,b)=>Date.parse(b)-Date.parse(a));
 $("dashboardDate").textContent=collectedDates.length?`Dernière collecte du ${date(collectedDates[0])}`:audit.audited_at?`Contrôle du ${date(audit.audited_at)}`:"Observations documentées";
 $("dashboardCities").innerHTML=cities.map(city=>`<button class="city-chip" data-dashboard-city="${escapeHtml(city.insee_code)}" aria-pressed="${dashboardSelection==null||dashboardSelection.has(city.insee_code)}">${escapeHtml(city.city_name)}</button>`).join("");
 const cards=[["Villes dans l’analyse",n,"Choisissez les villes à comparer ci-dessus","⌖"],["Prix immobiliers disponibles",`${prices.length} <small>/ ${n}</small>`,"Villes avec des prix disponibles pour les appartements ou les maisons","⌂"],["Ventes analysées",samples.length?number(total):"—","Nombre de ventes de maisons et d’appartements étudiées","↗"],["Collectes de services",`${osm.length} <small>/ ${n}</small>`,"Services recensés à l’échelle de la commune","◈"]];
 $("kpiGrid").innerHTML=cards.map(([label,value,note,icon])=>`<div class="kpi-card"><div class="kpi-top"><span>${label}</span><span aria-hidden="true">${icon}</span></div><div class="kpi-value">${value}</div><div class="kpi-note">${note}</div></div>`).join("");
 const values=rows.filter(r=>r.apartment!=null).sort((a,b)=>a.apartment-b.apartment);
 if(values.length>=2){const low=values[0],high=values.at(-1);
  $("analysisInsight").innerHTML=`<strong>Dans votre sélection,</strong> les prix médians des appartements vont de <strong>${number(low.apartment)} €/m² à ${escapeHtml(low.name)}</strong> à <strong>${number(high.apartment)} €/m² à ${escapeHtml(high.name)}</strong>. Croisez ce budget avec les services de chaque commune pour affiner votre choix.`;
 }else $("analysisInsight").textContent=n?"La sélection ne contient pas assez de médianes d’appartements pour commenter leur dispersion. Les données disponibles restent affichées séparément.":"Aucune ville sélectionnée. Activez les villes à analyser ou utilisez « Toutes les villes ».";
 $("priceChart").innerHTML=priceBars(rows);$("housingChart").innerHTML=housingDumbbells(rows);
 $("servicesChart").innerHTML=servicesMatrix(rows);$("tradeoffChart").innerHTML=budgetRecommendations(rows);
 $("airChart").innerHTML=airLollipops(rows);$("risksChart").innerHTML=risksMatrix(rows);$("qualityChart").innerHTML=qualityCoverage(rows);
 $("dashboardCities").querySelectorAll("[data-dashboard-city]").forEach(button=>button.addEventListener("click",()=>{
  if(dashboardSelection==null)dashboardSelection=new Set(cities.map(c=>c.insee_code));
  const code=button.dataset.dashboardCity;if(dashboardSelection.has(code))dashboardSelection.delete(code);else dashboardSelection.add(code);
  renderDashboard();$("dashboardCities").querySelector(`[data-dashboard-city="${code}"]`)?.focus();
 }));
 $("dashboard").querySelectorAll("[data-chart-city]").forEach(point=>{
  const activate=()=>{
   selectCity(point.dataset.chartCity,false);
   if(point.classList.contains("tradeoff-city"))$("explorer").scrollIntoView({behavior:reducedMotion?"auto":"smooth",block:"start"});
  };
  point.addEventListener("click",activate);point.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();activate();}});
 });
}
window.addEventListener("cities:loaded",renderDashboard);
["priceType","scatterMetric","riskCategory"].forEach(id=>$(id).addEventListener("change",renderDashboard));
$("budgetMax").addEventListener("input",renderDashboard);
$("resetDashboard").addEventListener("click",()=>{dashboardSelection=null;renderDashboard();});
renderDashboard();
