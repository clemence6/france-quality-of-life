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
 return `<details class="chart-data"><summary>Read values in a table</summary><div class="matrix-scroll"><table class="data-table"><thead><tr>${headers.map(h=>`<th scope="col">${escapeHtml(h)}</th>`).join("")}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(cell=>`<td>${escapeHtml(cell)}</td>`).join("")}</tr>`).join("")}</tbody></table></div></details>`;
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
 $("priceNote").textContent = `${present.length} / ${rows.length} cities with available prices. Hover over a bar to see the sample size and dates. The calculation is explained in Sources & methodology.`;
 if (!present.length) return chartEmpty("No documented median is available for this property type in the selection.");
 const w=560, left=113, right=70, plot=w-left-right, h=present.length*29+50, max=niceMaximum(Math.max(...present.map(r=>r[type])));
 let body="";
 for (let i=0;i<=4;i++) {const x=left+plot*i/4;body+=`<line x1="${x}" y1="8" x2="${x}" y2="${h-35}" class="chart-gridline"/><text x="${x}" y="${h-13}" text-anchor="middle" class="chart-axis">${number(max*i/4)}</text>`;}
 present.forEach((row,i)=>{
  const y=12+i*29, length=row[type]/max*plot, selected=row.code===selectedId;
  const p=priceInfo(row.city,type), count=type==="apartment"?row.apartmentCount:row.houseCount;
  body+=chartCity(row,`<text x="0" y="${y+13}" class="chart-label">${escapeHtml(row.name)}</text><rect x="${left}" y="${y}" width="${length}" height="18" rx="4" fill="${selected?CHART_COLORS.orange:CHART_COLORS.teal}" opacity="${selected?1:.85}"/><text x="${left+length+7}" y="${y+13}" class="chart-value">${number(row[type])}</text>`,`${row.name} : ${number(row[type])} €/m², ${number(count)} retained sales, ${p.period}. Select to highlight this city.`);
 });
 return svgChart("Median property prices per square metre by city, ascending order",w,h,body)+dataTable(["City","Median €/m²","Retained sales","Period"],present.map(row=>[row.name,number(row[type]),number(type==="apartment"?row.apartmentCount:row.houseCount),priceInfo(row.city,type).period]));
}
function housingDumbbells(rows) {
 const present=rows.filter(row=>row.apartment!=null&&row.house!=null);
 if (!present.length) return chartEmpty("No city in this selection has two documented medians.");
 const w=560,left=113,right=24,plot=w-left-right,h=present.length*29+50,max=niceMaximum(Math.max(...present.flatMap(r=>[r.apartment,r.house])));
 let body="";
 for(let i=0;i<=4;i++){const x=left+plot*i/4;body+=`<line x1="${x}" y1="8" x2="${x}" y2="${h-35}" class="chart-gridline"/><text x="${x}" y="${h-13}" text-anchor="middle" class="chart-axis">${number(max*i/4)}</text>`;}
 present.forEach((row,i)=>{
  const y=20+i*29,a=left+row.apartment/max*plot,b=left+row.house/max*plot;
  body+=chartCity(row,`<text x="0" y="${y+4}" class="chart-label">${escapeHtml(row.name)}</text><line x1="${a}" y1="${y}" x2="${b}" y2="${y}" stroke="#b8c8bd" stroke-width="3"/><circle cx="${a}" cy="${y}" r="6" fill="${CHART_COLORS.teal}"/><circle cx="${b}" cy="${y}" r="6" fill="${CHART_COLORS.orange}"/>`,`${row.name} : apartments ${number(row.apartment)} €/m² (${number(row.apartmentCount)} sales), houses ${number(row.house)} €/m² (${number(row.houseCount)} sales). Difference between medians ${number(row.house-row.apartment)} €/m².`);
 });
 return svgChart("Differences between apartment and house medians",w,h,body)+dataTable(["City","Apartment €/m²","House €/m²","Difference €/m²"],present.map(r=>[r.name,number(r.apartment),number(r.house),number(r.house-r.apartment)]));
}
function servicesMatrix(rows) {
 if (!rows.length) return chartEmpty("Select at least one city to display services.");
 const maxima=Object.fromEntries(POI.map(([key])=>[key,Math.max(1,...rows.map(r=>r.services[key]??0))]));
 const header=POI.map(([,label])=>`<th scope="col">${label}</th>`).join("");
 const body=rows.map(row=>`<tr><td>${escapeHtml(row.name)}</td>${POI.map(([key,label])=>{
  const value=row.services[key];
  if(value==null)return `<td class="missing" title="${escapeHtml(row.name)} : ${label}, undocumented collection">—</td>`;
  const proportion=value/maxima[key],light=96-proportion*60,ink=proportion>.6?"#fff":"#244a3a";
  return `<td style="background:hsl(156 30% ${light}%);color:${ink}" title="${escapeHtml(row.name)} : ${number(value)} mapped ${label.toLowerCase()} across the municipality, collected on ${date(row.info.poi.collected_at)}${row.info.poi.retained?", latest update unavailable":""}">${number(value)}</td>`;
 }).join("")}</tr>`).join("");
 return `<div class="matrix-scroll"><table class="services-table"><caption class="sr-only">Mapped services by category and municipality</caption><thead><tr><th scope="col">City</th>${header}</tr></thead><tbody>${body}</tbody></table></div><div class="matrix-legend"><span>Fewer services</span><span class="legend-ramp"></span><span>More services</span></div>`;
}
function tradeoffAnalysis(rows,key) {
 const present=rows.filter(row=>finiteMetric(row.apartment)>0 && finiteMetric(row.services[key])!=null && Number.isInteger(Number(row.info.dvf?.year)) && Number(row.info.dvf.year)>=2000);
 const codes=new Set(present.map(row=>row.code)),missing=rows.filter(row=>!codes.has(row.code));
 const years=[...new Set(present.map(row=>Number(row.info.dvf.year)))];
 if(years.length>1)return {status:"periods",present,missing};
 if(present.length<3)return {status:"insufficient",present,missing};
 const priceMedian=medianOfValues(present.map(row=>row.apartment));
 const serviceMedian=medianOfValues(present.map(row=>row.services[key]));
 const matching=present.filter(row=>row.apartment<=priceMedian && row.services[key]>serviceMedian).sort((a,b)=>a.name.localeCompare(b.name,"fr"));
 return {status:"ready",present,missing,priceMedian,serviceMedian,matching,year:years[0]};
}
function scatterPlot(rows) {
 const key=$("scatterMetric").value,label=POI.find(([k])=>k===key)[1];
 const analysis=tradeoffAnalysis(rows,key),{present,missing}=analysis;
 const exclusions=missing.length?`<p class="tradeoff-exclusions">Cities not assessed because of incomplete data: ${missing.map(row=>escapeHtml(row.name)).join(", ")}. Missing values are not replaced with zero.</p>`:"";
 if(analysis.status!=="ready")return chartEmpty(analysis.status==="periods"?"Property prices cover different years. Select cities with prices from the same year to calculate the benchmarks.":"Select at least three cities with documented apartment prices and this service to display the analysis.")+exclusions;
 const {priceMedian,serviceMedian,matching,year}=analysis;
 const matchingCodes=new Set(matching.map(row=>row.code));
 const w=560,h=340,left=58,right=28,top=28,bottom=65,plotW=w-left-right,plotH=h-top-bottom;
 const xMax=niceMaximum(Math.max(...present.map(r=>r.apartment))),yMax=Math.max(4,niceMaximum(Math.max(...present.map(r=>r.services[key]))));
 const medianX=left+priceMedian/xMax*plotW,medianY=top+plotH-serviceMedian/yMax*plotH;
 let body=`<rect x="${left}" y="${top}" width="${medianX-left}" height="${medianY-top}" fill="#e4f2e7"/>`;
 for(let i=0;i<=4;i++){
  const x=left+plotW*i/4,y=top+plotH-plotH*i/4;
  body+=`<line x1="${x}" y1="${top}" x2="${x}" y2="${top+plotH}" class="chart-gridline"/><text x="${x}" y="${h-42}" text-anchor="middle" class="chart-axis">${number(xMax*i/4)}</text><line x1="${left}" y1="${y}" x2="${w-right}" y2="${y}" class="chart-gridline"/><text x="${left-10}" y="${y+4}" text-anchor="end" class="chart-axis">${number(yMax*i/4,1)}</text>`;
 }
 body+=`<line x1="${medianX}" y1="${top}" x2="${medianX}" y2="${top+plotH}" stroke="#57796b" stroke-dasharray="5 5"/><line x1="${left}" y1="${medianY}" x2="${w-right}" y2="${medianY}" stroke="#57796b" stroke-dasharray="5 5"/>`;
 body+=`<text x="${left}" y="14" class="chart-axis">${label} · count across the municipality</text><text x="${left+plotW/2}" y="${h-13}" text-anchor="middle" class="chart-axis">Apartments · €/m²</text>`;
 present.forEach(row=>{
  const x=left+row.apartment/xMax*plotW,y=top+plotH-row.services[key]/yMax*plotH,selected=row.code===selectedId,match=matchingCodes.has(row.code);
  body+=chartCity(row,`<circle cx="${x}" cy="${y}" r="${selected?9:7}" fill="${selected?CHART_COLORS.orange:match?CHART_COLORS.teal:"#829b95"}" stroke="white" stroke-width="2" opacity=".9"/>${selected?`<text x="${x-10}" y="${y-12}" text-anchor="end" class="chart-label">${escapeHtml(row.name)}</text>`:""}`,`${row.name} : ${number(row.apartment)} €/m² and ${number(row.services[key])} mapped ${label.toLowerCase()} across the municipality. Select to highlight this city.`);
 });
 const summary=`<div class="tradeoff-summary" role="status"><p><strong>${matching.length} / ${present.length} cities meet both criteria.</strong> An apartment price at or below the selection benchmark and a service count above its benchmark.</p><div class="tradeoff-benchmarks"><div><span>Price benchmark · apartments</span><strong>${number(priceMedian)} €/m²</strong><small>Sales ${escapeHtml(year)}</small></div><div><span>Service benchmark · ${escapeHtml(label.toLowerCase())}</span><strong>${number(serviceMedian,1)}</strong><small>Mapped objects per municipality</small></div></div></div>`;
 const cards=matching.length?`<div class="tradeoff-shortlist">${matching.map(row=>`<button class="tradeoff-city" data-chart-city="${escapeHtml(row.code)}"><strong>${escapeHtml(row.name)} ↗</strong><span>${number(row.apartment)} €/m² · ${number(row.apartmentCount)} retained sales</span><span>${escapeHtml(label)} : ${number(row.services[key])}</span><small>Services collected on ${date(row.info.poi.collected_at)}${row.info.poi.retained?" · previous figures retained":""}</small></button>`).join("")}</div>`:chartEmpty("No city meets both criteria in this selection. Change the service or the selected cities to explore another trade-off.");
 return summary+`<div class="tradeoff-layout"><div><div class="chart-legend"><span><i style="background:#248474"></i>Both criteria met</span><span><i style="background:#829b95"></i>Other cities</span></div>`+svgChart(`Apartment prices and number of ${label.toLowerCase()} across the municipality for ${present.length} cities`,w,h,body)+`<p class="chart-footnote">The green area combines lower prices and more services, relative to the benchmarks for this selection.</p></div><div><h4>Cities to explore</h4>${cards}</div></div>`+exclusions+`<details class="tradeoff-method"><summary>How are the benchmarks chosen?</summary><p>Each benchmark is the median across cities with both indicators: half the values fall below it and half above it. The apartment price must be at or below its median; the service count must be strictly above its own median. Benchmarks change with your selection. Cities are listed alphabetically.</p><p>Services are compared one category at a time using raw municipal counts. Larger cities may have more services; this does not measure proximity from a neighbourhood, quality or mapping completeness. This selection is not a quality-of-life ranking.</p></details>`+dataTable(["City","Apartment prices €/m²",`${label} · count across the municipality`,"Retained sales","Service collection date"],present.map(r=>[r.name,number(r.apartment),number(r.services[key]),number(r.apartmentCount),date(r.info.poi.collected_at)]));
}
function airLollipops(rows) {
 const present=rows.filter(row=>row.air!=null);
 if(!present.length)return chartEmpty("No PM2.5 reading with unit, station and date is available in this selection.");
 const w=560,left=113,right=60,plot=w-left-right,h=present.length*29+50,max=niceMaximum(Math.max(...present.map(r=>Number(r.air.value))));
 let body="";
 for(let i=0;i<=4;i++){const x=left+plot*i/4;body+=`<line x1="${x}" y1="8" x2="${x}" y2="${h-35}" class="chart-gridline"/><text x="${x}" y="${h-13}" text-anchor="middle" class="chart-axis">${number(max*i/4,1)}</text>`;}
 present.forEach((row,i)=>{
  const y=20+i*29,x=left+Number(row.air.value)/max*plot;
  body+=chartCity(row,`<text x="0" y="${y+4}" class="chart-label">${escapeHtml(row.name)}</text><line x1="${left}" y1="${y}" x2="${x}" y2="${y}" stroke="#cedce4" stroke-width="3"/><circle cx="${x}" cy="${y}" r="6" fill="${CHART_COLORS.blue}"/><text x="${x+10}" y="${y+4}" class="chart-value">${number(row.air.value,1)}</text>`,`${row.name} : PM2.5 ${number(row.air.value,1)} µg/m³, station ${row.air.station}, ${number(row.air.distance,1)} km, ${dateTime(row.air.measured_at)}. Single reading, without a health ranking.`);
 });
 return svgChart("Latest documented PM2.5 readings, cities in alphabetical order",w,h,body)+dataTable(["City","PM2.5 µg/m³","Station","Distance km","Reading"],present.map(r=>[r.name,number(r.air.value,1),r.air.station,number(r.air.distance,1),dateTime(r.air.measured_at)]));
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
 if(!rows.length)return chartEmpty("Select at least one city to explore recorded hazards.");
 const category=$("riskCategory").value;
 const labels=[...new Set(rows.flatMap(row=>row.risks||[]))].filter(label=>category==="all"||riskFamily(label)===category).sort((a,b)=>a.localeCompare(b,"fr"));
 if(!labels.length)return chartEmpty("No hazard of this category appears in the documented responses for this selection.");
 const head=rows.map(row=>`<th scope="col">${escapeHtml(row.name)}</th>`).join("");
 const body=labels.map(label=>`<tr><td>${escapeHtml(riskLabel(label))}</td>${rows.map(row=>{
  if(!row.risks)return '<td class="missing" title="Undocumented list">—</td>';
  const present=row.risks.includes(label);
  return `<td class="${present?"present":""}" aria-label="${escapeHtml(row.name)} : ${present?"recorded":"not recorded in this response"}" title="${escapeHtml(row.name)} : ${present?"recorded":"not recorded in this response"}"><span class="${present?"risk-presence":"risk-absence"}" aria-hidden="true"></span></td>`;
 }).join("")}</tr>`).join("");
 return `<p class="risk-filter-note">${labels.length} hazard types shown. Use the filter to choose a category.</p><div class="matrix-scroll"><table class="services-table risk-table" style="min-width:${Math.max(650,240+rows.length*76)}px"><caption class="sr-only">Recorded hazard types by city (English translations of French source labels)</caption><thead><tr><th scope="col">Hazard type</th>${head}</tr></thead><tbody>${body}</tbody></table></div><div class="chart-legend" style="margin-top:15px"><span><i style="background:#b58054"></i>Recorded</span><span>○ Not in this list</span><span>— Data unavailable</span></div>`;
}
function qualityCoverage(rows) {
 const n=rows.length;
 const retained=rows.filter(r=>r.info.poi?.status==="available"&&r.info.poi.retained).length;
 const definitions=[
  ["Property prices · DVF",rows.filter(r=>r.apartment!=null||r.house!=null).length,"Prices are calculated from a selected sample of sales. They provide a reference point, not a description of every home."],
  ["Services · OSM",rows.filter(r=>r.info.poi?.status==="available").length,`Counts cover the whole municipality. Services not mapped in OpenStreetMap may be missing.${retained?` For ${retained} cities, previous figures are retained after an update failure, together with their original date.`:""}`],
  ["Air · OpenAQ",rows.filter(r=>r.air!=null).length,"The station and time of each measurement are retained. These readings do not describe a full year."],
  ["Hazards · GASPAR",rows.filter(r=>r.risks!=null).length,"A list of hazards recorded for the municipality. It does not describe exposure at each property."]
 ];
 return `<div class="quality-layout">${definitions.map(([label,count,note])=>`<div class="quality-item"><h4>${label}</h4><strong>${count} / ${n}</strong><div class="coverage-track"><span style="width:${n?count/n*100:0}%"></span></div><p>${note}</p></div>`).join("")}</div>`;
}
function renderDashboard() {
 if(!$("dashboard"))return;
 if(!cities.length){
  $("dashboardDate").textContent="Waiting for the data connection";
  $("analysisInsight").textContent="Charts will appear once the cities have loaded. The connection status is shown above the map.";
  $("kpiGrid").innerHTML=["Cities in the analysis","Available property prices","Retained sales","Service collections"].map(label=>`<div class="kpi-card"><div class="kpi-top">${label}</div><div class="kpi-value">—</div><div class="kpi-note">Waiting for data</div></div>`).join("");
  ["priceChart","housingChart","servicesChart","tradeoffChart","airChart","risksChart","qualityChart"].forEach(id=>{$(id).innerHTML=chartEmpty("City data has not loaded yet.");});
  return;
 }
 const rows=selectedDashboardRows(),n=rows.length,prices=rows.filter(r=>r.apartment!=null||r.house!=null),osm=rows.filter(r=>r.info.poi?.status==="available");
 const samples=rows.filter(r=>r.samples!=null),total=samples.reduce((sum,r)=>sum+r.samples,0);
 const collectedDates=rows.map(r=>r.info.collected?.collected_at||r.info.poi?.collected_at).filter(d=>d&&!Number.isNaN(Date.parse(d))).sort((a,b)=>Date.parse(b)-Date.parse(a));
 $("dashboardDate").textContent=collectedDates.length?`Last collected on ${date(collectedDates[0])}`:audit.audited_at?`Checked on ${date(audit.audited_at)}`:"Documented observations";
 $("dashboardCities").innerHTML=cities.map(city=>`<button class="city-chip" data-dashboard-city="${escapeHtml(city.insee_code)}" aria-pressed="${dashboardSelection==null||dashboardSelection.has(city.insee_code)}">${escapeHtml(city.city_name)}</button>`).join("");
 const cards=[["Cities in the analysis",n,"Choose the cities to compare above","⌖"],["Available property prices",`${prices.length} <small>/ ${n}</small>`,"Cities with available prices for apartments or houses","⌂"],["Retained sales",samples.length?number(total):"—","Sales retained after data cleaning","↗"],["Service collections",`${osm.length} <small>/ ${n}</small>`,"Services mapped across the municipality","◈"]];
 $("kpiGrid").innerHTML=cards.map(([label,value,note,icon])=>`<div class="kpi-card"><div class="kpi-top"><span>${label}</span><span aria-hidden="true">${icon}</span></div><div class="kpi-value">${value}</div><div class="kpi-note">${note}</div></div>`).join("");
 const values=rows.filter(r=>r.apartment!=null).sort((a,b)=>a.apartment-b.apartment);
 if(values.length>=2){const low=values[0],high=values.at(-1);
  $("analysisInsight").innerHTML=`<strong>In your selection,</strong> median apartment prices range from <strong>${number(low.apartment)} €/m² in ${escapeHtml(low.name)}</strong> to <strong>${number(high.apartment)} €/m² in ${escapeHtml(high.name)}</strong>. Compare this budget with municipal services to refine your choice.`;
 }else $("analysisInsight").textContent=n?"There are not enough apartment medians in the selection to describe their spread. Available indicators remain displayed separately.":"No city is selected. Choose cities to analyse, or use All cities.";
 $("priceChart").innerHTML=priceBars(rows);$("housingChart").innerHTML=housingDumbbells(rows);
 $("servicesChart").innerHTML=servicesMatrix(rows);$("tradeoffChart").innerHTML=scatterPlot(rows);
 $("airChart").innerHTML=airLollipops(rows);$("risksChart").innerHTML=risksMatrix(rows);$("qualityChart").innerHTML=qualityCoverage(rows);
 $("dashboardCities").querySelectorAll("[data-dashboard-city]").forEach(button=>button.addEventListener("click",()=>{
  if(dashboardSelection==null)dashboardSelection=new Set(cities.map(c=>c.insee_code));
  const code=button.dataset.dashboardCity;if(dashboardSelection.has(code))dashboardSelection.delete(code);else dashboardSelection.add(code);
  renderDashboard();$("dashboardCities").querySelector(`[data-dashboard-city="${code}"]`)?.focus();
 }));
 $("dashboard").querySelectorAll("[data-chart-city]").forEach(point=>{
  const activate=()=>selectCity(point.dataset.chartCity,false);
  point.addEventListener("click",activate);point.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();activate();}});
 });
}
window.addEventListener("cities:loaded",renderDashboard);
["priceType","scatterMetric","riskCategory"].forEach(id=>$(id).addEventListener("change",renderDashboard));
$("resetDashboard").addEventListener("click",()=>{dashboardSelection=null;renderDashboard();});
renderDashboard();
