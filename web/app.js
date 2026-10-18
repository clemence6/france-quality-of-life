/* Habiter : observations séparées, sans score synthétique. */
const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const number = (value, digits = 0) => value != null && value !== "" && Number.isFinite(Number(value)) ? new Intl.NumberFormat("fr-FR", {maximumFractionDigits: digits}).format(Number(value)) : "—";
const date = (value) => value && !Number.isNaN(Date.parse(value)) ? new Intl.DateTimeFormat("fr-FR", {day:"numeric",month:"short",year:"numeric",timeZone:"Europe/Paris"}).format(new Date(value)) : "date inconnue";
const dateTime = (value) => value && !Number.isNaN(Date.parse(value)) ? new Intl.DateTimeFormat("fr-FR", {dateStyle:"medium",timeStyle:"short",timeZone:"Europe/Paris"}).format(new Date(value)) + " (Paris)" : "date inconnue";
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
// URL publique du profil de l’autrice du portfolio.
const PORTFOLIO_LINKEDIN_URL = "";
const SOURCE_URLS = {
 dvf:"https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres-geolocalisees",
 risks:"https://www.georisques.gouv.fr/donnees/bases-de-donnees/procedures-administratives-relatives-aux-risques",
 osm:"https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL",
 air:"https://docs.openaq.org/resources/latest",
 ign:"https://cartes.gouv.fr/aide/fr/guides-utilisateur/utiliser-les-services-de-la-geoplateforme/geocodage/",
};
const SCHOOL_COUNT_NOTE = "Ce comptage OSM inclut les écoles, collèges et lycées, publics ou privés. Un établissement peut être représenté plusieurs fois ; ce total ne constitue pas un annuaire officiel.";
const POI = [["poi_pharmacy","Pharmacies"],["poi_hospital","Hôpitaux"],["poi_school","Établissements scolaires"],["poi_park","Parcs"],["poi_sport","Centres de fitness"],["poi_supermarket","Supermarchés"],["poi_restaurant","Restaurants"]];
let cities = [], provenance = {}, audit = {}, map = null, mapReady = false;
let selectedId = null, currentView = "explore", shortlist = [], markers = [], hub = null, hoverPopup = null;
let labelFrame = null;

