/* Two static language versions, sharing the same data and stylesheet. */
(() => {
 const current=document.documentElement.lang === "en" ? "en" : "fr";
 const root=new URL("./",document.baseURI);
 const key="qol-language";
 let saved;
 try {saved=localStorage.getItem(key);} catch { /* The site also works without storage. */ }
 if(current === "fr" && saved === "en") {
  const target=new URL("en/",root);target.hash=location.hash;
  location.replace(target.href);return;
 }
 if(current === "en") {try {localStorage.setItem(key,"en");} catch {}}
 document.addEventListener("DOMContentLoaded",()=>{
  const select=document.getElementById("languageSelect");
  select.value=current;
  select.addEventListener("change",()=>{
   const language=select.value === "en" ? "en" : "fr";
   try {localStorage.setItem(key,language);} catch {}
   const target=new URL(language === "en" ? "en/" : "./",root);
   target.hash=location.hash;
   location.assign(target.href);
  });
 });
})();