// Des métadonnées anciennes ne doivent jamais certifier une nouvelle ligne.
function matchingEntry(document, city) {
 const entry = document.cities?.[city.insee_code];
 if (!entry?.snapshot) return null;
 return Object.entries(entry.snapshot).every(([key, value]) => key === "updated_at"
  ? value != null && Date.parse(city[key]) === Date.parse(value)
  : (city[key] ?? null) === value) ? entry : null;
}
function information(city) {
 const collected = matchingEntry(provenance, city);
 const checked = matchingEntry(audit, city);
 return {
  collected, checked,
  dvf: collected?.dvf || checked?.dvf || null,
  risks: collected?.risks || checked?.risks || null,
  geocoding: collected?.geocoding || checked?.geocoding || null,
  air: collected?.air || checked?.air || null,
  poi: communePoi(collected) || communePoi(checked),
  verifiedDate: collected?.collected_at || checked?.audited_at,
 };
}
function communePoi(entry) {
 const poi=entry?.poi_commune || entry?.poi;
 return poi?.scope === "commune" ? poi : null;
}
function priceInfo(city, type = "apartment") {
 const d = information(city).dvf;
 if (!d) return {value:null, count:null, note:"Ancien calcul retiré · à recalculer", valid:false};
 const stat = d.by_type?.[type];
 return {value:stat?.median_price_m2 ?? null,count:stat?.sample_count ?? 0,
  note:`${d.year || ""} · ${number(stat?.sample_count)} ventes analysées`,
  period:`${date(d.period_start)} → ${date(d.period_end)}`,valid:true};
}
function poiValue(city, key) {
 const poi = information(city).poi;
 // Aucun repli vers les anciens comptages locaux pour un total communal.
 const value = poi?.status === "available" ? poi.counts?.[key.replace("poi_", "")] : null;
 return value != null && Number.isFinite(Number(value)) && Number(value)>=0 ? Number(value) : null;
}
function coords(city) {
 const geo = information(city).geocoding;
 const lat = geo?.latitude ?? city.latitude, lon = geo?.longitude ?? city.longitude;
 if (lat == null || lon == null || !Number.isFinite(Number(lat)) || !Number.isFinite(Number(lon)) || Math.abs(lat)>90 || Math.abs(lon)>180) return null;
 return [Number(lon),Number(lat)];
}
async function fetchJson(url, options = {}) {
 const {timeoutMs=20000,...requestOptions}=options;
 const controller = new AbortController();
 const timer = setTimeout(() => controller.abort(), timeoutMs);
 try {
  const response = await fetch(url, {...requestOptions, signal:controller.signal});
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || `HTTP ${response.status}`);
  return data;
 } finally { clearTimeout(timer); }
}
async function loadCities() {
 $("statusArea").hidden = false;
 $("statusArea").textContent = "Connexion aux données…";
 try {
  if (typeof SUPABASE_CONFIG === "undefined" || !SUPABASE_CONFIG.url || !SUPABASE_CONFIG.anonKey || SUPABASE_CONFIG.url.includes("YOUR-PROJECT")) throw new Error("Renseigne l’URL et la clé publique dans config.js.");
  const endpoint = new URL(`/rest/v1/${encodeURIComponent(SUPABASE_CONFIG.table || "cities_qol")}`, SUPABASE_CONFIG.url);
  endpoint.searchParams.set("select", "*"); endpoint.searchParams.set("order", "city_name.asc");
  const rows = [];
  for (let offset = 0; ; offset += 1000) {
   endpoint.searchParams.set("limit",1000); endpoint.searchParams.set("offset",offset);
   const page = await fetchJson(endpoint, {headers:{apikey:SUPABASE_CONFIG.anonKey,Authorization:`Bearer ${SUPABASE_CONFIG.anonKey}`}});
   if (!Array.isArray(page)) throw new Error("Réponse Supabase inattendue.");
   rows.push(...page); if (page.length<1000) break;
  }
  // Les rapports sont facultatifs : sans eux les valeurs restent historiques.
  const metadataUrl = new URL("/storage/v1/object/public/qol-public-metadata/provenance.json",SUPABASE_CONFIG.url);
  const documents = await Promise.allSettled([fetchJson("data/provenance.json"), fetchJson("data/audit.json"),fetchJson(metadataUrl.href,{timeoutMs:5000,cache:"no-store"})]);
  const local=documents[0].status === "fulfilled" ? documents[0].value : {};
  const remote=documents[2].status === "fulfilled" ? documents[2].value : {};
  provenance = resolveProvenance(rows,local,remote);
  audit = documents[1].status === "fulfilled" ? documents[1].value : {};
  cities = rows.filter((c) => c.insee_code && typeof c.city_name === "string").sort((a,b)=>a.city_name.localeCompare(b.city_name,"fr"));
  if (!cities.length) { $("statusArea").textContent = "Aucune ville accessible. Vérifie l’alimentation de la table et sa policy RLS de lecture."; return; }
  $("statusArea").hidden = true;
  $("studyCityCount").textContent = `${cities.length} villes françaises`;
  $("dataFreshness").textContent = `${cities.length} villes documentées · France métropolitaine`;
  $("auditCaption").textContent = audit.audited_at ? `Rapport de contrôle du ${date(audit.audited_at)}. Les prix sont recalculés à partir des fichiers DVF déjà téléchargés ; chaque collecte d’API conserve sa propre date.` : "Le rapport de contrôle n’est pas disponible pour cette version.";
  fillCompare(); renderList(); addMarkers(); renderCompare();
  window.dispatchEvent(new Event("cities:loaded"));
 } catch (error) {
  const p = document.createElement("p");
  p.textContent = error.name === "AbortError" ? "La base ne répond pas après 20 secondes. Vérifie que le projet Supabase est actif." : error.name === "TypeError" ? "Impossible de joindre la base. Vérifie la connexion et que Supabase n’est pas en pause." : error.message;
  const button = document.createElement("button"); button.className="retry"; button.textContent="Réessayer"; button.addEventListener("click",loadCities);
  $("statusArea").replaceChildren(p,button);
 }
}
function resolveProvenance(rows,local,remote) {
 return {cities:Object.fromEntries(rows.map(city=>[city.insee_code,matchingEntry(remote,city)||matchingEntry(local,city)]).filter(([,entry])=>entry))};
}
function filteredCities() {
 const normalize = (s) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
 const term = normalize($("searchInput").value.trim());
 return cities.filter((c)=>normalize(c.city_name).includes(term) || String(c.insee_code).includes(term));
}
function renderList() {
 const filtered = filteredCities();
 $("cityCount").textContent = `${filtered.length} / ${cities.length}`;
 $("cityList").innerHTML = filtered.length ? filtered.map((c,i)=>{
  const p = priceInfo(c);
  return `<button class="city-row ${selectedId===c.insee_code?"selected":""}" data-city="${escapeHtml(c.insee_code)}" aria-pressed="${selectedId===c.insee_code}"><span class="city-number">${String(i+1).padStart(2,"0")}</span><span class="city-row-main"><strong>${escapeHtml(c.city_name)}</strong><small>${p.value!=null ? `${number(p.value)} €/m² · appartements, échantillon` : "Découvrir les données & leurs limites"}</small></span><span aria-hidden="true">↗</span></button>`;
 }).join("") : '<p class="empty-list">Aucune ville ne correspond à la recherche.</p>';
 $("cityList").querySelectorAll("[data-city]").forEach((b)=>b.addEventListener("click",()=>selectCity(b.dataset.city)));
 const visible = new Set(filtered.map(c=>c.insee_code));
 markers.forEach(({city,marker})=>{marker.getElement().hidden=!visible.has(city.insee_code) || (map && map.getZoom()<3.3);});
 layoutMapLabels();
}
function riskLabel(value) { return value; }
function sourceLink(key,label) { return `<a href="${SOURCE_URLS[key]}" target="_blank" rel="noopener noreferrer">${label} ↗</a>`; }
function badge(label,checked=false) { return `<span class="badge ${checked?"checked":""}">${label}</span>`; }
function airObservation(city) {
 const air = information(city).air;
 if (!air) return null;
 const measurement = air.measurements?.pm25 || air.measurements?.["pm2.5"];
 if (!measurement || measurement.unit?.replace("μ","µ")!=="µg/m³" || !measurement.measured_at || measurement.value == null || !Number.isFinite(Number(measurement.value)) || Number(measurement.value)<0) return null;
 return {...measurement,station:air.station_name,distance:air.distance_km};
}
function selectCity(code, fly=true) {
 const city = cities.find(c=>c.insee_code===code); if (!city) return;
 if (currentView!=="explore") switchView("explore");
 selectedId=code; renderList();
 hoverPopup?.remove();
 markers.forEach(({city,marker})=>marker.getElement().classList.toggle("is-selected",city.insee_code===code));
 if(typeof renderDashboard === "function") renderDashboard();
 const info=information(city), p=priceInfo(city), house=priceInfo(city,"house"), air=airObservation(city);
 const riskList=info.risks?.risks || [];
 $("cityPanel").hidden=false;
 $("cityPanel").innerHTML=`<div class="panel-top"><span class="eyebrow">PORTRAIT DE VILLE</span><button id="closeCity" class="close-btn" aria-label="Fermer la fiche">×</button></div><h2>${escapeHtml(city.city_name)}</h2><div class="city-context">Commune · INSEE ${escapeHtml(code)}<br>Base mise à jour le ${date(city.updated_at)}</div>
 <div class="city-highlight"><div class="metric-label">ACHETER UN APPARTEMENT</div><div class="metric-big">${number(p.value)} <small>€/m²</small></div>${badge(p.value!=null?"Calculé à partir des ventes DVF":"Prix indisponible",p.value!=null)}<div class="metric-meta">Prix médian · ${escapeHtml(p.note)}${p.valid?`<br>${escapeHtml(p.period)}`:""}</div></div>
 <section class="detail-section"><h3>Immobilier ${sourceLink("dvf","DVF")}</h3><div class="metric-line"><span>Maisons · prix médian</span><strong>${number(house.value)} €/m²</strong></div><div class="metric-meta">${escapeHtml(house.note)}</div><p class="micro-note">${info.dvf?"Un repère calculé sur une sélection de ventes, pas sur tous les logements. Aucun prix n’est affiché avec moins de 10 ventes analysées.":"Les données disponibles ne permettent pas encore de calculer un prix fiable pour cette ville."}</p><details><summary>Que signifie « prix médian » ?</summary><p>La moitié des ventes analysées a un prix au m² plus bas, l’autre moitié un prix plus élevé. Les maisons et les appartements sont étudiés séparément.</p><p>La sélection des ventes et les filtres de prix sont expliqués dans « Sources & méthode ».</p></details></section>
 <section class="detail-section"><h3>Les services dans la ville ${sourceLink("osm","OSM")}</h3>${badge(info.poi?.status==="available"?`${info.poi.retained?"Dernière collecte du":"Actualisé le"} ${date(info.poi.collected_at)}`:"Données communales indisponibles",info.poi?.status==="available"&&!info.poi.retained)}${POI.map(([key,label])=>`<div class="metric-line"><span>${label}</span><strong>${number(poiValue(city,key))}</strong></div>`).join("")}<p class="micro-note">${info.poi?.retained?`La mise à jour a échoué. Les chiffres du ${date(info.poi.collected_at)} restent affichés. `:""}Services référencés dans les limites de la commune de ${escapeHtml(city.city_name)}. Le recensement dépend des informations disponibles dans OpenStreetMap.</p></section>
 <p class="micro-note">${escapeHtml(SCHOOL_COUNT_NOTE)}</p>
 <section class="detail-section"><h3>Risques recensés ${sourceLink("risks","GASPAR")}</h3>${badge(info.checked?.risks?`Consulté le ${date(info.checked.audited_at)}`:info.risks?"Source et date conservées":"Ancienne donnée · à vérifier",!!info.risks)}${riskList.length?`<div class="risk-tags">${riskList.map(r=>`<span class="risk-tag">${escapeHtml(riskLabel(r))}</span>`).join("")}</div>`:`<div class="metric-line"><span>Types de risques</span><strong>${number(info.risks?.total_risks ?? city.risks_count)}</strong></div>`}<p class="micro-note">Un risque mentionné pour la commune ne touche pas forcément chaque logement. Consultez Géorisques à l’adresse du bien pour en savoir plus. ${info.checked?.risks?.matches_stored===false?"La liste a évolué depuis l’ancienne collecte.":""}</p></section>
 <section class="detail-section"><h3>Air · particules fines ${sourceLink("air","OpenAQ")}</h3>${air?`<div class="metric-line"><span>Dernière mesure PM2.5 conservée</span><strong>${number(air.value,1)} µg/m³</strong></div><div class="metric-meta">${escapeHtml(air.station)} · ${number(air.distance,1)} km<br>Mesure du ${dateTime(air.measured_at)}</div><p class="micro-note">Une mesure à un endroit et à un instant précis. Elle ne décrit pas l’air de toute la ville sur l’année.</p>`:info.air?`${badge("Donnée indisponible")}<p class="micro-note">Aucune mesure récente de particules fines trouvée dans les stations interrogées à moins de 25 km. Cela ne signifie pas que l’air est bon ou mauvais.</p>`:`${badge("Donnée insuffisante")}<p class="micro-note">La source ou la date de l’ancienne mesure manque. Elle n’est pas affichée pour éviter une comparaison trompeuse.</p>`}</section>
 <button id="addCompare" class="primary-btn">${shortlist.includes(code)?"Voir la comparaison ↗":"Ajouter à ma comparaison ↗"}</button><a class="text-link" href="https://www.insee.fr/fr/statistiques/1405599?geo=COM-${encodeURIComponent(code)}" target="_blank" rel="noopener noreferrer">Portrait officiel INSEE ↗</a>`;
 $("closeCity").addEventListener("click",closeCity);
 $("addCompare").addEventListener("click",()=>{
  if (!shortlist.includes(code)) shortlist=[...shortlist,code].slice(-2);
  $("compareCount").textContent=shortlist.length;
  if(shortlist[0]) $("compareCityA").value=shortlist[0];
  if(shortlist[1]) $("compareCityB").value=shortlist[1];
  else {const other=cities.find(c=>c.insee_code!==code);if(other) $("compareCityB").value=other.insee_code;}
  switchView("compare"); renderCompare();
 });
 const position=coords(city);
 if(map && position && fly) map.flyTo({center:position,zoom:7,bearing:0,pitch:0,duration:reducedMotion?0:1700,padding:{left:window.innerWidth>900?370:0,right:window.innerWidth>1000?390:0,top:30,bottom:40}});
 updateRadius(city);
}
function closeCity() {selectedId=null;hoverPopup?.remove();markers.forEach(({marker})=>marker.getElement().classList.remove("is-selected"));if(typeof renderDashboard === "function") renderDashboard();$("cityPanel").hidden=true;renderList();if(mapReady) map.getSource("sample-radius")?.setData({type:"FeatureCollection",features:[]});}
function fillCompare() {
 const options=cities.map(c=>`<option value="${escapeHtml(c.insee_code)}">${escapeHtml(c.city_name)}</option>`).join("");
 $("compareCityA").innerHTML=options;$("compareCityB").innerHTML=options;
 if(cities.length>1) $("compareCityB").selectedIndex=1;
}
function renderCompare() {
 const a=cities.find(c=>c.insee_code===$("compareCityA").value),b=cities.find(c=>c.insee_code===$("compareCityB").value);
 if(!a||!b){$("compareContent").textContent="Chargez les villes pour les comparer.";return;}
 const priceCell=(c,type)=>{const p=priceInfo(c,type);return `${number(p.value)} €/m²<small>${escapeHtml(p.note)}${p.valid?`<br>${escapeHtml(p.period)}`:""}</small>`;};
 const riskCell=c=>{const i=information(c);return `${number(i.risks?.total_risks ?? c.risks_count)} types<small>${i.risks?"Liste documentée":"Historique, non certifié"} · pas une intensité de risque</small>`;};
 const airCell=c=>{const v=airObservation(c);return v?`${number(v.value,1)} µg/m³<small>PM2.5 · ${dateTime(v.measured_at)}<br>${escapeHtml(v.station)} · relevé ponctuel</small>`:information(c).air?'Donnée indisponible<small>Aucun relevé PM2.5 récent exploitable trouvé</small>':'Non comparable<small>Polluant / unité / date non conservés</small>';};
 const rows=[["Appartements · médiane",priceCell(a,"apartment"),priceCell(b,"apartment")],["Maisons · médiane",priceCell(a,"house"),priceCell(b,"house")],["Risques recensés",riskCell(a),riskCell(b)],["Air · relevé documenté",airCell(a),airCell(b)],...POI.map(([key,label])=>[`${label} · dans la commune`,`${number(poiValue(a,key))}<small>${information(a).poi?.status==="available"?"Recensé dans toute la commune":"Donnée indisponible"}</small>`,`${number(poiValue(b,key))}<small>${information(b).poi?.status==="available"?"Recensé dans toute la commune":"Donnée indisponible"}</small>`])];
 const pa=priceInfo(a),pb=priceInfo(b);
 const samePeriod=pa.valid&&pb.valid&&pa.period===pb.period;
 $("compareContent").innerHTML=`${a===b?'<p class="compare-warning">La même ville est sélectionnée des deux côtés.</p>':""}<div class="compare-warning">${samePeriod?"Les prix couvrent la même période et sont calculés avec les mêmes règles. Les logements vendus peuvent cependant être différents d’une ville à l’autre.":"Les périodes des prix diffèrent ou certaines données manquent : comparez ces prix avec prudence."} Une grande ville peut compter davantage de services. Les mesures d’air décrivent un moment précis.</div><div style="overflow-x:auto"><table class="compare-table"><thead><tr><th>Indicateur</th><th>${escapeHtml(a.city_name)}</th><th>${escapeHtml(b.city_name)}</th></tr></thead><tbody>${rows.map(([label,va,vb])=>`<tr><td>${label}</td><td>${va}</td><td>${vb}</td></tr>`).join("")}</tbody></table></div>`;
}
function switchView(view) {
 currentView=view;
 $("explorer").classList.toggle("show-sources",view==="sources");
 ["explore","compare","sources"].forEach(v=>{$(`${v}View`).hidden=v!==view;});
 $("cityPanel").hidden=view!=="explore" || !selectedId;
 $("dashboard").hidden=view!=="explore";
 if(map && view!=="sources")map.resize();
 document.querySelectorAll("[data-view]").forEach(button=>{const active=button.dataset.view===view;button.classList.toggle("active",active);button.setAttribute("aria-pressed",String(active));});
 if(view==="compare")renderCompare();
}
function renderSources() {
 const contact=$("linkedinContact");
 if (PORTFOLIO_LINKEDIN_URL) {
  try {
   const profile=new URL(PORTFOLIO_LINKEDIN_URL);
   if(profile.protocol==="https:" && /^(www\.)?linkedin\.com$/.test(profile.hostname) && /^\/in\/[^/]+/.test(profile.pathname)) {
    contact.href=profile.href;
    contact.hidden=false;
   }
  } catch { /* Sans URL de profil valide, aucun lien de contact n’est affiché. */ }
 }
 const sources=[
 ["DVF · quel budget pour acheter ?","dvf","Fichiers CSV · ventes immobilières","Les fichiers de ventes publiés par la DGFiP fournissent le prix, la surface et le type de logement. Python et pandas sélectionnent les ventes utilisables et calculent le prix médian au m² par ville, pour les maisons et les appartements séparément.","Ces prix décrivent les ventes analysées. Strasbourg n’a pas de prix DVF : cette source ne couvre pas le Bas-Rhin."],
 ["OpenStreetMap · quels services au quotidien ?","osm","API Overpass · services cartographiés","Une requête récupère les services référencés dans les limites de chaque commune : pharmacies, hôpitaux, écoles, parcs, centres de fitness, supermarchés et restaurants. Le code INSEE permet de sélectionner le bon territoire.","La carte est alimentée par des contributeurs : des lieux peuvent manquer ou être décrits plusieurs fois. Le nombre de services dépend aussi de la taille de la ville."],
 ["Géorisques · quels risques sont recensés ?","risks","API GASPAR · risques par commune","L’API est interrogée pour chaque commune. Les intitulés des risques sont conservés et les répétitions retirées pour présenter une liste lisible.","La liste concerne la commune. Elle n’indique ni la gravité d’un risque ni si un logement précis est exposé."],
 ["OpenAQ · que mesure l’air à proximité ?","air","API OpenAQ v3 · mesures de particules fines","Le script cherche une station fixe de référence à moins de 25 km et récupère un relevé de particules fines PM2.5. Il garde la station, la distance, l’heure et l’unité de mesure. À la collecte, seuls les relevés de moins de 48 heures sont retenus.","Il s’agit d’une mesure ponctuelle près d’une station, pas d’une moyenne annuelle pour toute la ville. La date reste visible même lorsque la mesure vieillit."],
 ["IGN · où placer la ville sur la carte ?","ign","API de géocodage · coordonnées de la commune","Le service IGN fournit les coordonnées de la commune. Le code renvoyé est vérifié pour éviter de placer sur la carte une autre ville portant le même nom.","Le point sert à localiser la commune et à rechercher les stations proches. Il ne représente pas tous ses quartiers."],
 ];
 $("sourceCards").innerHTML=sources.map(([title,key,format,text,scope])=>`<article class="source-card"><span class="source-format">${format}</span><h4>${title}${sourceLink(key,"Voir la source")}</h4><p>${text}</p><p class="source-scope"><strong>À garder en tête.</strong> ${scope}</p></article>`).join("");
}
function mapMessage(message) {$("mapStatus").hidden=false;$("mapStatus").textContent=message;}
function initMap() {
 if(!window.maplibregl){mapMessage("La bibliothèque cartographique est indisponible. Les fiches et la comparaison restent accessibles.");return;}
 try {
  map=new maplibregl.Map({container:"map",center:[2.8,46.6],zoom:4.7,minZoom:3.3,maxZoom:17,attributionControl:{compact:false},padding:{left:window.innerWidth>900?380:0,right:0,top:25,bottom:45},
   style:{version:8,projection:{type:"mercator"},sources:{
    world:{type:"geojson",data:"vendor/world.geojson",attribution:'<a href="https://www.naturalearthdata.com/" target="_blank">Natural Earth</a>'},
    streets:{type:"raster",tiles:["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],tileSize:256,minzoom:5,maxzoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap contributors</a>'},
   },layers:[
    {id:"ocean",type:"background",paint:{"background-color":"#bcd4dc"}},
    {id:"land",type:"fill",source:"world",paint:{"fill-color":["case",["==",["get","ADMIN"],"France"],"#d9e3d1","#edf0e6"],"fill-opacity":1}},
    {id:"borders",type:"line",source:"world",paint:{"line-color":"#7f9d96","line-width":0.6,"line-opacity":0.6}},
    {id:"streets",type:"raster",source:"streets",minzoom:5,paint:{"raster-saturation":-0.5,"raster-brightness-min":0.12,"raster-brightness-max":0.95,"raster-opacity":["interpolate",["linear"],["zoom"],5,0,6,1]}}
   ]}});
  map.on("load",()=>{
   mapReady=true;
   map.addSource("sample-radius",{type:"geojson",data:{type:"FeatureCollection",features:[]}});
   map.addLayer({id:"sample-fill",type:"fill",source:"sample-radius",paint:{"fill-color":"#197660","fill-opacity":0.07}});
   map.addLayer({id:"sample-line",type:"line",source:"sample-radius",paint:{"line-color":"#197660","line-width":1,"line-dasharray":[3,3]}});
   focusFrance(); addMarkers(); if(selectedId) updateRadius(cities.find(c=>c.insee_code===selectedId));
  });
  map.on("zoom",()=>{ const visible=new Set(filteredCities().map(c=>c.insee_code)); markers.forEach(({city,marker})=>{marker.getElement().hidden=!visible.has(city.insee_code);}); });
  map.on("move",layoutMapLabels);map.on("resize",layoutMapLabels);
  map.on("error",()=>mapMessage("Une ressource de la carte ne charge pas. Vérifie ta connexion ; les données des villes restent indépendantes du fond de carte."));
  map.on("idle",()=>{if(map.areTilesLoaded())$("mapStatus").hidden=true;});
 } catch(error) {map=null;mapMessage("Ce navigateur ne permet pas d’afficher la carte WebGL. Explore les villes depuis la liste.");}
}
function addMarkers() {
 if(!mapReady || !cities.length)return;
 markers.forEach(({marker})=>marker.remove());markers=[];hub?.remove();hoverPopup?.remove();
 const hubButton=document.createElement("button");hubButton.className="marker-button";hubButton.setAttribute("aria-label",`Explorer les ${cities.length} villes françaises`);
 hubButton.innerHTML=`<span class="marker-dot"></span><span class="marker-label">FRANCE · ${cities.length} VILLES ↗</span>`;
 hubButton.addEventListener("click",focusFrance);
 hub=new maplibregl.Marker({element:hubButton}).setLngLat([2.5,46.6]).addTo(map);
 for(const city of cities){
  const position=coords(city);if(!position)continue;
  const element=document.createElement("button");element.className="marker-button";element.dataset.cityCode=city.insee_code;element.setAttribute("aria-label",`Découvrir ${city.city_name}`);
  element.innerHTML=`<span class="marker-dot"></span><span class="marker-label">${escapeHtml(city.city_name)}</span>`;
  element.addEventListener("click",()=>selectCity(city.insee_code));
  const show=()=>{hoverPopup?.remove();const p=priceInfo(city);hoverPopup=new maplibregl.Popup({className:"city-tooltip",closeButton:false,closeOnClick:false,offset:20,maxWidth:"260px"}).setLngLat(position).setHTML(`<div class="hover-name">${escapeHtml(city.city_name)}</div><div class="hover-data">${p.value!=null?`${number(p.value)} €/m² · appartements<br>Échantillon DVF ${escapeHtml(information(city).dvf?.year)}`:"Données publiques & périmètres"}<br>Cliquer pour découvrir la fiche ↗</div>`).addTo(map);};
  element.addEventListener("mouseenter",show);element.addEventListener("focus",show);element.addEventListener("mouseleave",()=>hoverPopup?.remove());element.addEventListener("blur",()=>hoverPopup?.remove());
  markers.push({city,marker:new maplibregl.Marker({element,anchor:"center"}).setLngLat(position).addTo(map)});
 }
 updateMarkerVisibility();renderList();
}
// Seules les étiquettes bougent : les points restent aux coordonnées IGN.
function chooseLabelPlacement(point,width,height,occupied,dots,bounds,above=false) {
 const right=[10,-height/2],left=[-width-10,-height/2];
 const top=[-width/2,-height-10],bottom=[-width/2,10];
 const candidates=above?[top,right,left,bottom]:[right,left,top,bottom];
 candidates.push([10,-height-6],[-width-10,-height-6],[10,6],[-width-10,6],[-width/2,-height-22],[-width/2,22]);
 const overlap=(a,b)=>Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))*Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top));
 return candidates.map(([x,y],index)=>{
  const rect={left:point.x+x,top:point.y+y,right:point.x+x+width,bottom:point.y+y+height};
  const padded={left:rect.left-3,top:rect.top-3,right:rect.right+3,bottom:rect.bottom+3};
  const covered=occupied.reduce((n,r)=>n+overlap(padded,r),0)+dots.reduce((n,p)=>n+overlap(padded,{left:p.x-6,top:p.y-6,right:p.x+6,bottom:p.y+6}),0);
  const outside=width*height-overlap(rect,{left:8,top:8,right:bounds.width-8,bottom:bounds.height-8});
  return {x,y,rect,score:covered*1000+outside*2000+index};
 }).sort((a,b)=>a.score-b.score)[0];
}
function layoutMapLabels() {
 if(!mapReady || labelFrame!==null)return;
 labelFrame=requestAnimationFrame(()=>{
  labelFrame=null;
  const bounds=map.getContainer().getBoundingClientRect();
  const visible=markers.filter(({marker})=>!marker.getElement().hidden).map(item=>({...item,point:map.project(item.marker.getLngLat())}));
  const dots=visible.map(item=>item.point),occupied=[];
  // Montpellier garde son nom au-dessus du point, à proximité du repère.
  visible.sort((a,b)=>(b.city.insee_code==="34172")-(a.city.insee_code==="34172") || a.point.y-b.point.y);
  for(const {city,marker,point} of visible){
   const element=marker.getElement(),label=element.querySelector(".marker-label");
   const placement=chooseLabelPlacement(point,label.offsetWidth,label.offsetHeight,occupied,dots,bounds,city.insee_code==="34172");
   label.style.left=`${13+placement.x}px`;label.style.top=`${13+placement.y}px`;
   occupied.push(placement.rect);
  }
 });
}
function updateMarkerVisibility(){if(hub)hub.getElement().hidden=map.getZoom()>=3.3;}
function focusFrance(){if(!map)return;closeCity();map.fitBounds([[-5.5,41.2],[9.7,51.3]],{padding:{left:window.innerWidth>900?390:25,right:45,top:40,bottom:55},duration:reducedMotion?0:1300,maxZoom:5});}
function updateRadius(city) {
 if(mapReady)map.getSource("sample-radius")?.setData({type:"FeatureCollection",features:[]});
}
$("searchInput").addEventListener("input",renderList);
["compareCityA","compareCityB"].forEach(id=>$(id).addEventListener("change",renderCompare));
document.querySelectorAll("[data-view]").forEach(b=>b.addEventListener("click",()=>{switchView(b.dataset.view);$("explorer").scrollIntoView({behavior:reducedMotion?"auto":"smooth",block:"start"});}));
$("franceBtn").addEventListener("click",()=>{switchView("explore");focusFrance();});
$("worldBtn").addEventListener("click",()=>{switchView("explore");focusFrance();});
document.addEventListener("keydown",e=>{if(e.key==="Escape")closeCity();if(e.key==="/"&&!/INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName)){e.preventDefault();switchView("explore");$("searchInput").focus();}});
renderSources();initMap();if(map)map.on("zoom",updateMarkerVisibility);loadCities();
